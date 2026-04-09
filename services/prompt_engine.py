import hashlib
import json
from dataclasses import dataclass

from domain.models import CompiledPrompt, PromptContext
from domain.ports import CachePort, PromptStrategy


class ContextPromptStrategy(PromptStrategy):
    """Strategy that turns code context into a compact engineering prompt."""

    async def compile(self, context: PromptContext) -> CompiledPrompt:
        payload = context.model_dump(mode="json")
        cache_key = _stable_hash(payload)
        file_section = "\n\n".join(
            f"### {path}\n```text\n{content[:4_000]}\n```"
            for path, content in sorted(context.files.items())
        )
        constraints = "\n".join(f"- {constraint}" for constraint in context.constraints)
        agent = context.agent_name.value if context.agent_name else "general"
        text = (
            f"You are the {agent} agent in the Autonomous AI Software Factory.\n"
            f"Task:\n{context.task}\n\n"
            f"Project:\n{context.project_summary}\n\n"
            f"Constraints:\n{constraints or '- Keep changes focused, tested, observable, and reversible.'}\n\n"
            f"Context files:\n{file_section or 'No files were attached.'}\n\n"
            "Return an implementation-oriented answer with risks, validation, and changed artifacts."
        )
        version = "context-prompt-v1"
        return CompiledPrompt(
            version=version,
            cache_key=f"prompt:{version}:{cache_key}",
            text=text,
            token_budget_hint=max(1_000, len(text) // 3),
        )


@dataclass
class PromptIntelligenceEngine:
    strategy: PromptStrategy
    cache: CachePort | None = None
    cache_seconds: int = 3_600

    async def compile(self, context: PromptContext) -> CompiledPrompt:
        draft = await self.strategy.compile(context)
        if self.cache is None:
            return draft

        cached = await self.cache.get_text(draft.cache_key)
        if cached is not None:
            return CompiledPrompt.model_validate_json(cached)

        await self.cache.set_text(draft.cache_key, draft.model_dump_json(), ttl_seconds=self.cache_seconds)
        return draft


def _stable_hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

