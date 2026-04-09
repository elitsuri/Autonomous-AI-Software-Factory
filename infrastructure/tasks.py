import asyncio
from pathlib import Path

from agents.factory import AgentFactory
from domain.models import FactoryRunRequest, ProjectSpec
from infrastructure.celery_app import celery_app
from orchestration.pipeline import FactoryOrchestrator
from services.analyzer import CodeAnalyzer
from services.project_generator import ProjectGenerator
from services.self_improvement import SelfImprovementService


@celery_app.task(name="factory.run_pipeline")
def run_pipeline_task(spec_payload: dict, output_dir: str | None = None) -> dict:
    return asyncio.run(_run_pipeline(spec_payload, output_dir))


async def _run_pipeline(spec_payload: dict, output_dir: str | None) -> dict:
    analyzer = CodeAnalyzer()
    improver = SelfImprovementService(analyzer)
    factory = AgentFactory(generator=ProjectGenerator(), analyzer=analyzer, improver=improver)
    orchestrator = FactoryOrchestrator(factory.pipeline())
    request = FactoryRunRequest(
        spec=ProjectSpec.model_validate(spec_payload),
        output_dir=Path(output_dir) if output_dir else None,
    )
    result = await orchestrator.run(request)
    return result.model_dump(mode="json")

