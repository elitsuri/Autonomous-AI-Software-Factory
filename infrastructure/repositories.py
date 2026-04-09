from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import AgentResult, FactoryRunResult
from infrastructure.orm import AgentRunRow, FactoryRunRow, UserRow


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, email: str, password_hash: str, roles: list[str]) -> UserRow:
        row = UserRow(email=email.lower(), password_hash=password_hash, roles=roles)
        self.session.add(row)
        await self.session.flush()
        return row

    async def find_by_email(self, email: str) -> UserRow | None:
        result = await self.session.scalar(select(UserRow).where(UserRow.email == email.lower()))
        return result

    async def has_users(self) -> bool:
        count = await self.session.scalar(select(func.count(UserRow.id)))
        return bool(count)


class AgentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_agent_result(self, result: AgentResult) -> None:
        row = AgentRunRow(
            id=result.run_id,
            agent_name=result.agent_name.value,
            status=result.status.value,
            runtime_seconds=result.runtime_seconds,
            payload=result.model_dump(mode="json"),
        )
        await self.session.merge(row)
        await self.session.flush()

    async def list_recent_agent_results(self, limit: int = 50) -> list[AgentResult]:
        rows = (
            await self.session.scalars(
                select(AgentRunRow).order_by(AgentRunRow.created_at.desc()).limit(limit)
            )
        ).all()
        return [AgentResult.model_validate(row.payload) for row in rows]


class FactoryRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_factory_run(self, result: FactoryRunResult) -> None:
        row = FactoryRunRow(
            id=result.id,
            project_name=result.spec.name,
            status=result.status.value,
            output_dir=result.output_dir,
            payload=result.model_dump(mode="json", exclude_computed_fields=True),
        )
        await self.session.merge(row)
        await self.session.flush()

    async def list_recent_runs(self, limit: int = 25) -> list[FactoryRunResult]:
        rows = (
            await self.session.scalars(
                select(FactoryRunRow).order_by(FactoryRunRow.created_at.desc()).limit(limit)
            )
        ).all()
        return [FactoryRunResult.model_validate(_clean_factory_payload(row.payload)) for row in rows]


def _clean_factory_payload(payload: dict) -> dict:
    cleaned = dict(payload)
    spec = cleaned.get("spec")
    if isinstance(spec, dict) and "package_name" in spec:
        cleaned["spec"] = {key: value for key, value in spec.items() if key != "package_name"}
    return cleaned
