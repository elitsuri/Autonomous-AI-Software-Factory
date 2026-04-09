from dataclasses import dataclass

import httpx


@dataclass
class PullRequest:
    number: int
    url: str
    title: str


class GitHubPullRequestClient:
    def __init__(self, *, token: str, repository: str) -> None:
        self.token = token
        self.repository = repository

    async def create_pull_request(
        self,
        *,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        draft: bool = True,
    ) -> PullRequest:
        url = f"https://api.github.com/repos/{self.repository}/pulls"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return PullRequest(number=int(data["number"]), url=str(data["html_url"]), title=str(data["title"]))

