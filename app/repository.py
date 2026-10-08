from typing import Any

from sqlalchemy.orm import Session

from app.models import Analisis


def save_analisis(session: Session, data: dict[str, Any]) -> Analisis:
    """Insert or update (by request id) an analysis and return the stored row."""
    row = session.get(Analisis, data["id"])
    if row is None:
        row = Analisis(**data)
        session.add(row)
    else:
        for field, value in data.items():
            setattr(row, field, value)
    session.commit()
    session.refresh(row)
    return row


def get_analisis(session: Session, analisis_id: str) -> Analisis | None:
    return session.get(Analisis, analisis_id)
