from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis
from redis.exceptions import RedisError

from api.dashboard import dashboard_snapshot, render_dashboard
from api.routes import router
from core.config import get_settings
from core.logging import configure_logging
from core.security import SecurityService
from infrastructure.cache import InMemoryCache, RedisCache
from infrastructure.database import create_engine, create_schema, create_session_factory
from infrastructure.metrics import metrics_response
from infrastructure.rate_limit import SlidingWindowRateLimitMiddleware
from infrastructure.repositories import AgentRunRepository, FactoryRunRepository
from orchestration.runtime import RuntimeState
from plugins.loader import PluginLoader


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging("DEBUG" if settings.debug else "INFO")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.runtime = RuntimeState()
        app.state.plugin_loader = PluginLoader(settings.plugin_dirs)
        app.state.security = SecurityService(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            token_minutes=settings.jwt_access_token_minutes,
            password_iterations=settings.password_pbkdf2_iterations,
        )
        app.state.redis = Redis.from_url(str(settings.redis_url), decode_responses=False)
        try:
            await app.state.redis.ping()
            app.state.prompt_cache = RedisCache(app.state.redis)
        except RedisError:
            app.state.prompt_cache = InMemoryCache()
        await create_schema(engine)
        try:
            yield
        finally:
            await app.state.redis.aclose()
            await engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.prompt_cache = InMemoryCache()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SlidingWindowRateLimitMiddleware,
        requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    app.mount("/static", StaticFiles(directory="api/static"), name="static")
    app.include_router(router)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        return HTMLResponse(render_dashboard())

    @app.get("/dashboard/snapshot")
    async def dashboard_state() -> dict:
        async for session in get_session_from_state(app):
            runs = await FactoryRunRepository(session).list_recent_runs()
            agents = await AgentRunRepository(session).list_recent_agent_results()
        return dashboard_snapshot(runs=runs, agents=agents)

    @app.get("/metrics")
    async def metrics():
        return metrics_response()

    return app


async def get_session_from_state(app: FastAPI):
    async with app.state.session_factory() as session:
        yield session


app = create_app()
