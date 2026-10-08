def test_analyze_persists_and_get_returns_it(client, stub_crm):
    body = {"id": "sol-1", "texto": "Me cobraron dos veces este mes", "cliente_id": "cli-1"}

    created = client.post("/solicitudes/analizar", json=body)
    assert created.status_code == 200
    data = created.json()
    assert data["prioridad"] == "alta"
    assert data["cliente_info"]["nombre"] == "Ana Pérez"
    assert data["tokens_entrada"] > 0 and data["costo_estimado"] > 0

    fetched = client.get("/solicitudes/sol-1")
    assert fetched.status_code == 200
    assert fetched.json() == data


def test_reposting_same_id_updates_the_analysis(client):
    client.post("/solicitudes/analizar", json={"id": "sol-1", "texto": "primero", "cliente_id": "cli-1"})
    client.post("/solicitudes/analizar", json={"id": "sol-1", "texto": "segundo", "cliente_id": "cli-1"})

    assert client.get("/solicitudes/sol-1").json()["texto"] == "segundo"


def test_get_unknown_id_returns_404(client):
    assert client.get("/solicitudes/no-existe").status_code == 404


def test_invalid_model_output_returns_502(client):
    from langchain_core.language_models import FakeListChatModel

    from app.main import app, get_model

    app.dependency_overrides[get_model] = lambda: FakeListChatModel(responses=["no es json"])

    response = client.post("/solicitudes/analizar", json={"id": "sol-x", "texto": "hola", "cliente_id": "cli-1"})

    assert response.status_code == 502
    assert client.get("/solicitudes/sol-x").status_code == 404
