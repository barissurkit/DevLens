from app.db.models import User
from app.schemas.github import GitHubUser


def is_owner(*, authenticated_user: User | None, target_github_user: GitHubUser) -> bool:
    """Derive ownership only from trusted immutable provider IDs."""

    return (
        authenticated_user is not None
        and authenticated_user.github_user_id == target_github_user.github_user_id
    )
