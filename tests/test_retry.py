import httpx
import pytest
import respx

from app.crm_client import CRMUnavailable, HttpCRMClient

BASE_URL = "http://crm.test"
CLIENTE = {"id": "cli-1", "nombre": "Ana Pérez", "plan": "basico"}


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def crm(sleeps) -> HttpCRMClient:
    client = HttpCRMClient(BASE_URL, max_attempts=3, timeout=1.0, backoff_base=0.5, sleep=sleeps.append)
    yield client
    client.close()


@respx.mock
def test_succeeds_on_third_attempt_with_progressive_backoff(crm, sleeps):
    route = respx.get(f"{BASE_URL}/clientes/cli-1").mock(
        side_effect=[httpx.Response(500), httpx.Response(500), httpx.Response(200, json=CLIENTE)]
    )

    assert crm.get_cliente("cli-1") == CLIENTE
    assert route.call_count == 3
    assert sleeps == [0.5, 1.0]


@respx.mock
def test_gives_up_after_max_attempts(crm, sleeps):
    route = respx.get(f"{BASE_URL}/clientes/cli-1").mock(return_value=httpx.Response(429))

    with pytest.raises(CRMUnavailable):
        crm.get_cliente("cli-1")
    assert route.call_count == 3
    assert sleeps == [0.5, 1.0]  # no sleep after the last attempt


@respx.mock
def test_timeout_is_retried(crm, sleeps):
    route = respx.get(f"{BASE_URL}/clientes/cli-1").mock(
        side_effect=[httpx.ReadTimeout("timed out"), httpx.Response(200, json=CLIENTE)]
    )

    assert crm.get_cliente("cli-1") == CLIENTE
    assert route.call_count == 2
    assert sleeps == [0.5]


@respx.mock
def test_client_error_is_not_retried(crm, sleeps):
    route = respx.get(f"{BASE_URL}/clientes/cli-1").mock(return_value=httpx.Response(404))

    with pytest.raises(CRMUnavailable):
        crm.get_cliente("cli-1")
    assert route.call_count == 1
    assert sleeps == []
