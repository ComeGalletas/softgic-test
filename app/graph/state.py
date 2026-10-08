import operator
from typing import Annotated, Any, TypedDict

from app.schemas import Clasificacion


class AnalisisState(TypedDict, total=False):
    id: str
    texto: str
    cliente_id: str
    clasificacion: Clasificacion
    cliente_info: dict[str, Any] | None
    respuesta: str
    # Each LLM node returns its own usage; the reducer sums them across the run.
    tokens_entrada: Annotated[int, operator.add]
    tokens_salida: Annotated[int, operator.add]
