import base64
import binascii

import httpx

from app.config import Settings
from app.schemas.github import GitHubFileContent, GitHubRepository, GitHubUser

DEFAULT_TIMEOUT_SECONDS = 10.0
GITHUB_API_VERSION = "2026-03-10"
REPOSITORIES_PER_PAGE = 100
MAX_REPOSITORY_PAGES = 10
MAX_FILE_SIZE_BYTES = 1_048_576

IMPORTANT_REPOSITORY_FILE_PATHS: tuple[str, ...] = (
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
)


def decode_github_file_content(content: str, encoding: str) -> str:
    if encoding != "base64":
        raise ValueError(f"Unsupported GitHub file encoding: {encoding}")

    compact_content = "".join(content.split())

    try:
        decoded_bytes = base64.b64decode(compact_content, validate=True)
        return decoded_bytes.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as error:
        raise ValueError("GitHub file content is not valid Base64-encoded UTF-8 text.") from error


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

    async def get_repository_tree_paths(
        self,
        owner: str,
        repository: str,
        ref: str,
    ) -> list[str]:
        async with self._create_http_client() as client:
            response = await client.get(
                f"repos/{owner}/{repository}/git/trees/{ref}",
                params={"recursive": "1"},
            )
            response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise TypeError("GitHub tree response must be a JSON object.")

        truncated = payload.get("truncated")

        if not isinstance(truncated, bool):
            raise TypeError("GitHub tree response must include a boolean truncated field.")

        if truncated:
            raise RuntimeError("GitHub repository tree response is truncated.")

        tree_entries = payload.get("tree")

        if not isinstance(tree_entries, list):
            raise TypeError("GitHub tree response must include a tree array.")

        paths: list[str] = []

        for entry in tree_entries:
            if not isinstance(entry, dict):
                raise TypeError("GitHub tree entries must be JSON objects.")

            if entry.get("type") != "blob":
                continue

            path = entry.get("path")

            if not isinstance(path, str):
                raise TypeError("GitHub file tree entry must include a string path.")

            paths.append(path)

        return paths

    async def get_user(self, username: str) -> GitHubUser:
        async with self._create_http_client() as client:
            response = await client.get(f"users/{username}")
            response.raise_for_status()

        return GitHubUser.model_validate(response.json())

    async def get_file_content(
        self,
        owner: str,
        repository: str,
        path: str,
        ref: str | None = None,
    ) -> GitHubFileContent | None:
        params = {"ref": ref} if ref is not None else None

        async with self._create_http_client() as client:
            response = await client.get(
                f"repos/{owner}/{repository}/contents/{path}",
                params=params,
            )

            if response.status_code == httpx.codes.NOT_FOUND:
                return None

            response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict) or payload.get("type") != "file":
            raise TypeError("GitHub content response must describe a file.")

        encoded_content = payload.get("content")
        encoding = payload.get("encoding")

        size = payload.get("size")

        if not isinstance(size, int) or isinstance(size, bool):
            raise TypeError("GitHub file response must include an integer size")

        if size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Github file exceeds the maximum size of {MAX_FILE_SIZE_BYTES} bytes."
            )

        if not isinstance(encoded_content, str) or not isinstance(encoding, str):
            raise TypeError("GitHub file response must include string content and encoding.")

        return GitHubFileContent.model_validate(
            {
                "path": payload.get("path"),
                "name": payload.get("name"),
                "content": decode_github_file_content(
                    content=encoded_content,
                    encoding=encoding,
                ),
                "size": size,
                "sha": payload.get("sha"),
            }
        )

    async def get_important_files(
        self,
        owner: str,
        repository: str,
        ref: str | None = None,
    ) -> dict[str, GitHubFileContent | None]:
        files: dict[str, GitHubFileContent | None] = {}

        for path in IMPORTANT_REPOSITORY_FILE_PATHS:
            files[path] = await self.get_file_content(
                owner=owner,
                repository=repository,
                path=path,
                ref=ref,
            )

        return files

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
