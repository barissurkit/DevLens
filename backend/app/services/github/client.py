import httpx

from app.config import Settings
from app.schemas.github import GitHubRepository, GitHubUser

DEFAULT_TIMEOUT_SECONDS = 10.0
GITHUB_API_VERSION = "2026-03-10"
REPOSITORIES_PER_PAGE = 100
MAX_REPOSITORY_PAGES = 10


class GitHubClient:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = settings.github_api_base_url.rstrip("/")
        self._headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DevLens/0.1.0",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        self._transport = transport

        if settings.github_token:
            self._headers["Authorization"] = f"Bearer {settings.github_token}"

    def _create_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=httpx.Timeout(DEFAULT_TIMEOUT_SECONDS),
            transport=self._transport,
        )

    async def get_user(self, username: str) -> GitHubUser:
        async with self._create_http_client() as client:
            response = await client.get(f"users/{username}")
            response.raise_for_status()

        return GitHubUser.model_validate(response.json())

    async def get_repositories(
        self,
        username: str,
    ) -> list[GitHubRepository]:
        repositories: list[GitHubRepository] = []

        async with self._create_http_client() as client:
            for page in range(1, MAX_REPOSITORY_PAGES + 1):
                response = await client.get(
                    f"users/{username}/repos",
                    params={
                        "per_page": REPOSITORIES_PER_PAGE,
                        "page": page,
                    },
                )
                response.raise_for_status()

                payload = response.json()

                if not isinstance(payload, list):
                    raise TypeError("GitHub repositories response must be a JSON array.")

                repositories.extend(GitHubRepository.model_validate(item) for item in payload)

                if "next" not in response.links:
                    return repositories

        raise RuntimeError("GitHub repository pagination limit exceeded.")
