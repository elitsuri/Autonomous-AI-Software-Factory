from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

AGENT_RUNS = Counter("factory_agent_runs_total", "Agent runs by agent and status", ["agent", "status"])
FACTORY_RUNS = Counter("factory_runs_total", "Factory pipeline runs by status", ["status"])
AGENT_RUNTIME = Histogram("factory_agent_runtime_seconds", "Agent runtime by agent", ["agent"])


def record_agent(agent: str, status: str, runtime_seconds: float) -> None:
    AGENT_RUNS.labels(agent=agent, status=status).inc()
    AGENT_RUNTIME.labels(agent=agent).observe(runtime_seconds)


def record_factory_run(status: str) -> None:
    FACTORY_RUNS.labels(status=status).inc()


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

