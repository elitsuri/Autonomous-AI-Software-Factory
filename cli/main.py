import asyncio
import json
from pathlib import Path

import typer

from agents.factory import AgentFactory
from core.logging import configure_logging
from domain.models import FactoryRunRequest, ProjectSpec
from orchestration.pipeline import FactoryOrchestrator
from services.analyzer import CodeAnalyzer
from services.project_generator import ProjectGenerator
from services.self_improvement import SelfImprovementService

app = typer.Typer(help="Autonomous AI Software Factory CLI", no_args_is_help=True)


def _build_orchestrator() -> FactoryOrchestrator:
    analyzer = CodeAnalyzer()
    improver = SelfImprovementService(analyzer)
    agent_factory = AgentFactory(generator=ProjectGenerator(), analyzer=analyzer, improver=improver)
    return FactoryOrchestrator(agent_factory.pipeline())


@app.command()
def scan(path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True)) -> None:
    """Scan Python code for correctness, performance, and maintainability risks."""
    report = asyncio.run(CodeAnalyzer().scan(path))
    typer.echo(report.model_dump_json(indent=2))
    if report.has_blockers:
        raise typer.Exit(code=2)


@app.command()
def generate(
    name: str = typer.Option(..., "--name", "-n"),
    summary: str = typer.Option(..., "--summary", "-s"),
    output_dir: Path = typer.Option(Path("workspaces"), "--output-dir", "-o"),
    frontend: str = typer.Option("htmx", "--frontend"),
) -> None:
    """Generate a complete FastAPI application."""
    spec = ProjectSpec(name=name, summary=summary, frontend=frontend)  # type: ignore[arg-type]
    result = asyncio.run(_build_orchestrator().run(FactoryRunRequest(spec=spec, output_dir=output_dir)))
    typer.echo(result.model_dump_json(indent=2))
    if result.status.value != "succeeded":
        raise typer.Exit(code=1)


@app.command()
def fix(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True),
    apply: bool = typer.Option(False, "--apply/--dry-run"),
) -> None:
    """Run self-improvement analysis and optional safe repairs."""
    analyzer = CodeAnalyzer()
    improver = SelfImprovementService(analyzer)
    report, summary = asyncio.run(improver.inspect_and_repair(path, apply=apply))
    typer.echo(json.dumps({"repair": summary.__dict__, "report": report.model_dump(mode="json")}, indent=2, default=str))
    if report.has_blockers:
        raise typer.Exit(code=2)


@app.command()
def analyze(path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True)) -> None:
    """Print a concise analysis report."""
    report = asyncio.run(CodeAnalyzer().scan(path))
    typer.echo(f"Scanned {report.scanned_files} Python files")
    for issue in report.issues:
        typer.echo(f"{issue.severity.value.upper()} {issue.path}:{issue.line} {issue.rule} - {issue.message}")


@app.command()
def deploy(project_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True)) -> None:
    """Print deployment commands for a generated project."""
    commands = [
        f"cd {project_dir.resolve()}",
        "docker compose up --build",
        "curl http://localhost:8000/health",
        "kubectl apply -f k8s/deployment.yaml",
    ]
    typer.echo("\n".join(commands))


@app.command()
def report(path: Path = typer.Argument(Path("."), exists=True, file_okay=False, dir_okay=True)) -> None:
    """Write a JSON report under .factory/analysis-report.json."""
    analyzer = CodeAnalyzer()
    improver = SelfImprovementService(analyzer)
    report_model, summary = asyncio.run(improver.inspect_and_repair(path, apply=False))
    typer.echo(summary.report_path)
    typer.echo(f"issues={len(report_model.issues)} scanned_files={report_model.scanned_files}")


def main() -> None:
    configure_logging()
    app()


if __name__ == "__main__":
    main()

