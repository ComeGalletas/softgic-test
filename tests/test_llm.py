import pytest
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from app.llm import invoke_structured
from app.schemas import Clasificacion


class StructuredModelStub:
    """Mimics a model with native structured output whose answer fails validation."""

    def with_structured_output(self, schema, include_raw=False):
        return RunnableLambda(
            lambda _: {"raw": AIMessage(content="{}"), "parsed": None, "parsing_error": ValueError("bad output")}
        )


def test_native_structured_output_errors_are_normalized():
    with pytest.raises(OutputParserException):
        invoke_structured(StructuredModelStub(), Clasificacion, [HumanMessage(content="hola")])


def test_fake_model_invalid_json_raises_output_parser_exception():
    from langchain_core.language_models import FakeListChatModel

    with pytest.raises(OutputParserException):
        invoke_structured(FakeListChatModel(responses=["no es json"]), Clasificacion, [HumanMessage(content="hola")])
