import asyncio
from pathlib import Path


class GitUnavailable(RuntimeError):
    pass


class GitClient:
    def __init__(
        self,
        repo_path: Path,
        *,
        executable: str = "git",
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> None:
        self.repo_path = repo_path.resolve()
        self.executable = executable
        self.author_name = author_name
        self.author_email = author_email

    async def commit_all(self, message: str) -> str | None:
        await self.ensure_repository()
        await self.configure_identity()
        await self._run("add", "-A")
        diff = await self._run("status", "--porcelain")
        if not diff.strip():
            return None
        await self._run("commit", "-m", message)
        return (await self._run("rev-parse", "HEAD")).strip()

    async def recent_history(self, limit: int = 10) -> list[str]:
        output = await self._run("log", f"-{limit}", "--pretty=format:%h %ad %s", "--date=short")
        return [line for line in output.splitlines() if line.strip()]

    async def create_branch(self, branch_name: str) -> None:
        await self.ensure_repository()
        await self._run("checkout", "-B", branch_name)

    async def ensure_repository(self) -> None:
        self.repo_path.mkdir(parents=True, exist_ok=True)
        try:
            await self._run("rev-parse", "--is-inside-work-tree")
        except RuntimeError:
            await self._run("init", "-b", "main")

    async def configure_identity(self) -> None:
        if self.author_name:
            await self._run("config", "user.name", self.author_name)
        if self.author_email:
            await self._run("config", "user.email", self.author_email)

    async def _run(self, *args: str) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                self.executable,
                *args,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise GitUnavailable("git executable is not available in this runtime") from exc

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"git {' '.join(args)} failed: {message}")
        return stdout.decode("utf-8", errors="replace")
