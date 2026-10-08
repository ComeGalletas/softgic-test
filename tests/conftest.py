import os

# Tests always run offline with the fake model: never read the local .env or a real key.
# This runs before any `app` import, because app.db builds its engine from the settings at import time.
os.environ["OPENAI_API_KEY"] = ""
os.environ["DATABASE_URL"] = "sqlite://"

from app.config import Settings  # noqa: E402

Settings.model_config["env_file"] = None

import json  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.language_models import FakeListChatModel  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.crm_client import CRMUnavailable  # noqa: E402
from app.db import create_tables, get_session  # noqa: E402
from app.main import app, get_crm_client, get_model  # noqa: E402


class RecordingFakeLLM(FakeListChatModel):
    """Fake chat model that also keeps the prompts it received, so tests can inspect them."""

    prompts: list[Any] = []

    def _call(self, messages, *args: Any, **kwargs: Any) -> str:
        self.prompts.append(messages)
        return super()._call(messages, *args, **kwargs)


class StubCRM:
    def __init__(self, cliente: dict[str, Any] | None = None, fail: bool = False) -> None:
        self.cliente = cliente or {"id": "cli-1", "nombre": "Ana Pérez", "plan": "premium"}
        self.fail = fail
        self.calls: list[str] = []

    def get_cliente(self, cliente_id: str) -> dict[str, Any]:
        self.calls.append(cliente_id)
        if self.fail:
            raise CRMUnavailable("CRM down")
        return self.cliente


@pytest.fixture
def make_llm():
    """Build a fake model answering a classification with the given priority, then a reply."""

    def _make(prioridad: str = "alta", categoria: str = "tecnico") -> RecordingFakeLLM:
        return RecordingFakeLLM(
            prompts=[],
            responses=[
                json.dumps({"categoria": categoria, "prioridad": prioridad}),
                json.dumps({"respuesta": "Hola, ya estamos revisando tu caso."}),
            ],
        )

    return _make


@pytest.fixture
def stub_crm() -> StubCRM:
    return StubCRM()


@pytest.fixture
def failing_crm() -> StubCRM:
    return StubCRM(fail=True)


@pytest.fixture
def client(make_llm, stub_crm):
    """API client over an in-memory SQLite database, the fake model and the stub CRM.

    The lifespan is not run (no `with TestClient(...)`), so no real CRM client is created.
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    create_tables(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def _session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_model] = lambda: make_llm("alta")
    app.dependency_overrides[get_crm_client] = lambda: stub_crm
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()
