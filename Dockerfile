FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
COPY agents ./agents
COPY api ./api
COPY cli ./cli
COPY core ./core
COPY domain ./domain
COPY infrastructure ./infrastructure
COPY orchestration ./orchestration
COPY plugins ./plugins
COPY services ./services

RUN pip install --upgrade pip \
    && pip install .

RUN useradd --create-home --shell /usr/sbin/nologin factory \
    && mkdir -p /app/workspaces /app/external_plugins \
    && chown -R factory:factory /app

USER factory
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

