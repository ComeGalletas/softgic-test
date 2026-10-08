import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crm_client import CRMClient, HttpCRMClient
from app.db import create_tables, get_session
from app.graph import build_graph
from app.llm import get_llm
from app.repository import get_analisis, save_analisis
from app.schemas import AnalisisResponse, AnalizarRequest
from app.tokens import estimate_cost

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    app.state.crm_client = HttpCRMClient.from_settings(get_settings())
    yield
    app.state.crm_client.close()


app = FastAPI(title="Análisis de solicitudes", lifespan=lifespan)


def get_crm_client(request: Request) -> CRMClient:
    return request.app.state.crm_client


def get_model() -> BaseChatModel:
    return get_llm()


SessionDep = Annotated[Session, Depends(get_session)]


# Sync endpoints: the graph, the CRM client and SQLAlchemy are blocking, so FastAPI runs them in its threadpool.
@app.post("/solicitudes/analizar", response_model=AnalisisResponse)
def analizar(
    body: AnalizarRequest,
    session: SessionDep,
    llm: Annotated[BaseChatModel, Depends(get_model)],
    crm_client: Annotated[CRMClient, Depends(get_crm_client)],
) -> AnalisisResponse:
    graph = build_graph(llm, crm_client)
    try:
        result = graph.invoke(body.model_dump())
    except OutputParserException as exc:
        logger.error("Model output failed validation for id=%s: %s", body.id, exc)
        raise HTTPException(status_code=502, detail="El modelo devolvió una respuesta inválida") from exc

    settings = get_settings()
    tokens_in, tokens_out = result["tokens_entrada"], result["tokens_salida"]
    row = save_analisis(
        session,
        {
            "id": body.id,
            "cliente_id": body.cliente_id,
            "texto": body.texto,
            "categoria": result["clasificacion"].categoria,
            "prioridad": result["clasificacion"].prioridad,
            "respuesta_sugerida": result["respuesta"],
            "cliente_info": result.get("cliente_info"),
            "tokens_entrada": tokens_in,
            "tokens_salida": tokens_out,
            "costo_estimado": estimate_cost(
                tokens_in, tokens_out, settings.precio_input_por_millon, settings.precio_output_por_millon
            ),
        },
    )
    return AnalisisResponse.model_validate(row)


@app.get("/solicitudes/{id}", response_model=AnalisisResponse)
def obtener(id: str, session: SessionDep) -> AnalisisResponse:
    row = get_analisis(session, id)
    if row is None:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return AnalisisResponse.model_validate(row)
