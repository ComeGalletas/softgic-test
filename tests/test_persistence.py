from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import create_tables
from app.repository import save_analisis


def test_missing_customer_info_is_stored_as_sql_null():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    create_tables(engine)
    base = {
        "cliente_id": "cli-1",
        "texto": "consulta",
        "categoria": "otro",
        "prioridad": "baja",
        "respuesta_sugerida": "ok",
        "tokens_entrada": 1,
        "tokens_salida": 1,
        "costo_estimado": 0.0,
    }

    with Session(engine) as session:
        save_analisis(session, {**base, "id": "sin-cliente", "cliente_info": None})
        save_analisis(session, {**base, "id": "con-cliente", "cliente_info": {"nombre": "Ana"}})
        ids = session.execute(text("SELECT id FROM analisis WHERE cliente_info IS NULL")).scalars().all()

    assert ids == ["sin-cliente"]
