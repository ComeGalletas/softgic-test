import json
from typing import TypeVar

from langchain_core.language_models import BaseChatModel, FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.tokens import count_usage

T = TypeVar("T", bound=BaseModel)

# Canned responses for the fake model, in call order: classification, then reply.
FAKE_RESPONSES = [
    json.dumps({"categoria": "tecnico", "prioridad": "alta"}),
    json.dumps(
        {
            "respuesta": "Hola, gracias por escribirnos. Ya estamos revisando tu caso "
            "y te contactaremos en breve con una solución."
        },
        ensure_ascii=False,
    ),
]


def get_llm(settings: Settings | None = None) -> BaseChatModel:
    """Real OpenAI model when OPENAI_API_KEY is set; otherwise a fake model with fixed JSON responses.

    The fake model keeps an internal response cursor, so a fresh instance is returned per call to keep
    each analysis seeing the responses in the expected order.
    """
    settings = settings or get_settings()
    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)
    return FakeListChatModel(responses=FAKE_RESPONSES)


def invoke_structured(llm: BaseChatModel, schema: type[T], messages: list[BaseMessage]) -> tuple[T, int, int]:
    """Call the model and return (parsed output, input tokens, output tokens).

    Models with native structured output use it; models without it (the fake one) get the parser's
    format instructions in the prompt and their JSON answer is validated with Pydantic. Either way the
    caller receives a validated `schema` instance.
    """
    try:
        structured = llm.with_structured_output(schema, include_raw=True)
    except NotImplementedError:
        structured = None

    if structured is not None:
        result = structured.invoke(messages)
        if result["parsing_error"] is not None:
            raise result["parsing_error"]
        tokens_in, tokens_out = count_usage(messages, result["raw"])
        return result["parsed"], tokens_in, tokens_out

    parser = PydanticOutputParser(pydantic_object=schema)
    prompt = [*messages, SystemMessage(content=parser.get_format_instructions())]
    raw: AIMessage = llm.invoke(prompt)
    tokens_in, tokens_out = count_usage(prompt, raw)
    return parser.parse(raw.content), tokens_in, tokens_out
