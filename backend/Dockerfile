FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

RUN pip install --upgrade pip \
    && pip install -e . \
    && chmod +x /app/backend/scripts/start.sh

EXPOSE 8000

CMD ["./scripts/start.sh"]
