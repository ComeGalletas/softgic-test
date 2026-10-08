from functools import partial
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from app.crm_client import CRMClient
from app.graph.nodes import clasificar, consultar_cliente, proponer_respuesta
from app.graph.state import AnalisisState


def _route_after_clasificar(state: AnalisisState) -> Literal["consultar_cliente", "proponer_respuesta"]:
    return "consultar_cliente" if state["clasificacion"].prioridad == "alta" else "proponer_respuesta"


def build_graph(llm: BaseChatModel, crm_client: CRMClient):
    """Compile the analysis graph; the model and CRM client are injected so tests can swap them."""
    graph = StateGraph(AnalisisState)
    graph.add_node("clasificar", partial(clasificar, llm=llm))
    graph.add_node("consultar_cliente", partial(consultar_cliente, crm_client=crm_client))
    graph.add_node("proponer_respuesta", partial(proponer_respuesta, llm=llm))

    graph.add_edge(START, "clasificar")
    graph.add_conditional_edges("clasificar", _route_after_clasificar)
    graph.add_edge("consultar_cliente", "proponer_respuesta")
    graph.add_edge("proponer_respuesta", END)
    return graph.compile()
