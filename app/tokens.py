from collections.abc import Sequence
from functools import lru_cache

from langchain_core.messages import AIMessage, BaseMessage


@lru_cache
def _encoding():
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


def count_text_tokens(text: str) -> int:
    """Count tokens with tiktoken; fall back to a word-based estimate if the encoding is unavailable
    (tiktoken downloads it on first use, which fails offline)."""
    try:
        return len(_encoding().encode(text))
    except Exception:
        return round(len(text.split()) * 1.3)


def _message_text(message: BaseMessage) -> str:
    return message.content if isinstance(message.content, str) else str(message.content)


def count_usage(prompt: Sequence[BaseMessage], completion: AIMessage) -> tuple[int, int]:
    """Return (input_tokens, output_tokens): reported usage if the model gives it, otherwise an estimate."""
    usage = getattr(completion, "usage_metadata", None)
    if usage:
        return usage["input_tokens"], usage["output_tokens"]
    tokens_in = sum(count_text_tokens(_message_text(m)) for m in prompt)
    tokens_out = count_text_tokens(_message_text(completion))
    return tokens_in, tokens_out


def estimate_cost(tokens_in: int, tokens_out: int, price_in_per_million: float, price_out_per_million: float) -> float:
    return tokens_in / 1e6 * price_in_per_million + tokens_out / 1e6 * price_out_per_million
