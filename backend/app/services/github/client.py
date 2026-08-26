import base64
import binascii
import logging
import time
from typing import Any

import httpx

from app.config import Settings
from app.observability import emit_event
from app.schemas.github import (
    GitHubFileContent,
    GitHubRepository,
    GitHubRepositoryTree,
    GitHubUser,
)

logger = logging.getLogger(__name__)

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

    async def _request(
        self,
        client: httpx.AsyncClient,
        *,
        operation: str,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        started_at = time.monotonic()
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.TimeoutException:
            emit_event(
                logger,
                "github.request.completed",
                level=logging.WARNING,
                provider="github",
                operation=operation,
                duration_ms=max(0, round((time.monotonic() - started_at) * 1000)),
                error_category="timeout",
            )
            raise
        except httpx.RequestError:
            emit_event(
                logger,
                "github.request.completed",
                level=logging.WARNING,
                provider="github",
                operation=operation,
                duration_ms=max(0, round((time.monotonic() - started_at) * 1000)),
                error_category="transport_error",
            )
            raise

        headers = response.headers
        rate_fields: dict[str, int | str] = {}
        for header, field in (
            ("x-ratelimit-limit", "rate_limit_limit"),
            ("x-ratelimit-remaining", "rate_limit_remaining"),
            ("x-ratelimit-reset", "rate_limit_reset"),
            ("x-ratelimit-used", "rate_limit_used"),
        ):
            value = headers.get(header)
            if value is not None:
                try:
                    rate_fields[field] = int(value)
                except ValueError:
                    continue
        resource = headers.get("x-ratelimit-resource")
        if resource is not None and len(resource) <= 64:
            rate_fields["rate_limit_resource"] = resource
        retry_after = headers.get("retry-after")
        if retry_after is not None:
            try:
                retry_after_seconds = int(retry_after)
            except ValueError:
                retry_after_seconds = -1
            if retry_after_seconds >= 0:
                rate_fields["retry_after_seconds"] = retry_after_seconds

        error_category = None
        if response.status_code == httpx.codes.NOT_FOUND:
            error_category = "not_found"
        elif response.status_code in {httpx.codes.FORBIDDEN, httpx.codes.TOO_MANY_REQUESTS}:
            error_category = "rate_limit"
        elif response.status_code >= 400:
            error_category = "upstream_error"
        emit_event(
            logger,
            "github.request.completed",
            level=logging.WARNING if error_category else logging.INFO,
            provider="github",
            operation=operation,
            duration_ms=max(0, round((time.monotonic() - started_at) * 1000)),
            upstream_status=response.status_code,
            error_category=error_category,
            **rate_fields,
        )
        return response

    async def get_repository_tree(
        self,
        owner: str,
        repository: str,
        ref: str,
    ) -> GitHubRepositoryTree:
        async with self._create_http_client() as client:
            response = await self._request(
                client,
                operation="tree",
                method="GET",
                url=f"repos/{owner}/{repository}/git/trees/{ref}",
                params={"recursive": "1"},
            )
        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise TypeError("GitHub tree response must be a JSON object.")

        truncated = payload.get("truncated")

        if not isinstance(truncated, bool):
            raise TypeError("GitHub tree response must include a boolean truncated field.")

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

        return GitHubRepositoryTree(
            paths=paths,
            truncated=truncated,
        )

    async def get_user(self, username: str) -> GitHubUser:
        async with self._create_http_client() as client:
            response = await self._request(
                client, operation="user", method="GET", url=f"users/{username}"
            )
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
            response = await self._request(
                client,
                operation="file",
                method="GET",
                url=f"repos/{owner}/{repository}/contents/{path}",
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
                response = await self._request(
                    client,
                    operation="repos",
                    method="GET",
                    url=f"users/{username}/repos",
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
