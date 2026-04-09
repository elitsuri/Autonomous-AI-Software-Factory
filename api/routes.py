from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agents.factory import AgentFactory
from api.dependencies import Principal, get_current_principal, get_security_service, get_session, require_role
from core.events import EventBus
from core.security import SecurityService
from domain.models import FactoryRunRequest, FactoryRunResult, ProjectSpec, PromptContext, Role
from infrastructure.git_service import GitClient, GitUnavailable
from infrastructure.github_client import GitHubPullRequestClient
from infrastructure.metrics import record_agent, record_factory_run
from infrastructure.repositories import AgentRunRepository, FactoryRunRepository, UserRepository
from infrastructure.tasks import run_pipeline_task
from orchestration.pipeline import FactoryOrchestrator
from plugins.runner import PluginRunner
from services.analyzer import CodeAnalyzer
from services.git_workflow import SmartCommitService
from services.project_generator import ProjectGenerator
from services.prompt_engine import ContextPromptStrategy, PromptIntelligenceEngine
from services.self_improvement import SelfImprovementService

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class QueuedRunResponse(BaseModel):
    task_id: str
    status_url: str


class PromptCompileResponse(BaseModel):
    version: str
    cache_key: str
    token_budget_hint: int
    text: str


class PullRequestCreateRequest(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    body: str = Field(min_length=1, max_length=10_000)
    head_branch: str = Field(min_length=1, max_length=200)
    base_branch: str | None = None
    draft: bool = True


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "autonomous-ai-software-factory"}


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    security_service: Annotated[SecurityService, Depends(get_security_service)],
) -> TokenResponse:
    repo = UserRepository(session)
    if await repo.find_by_email(payload.email) is not None:
        raise HTTPException(status_code=409, detail="user already exists")
    roles = [Role.ADMIN.value] if not await repo.has_users() else [Role.VIEWER.value]
    user = await repo.create(
        email=payload.email,
        password_hash=security_service.hash_password(payload.password),
        roles=roles,
    )
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="user already exists") from exc

    token = security_service.create_access_token(subject=user.email, roles=user.roles)
    return TokenResponse(access_token=token)


@router.post("/auth/token", response_model=TokenResponse)
async def token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
    security_service: Annotated[SecurityService, Depends(get_security_service)],
) -> TokenResponse:
    user = await UserRepository(session).find_by_email(form.username)
    if user is None or not user.is_active or not security_service.verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return TokenResponse(access_token=security_service.create_access_token(subject=user.email, roles=user.roles))


@router.post("/factory/runs", response_model=FactoryRunResult)
async def run_factory(
    payload: FactoryRunRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_role(Role.OPERATOR))],
) -> FactoryRunResult:
    plugins = PluginRunner(request.app.state.plugin_loader.discover(), request.app.state.settings.generated_projects_dir)
    prepared_spec = await plugins.prepare_spec(payload.spec)
    payload = payload.model_copy(update={"spec": prepared_spec})
    orchestrator = _orchestrator_for_request(request, session)
    result = await orchestrator.run(payload)
    result = await plugins.finalize_result(result)
    if payload.commit_changes:
        settings = request.app.state.settings
        git = GitClient(
            Path(result.output_dir),
            author_name=settings.git_author_name,
            author_email=settings.git_author_email,
        )
        try:
            commit = await SmartCommitService(git).commit_factory_run(result)
        except GitUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        result.deployment["git"] = {"commit_message": commit.message, "sha": commit.sha}
        await FactoryRunRepository(session).save_factory_run(result)
    for agent_result in result.agent_results:
        record_agent(agent_result.agent_name.value, agent_result.status.value, agent_result.runtime_seconds)
    record_factory_run(result.status.value)
    return result


@router.post("/factory/jobs", response_model=QueuedRunResponse, status_code=202)
async def queue_factory_run(
    spec: ProjectSpec,
    request: Request,
    principal: Annotated[Principal, Depends(require_role(Role.OPERATOR))],
) -> QueuedRunResponse:
    task = run_pipeline_task.delay(spec.model_dump(mode="json"), str(request.app.state.settings.generated_projects_dir))
    return QueuedRunResponse(task_id=task.id, status_url=f"/factory/jobs/{task.id}")


@router.get("/factory/runs/recent", response_model=list[FactoryRunResult])
async def recent_runs(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[FactoryRunResult]:
    return await FactoryRunRepository(session).list_recent_runs()


@router.get("/agents/status")
async def agent_status(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> dict:
    results = await AgentRunRepository(session).list_recent_agent_results()
    return {"agents": [result.model_dump(mode="json") for result in results]}


@router.get("/plugins")
async def plugins(request: Request, principal: Annotated[Principal, Depends(get_current_principal)]) -> dict:
    loaded = request.app.state.plugin_loader.discover()
    return {"plugins": [{"name": plugin.name, "version": plugin.version} for plugin in loaded]}


@router.post("/prompts/compile", response_model=PromptCompileResponse)
async def compile_prompt(
    context: PromptContext,
    request: Request,
    principal: Annotated[Principal, Depends(require_role(Role.OPERATOR))],
) -> PromptCompileResponse:
    cache = request.app.state.prompt_cache
    engine = PromptIntelligenceEngine(ContextPromptStrategy(), cache=cache)
    compiled = await engine.compile(context)
    return PromptCompileResponse(**compiled.model_dump(mode="json"))


@router.get("/git/history")
async def git_history(
    principal: Annotated[Principal, Depends(require_role(Role.OPERATOR))],
) -> dict:
    try:
        history = await GitClient(Path.cwd()).recent_history()
    except GitUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"history": history}


@router.post("/git/pull-requests", status_code=201)
async def create_pull_request(
    payload: PullRequestCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_role(Role.OPERATOR))],
) -> dict:
    settings = request.app.state.settings
    if not settings.github_repository or not settings.github_token:
        raise HTTPException(status_code=503, detail="GITHUB_REPOSITORY and GITHUB_TOKEN are required for PR creation")
    client = GitHubPullRequestClient(token=settings.github_token, repository=settings.github_repository)
    pull_request = await client.create_pull_request(
        title=payload.title,
        body=payload.body,
        head_branch=payload.head_branch,
        base_branch=payload.base_branch or settings.github_default_base,
        draft=payload.draft,
    )
    return {"number": pull_request.number, "url": pull_request.url, "title": pull_request.title}


def _orchestrator_for_request(request: Request, session: AsyncSession) -> FactoryOrchestrator:
    analyzer = CodeAnalyzer(request.app.state.settings)
    improver = SelfImprovementService(analyzer)
    agent_factory = AgentFactory(generator=ProjectGenerator(), analyzer=analyzer, improver=improver)
    event_bus = EventBus()
    event_bus.subscribe("*", request.app.state.runtime.observe_event)
    return FactoryOrchestrator(
        agent_factory.pipeline(),
        event_bus=event_bus,
        agent_repository=AgentRunRepository(session),
        run_repository=FactoryRunRepository(session),
    )
