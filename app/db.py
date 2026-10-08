from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str) -> Engine:
    # SQLite connections are shared across FastAPI's threadpool workers.
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_tables(bind: Engine = engine) -> None:
    from app import models  # noqa: F401  (registers the tables on Base.metadata)

    Base.metadata.create_all(bind)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
