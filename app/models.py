from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Analisis(Base):
    __tablename__ = "analisis"

    # The client-supplied request id is the primary key, so re-posting the same id updates the row.
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String(100), index=True)
    texto: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(20))
    prioridad: Mapped[str] = mapped_column(String(10))
    respuesta_sugerida: Mapped[str] = mapped_column(Text)
    cliente_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0)
    tokens_salida: Mapped[int] = mapped_column(Integer, default=0)
    costo_estimado: Mapped[float] = mapped_column(Float, default=0.0)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
