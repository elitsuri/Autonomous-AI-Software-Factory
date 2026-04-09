from dataclasses import dataclass

from domain.models import FactoryRunResult
from domain.ports import GitPort


@dataclass
class CommitOutcome:
    message: str
    sha: str | None


class SmartCommitService:
    def __init__(self, git: GitPort) -> None:
        self.git = git

    async def commit_factory_run(self, result: FactoryRunResult) -> CommitOutcome:
        message = self.build_message(result)
        sha = await self.git.commit_all(message)
        return CommitOutcome(message=message, sha=sha)

    def build_message(self, result: FactoryRunResult) -> str:
        files = 0
        for agent_result in result.agent_results:
            files += len(agent_result.output.get("written_files", []))
        summary = result.spec.summary.rstrip(".")
        return f"Generate {result.spec.name} service\n\n{summary}.\n\nFactory wrote {files} files and finished with status {result.status.value}."

