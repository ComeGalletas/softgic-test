from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Categoria = Literal["facturacion", "tecnico", "comercial", "otro"]
Prioridad = Literal["alta", "media", "baja"]


class Clasificacion(BaseModel):
    """Structured output of the classification step."""

    categoria: Categoria = Field(description="Categoría de la solicitud")
    prioridad: Prioridad = Field(description="Prioridad de la solicitud")


class RespuestaSugerida(BaseModel):
    """Structured output of the reply step."""

    respuesta: str = Field(description="Respuesta sugerida para enviar al cliente")


class AnalizarRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    texto: str = Field(min_length=1, max_length=10_000)
    cliente_id: str = Field(min_length=1, max_length=100)


class AnalisisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cliente_id: str
    texto: str
    categoria: Categoria
    prioridad: Prioridad
    respuesta_sugerida: str
    cliente_info: dict[str, Any] | None
    tokens_entrada: int
    tokens_salida: int
    costo_estimado: float
    creado_en: datetime
