FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken \
    DATABASE_URL=sqlite:////app/data/solicitudes.db

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install ".[postgres]" \
    # Bake the tokenizer into the image so token counting works without network access at runtime.
    && python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown appuser /app/data
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
