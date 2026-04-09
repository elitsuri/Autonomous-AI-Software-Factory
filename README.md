# Autonomous AI Software Factory

A production-oriented multi-agent factory for generating, reviewing, repairing, packaging, and operating software projects.

The factory runs five rerunnable agents: Architect, Developer, Reviewer, Debugger, and DevOps. Each run produces typed input/output, logs, timestamps, runtime, dashboard state, metrics, and a persisted JSON payload when the API database is enabled.

## What Is Implemented

- FastAPI control plane with health, auth, an animated control-room dashboard, metrics, factory runs, queued jobs, prompts, plugins, Git history, and GitHub PR creation endpoints.
- Typer CLI with `scan`, `generate`, `fix`, `analyze`, `deploy`, and `report`.
- Code generator for complete FastAPI services with PostgreSQL schema, HTMX UI by default, optional React/Vite UI, tests, Dockerfile, Compose, Kubernetes Deployment and Service.
- Self-improvement service that scans Python AST, writes `.factory/analysis-report.json`, detects parse errors, broad exceptions, prints, large functions, and blocking sleeps in async code, and can safely repair `time.sleep` inside async functions.
- Prompt intelligence engine with strategy-based prompt compilation, deterministic versioned cache keys, Redis or in-memory cache adapters.
- Plugin SDK and dynamic loader for `external_plugins/<plugin-name>/plugin.py`.
- Git workflow adapters for init, identity, automatic add/commit/history, smart commit messages, and GitHub REST pull request creation.
- Docker Compose stack with API, Celery worker, PostgreSQL, Redis, Prometheus, and Grafana.

## Folder Structure

```text
agents/              multi-agent implementations
api/                 FastAPI app, routes, dashboard, auth dependencies
cli/                 Typer command line interface
core/                config, security, logging, DI container, event bus
domain/              Pydantic v2 models and hexagonal ports
infrastructure/      SQLAlchemy, Redis, Celery, Git, GitHub, metrics adapters
orchestration/       factory pipeline and runtime state
plugins/             plugin SDK, loader, runner
services/            analyzer, generator, repair, prompt, commit services
tests/               unit, integration, and end-to-end tests
observability/       Prometheus and Grafana provisioning
```

## Local Run

Create `.env` from the example:

```bash
cp .env.example .env
```

Start the platform:

```bash
docker compose up --build
```

Open:

- Factory dashboard: http://localhost:8000
- Live dashboard telemetry JSON: http://localhost:8000/dashboard/snapshot
- API docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## First API Session

Register the first user. The first registered account receives the `admin` role.

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"operator@example.com","password":"correct-horse-battery-staple"}'
```

Store the returned token:

```bash
TOKEN="<access_token>"
```

Run the factory synchronously:

```bash
curl -s -X POST http://localhost:8000/factory/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {
      "name": "ops-portal",
      "summary": "Internal operations portal for tracking work items and service readiness.",
      "frontend": "htmx",
      "features": ["work item API", "server-rendered dashboard", "postgres persistence"]
    },
    "output_dir": "/app/workspaces",
    "apply_repairs": true,
    "commit_changes": false
  }'
```

Queue a background generation job:

```bash
curl -s -X POST http://localhost:8000/factory/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "field-crm",
    "summary": "Small CRM service for field teams with durable work-item tracking.",
    "frontend": "react",
    "features": ["customer task queue", "react client", "postgres persistence"]
  }'
```

## CLI

Install for local development:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Generate a real service:

```bash
factory generate \
  --name inventory-hub \
  --summary "Inventory coordination service for warehouse operators." \
  --frontend htmx
```

Scan and repair a project:

```bash
factory scan ./workspaces/inventory-hub
factory fix ./workspaces/inventory-hub --apply
factory report ./workspaces/inventory-hub
```

Run a generated service:

```bash
cd workspaces/inventory-hub
docker compose up --build
```

## Plugins

Create `external_plugins/naming/plugin.py`:

```python
from plugins.sdk import PluginContext


class NamingPlugin:
    name = "naming"
    version = "1.0.0"

    async def on_project_spec(self, spec, context: PluginContext):
        if "audit log" not in spec.features:
            return spec.model_copy(update={"features": [*spec.features, "audit log"]})
        return spec

    async def on_scan_report(self, report, context: PluginContext):
        return report

    async def on_factory_result(self, result, context: PluginContext):
        result.deployment["plugin_naming"] = {"applied": True}
        return result


plugin = NamingPlugin()
```

The API loads plugins dynamically from `PLUGIN_DIRS`.

## GitHub Pull Requests

Set these in `.env` when PR creation is desired:

```bash
GITHUB_REPOSITORY=owner/repo
GITHUB_TOKEN=github_pat_or_actions_token
GITHUB_DEFAULT_BASE=main
```

Create a PR for a branch that is already pushed:

```bash
curl -s -X POST http://localhost:8000/git/pull-requests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Generate ops portal",
    "body": "Generated by the factory, reviewed by the reviewer agent, packaged by DevOps agent.",
    "head_branch": "factory/ops-portal",
    "draft": true
  }'
```

## Test

```bash
pytest
ruff check .
```

The pytest command enforces 90% coverage for the core factory packages.
