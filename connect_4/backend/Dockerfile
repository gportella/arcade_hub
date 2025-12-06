# syntax=docker/dockerfile:1.6

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CONNECT4_DATA_DIR=/app/backend/data \
    CONNECT4_DB_URL=sqlite:////app/backend/data/connect4.db

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

RUN mkdir -p "$CONNECT4_DATA_DIR"

EXPOSE 8000

VOLUME ["/app/backend/data"]

CMD ["uvicorn", "connect4.app:app", "--host", "0.0.0.0", "--port", "8000"]
