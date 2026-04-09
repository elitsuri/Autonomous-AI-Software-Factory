import pytest

from domain.models import AgentName, PromptContext
from infrastructure.cache import InMemoryCache
from services.prompt_engine import ContextPromptStrategy, PromptIntelligenceEngine


@pytest.mark.asyncio
async def test_prompt_engine_compiles_versioned_cached_prompt() -> None:
    cache = InMemoryCache()
    engine = PromptIntelligenceEngine(ContextPromptStrategy(), cache=cache)
    context = PromptContext(
        task="review the payment handler",
        project_summary="Billing API",
        files={"payments.py": "async def charge():\n    return 'paid'\n"},
        constraints=["prefer async SQLAlchemy"],
        agent_name=AgentName.REVIEWER,
    )

    first = await engine.compile(context)
    second = await engine.compile(context)

    assert first.cache_key == second.cache_key
    assert first.version == "context-prompt-v1"
    assert "reviewer agent" in first.text
    assert "payments.py" in first.text
    assert await cache.get_text(first.cache_key) is not None

