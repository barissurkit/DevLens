from app.db.models import User
from app.schemas.analysis import ViewerContext
from app.schemas.github import GitHubUser


def is_owner(*, authenticated_user: User | None, target_github_user: GitHubUser) -> bool:
    """Derive ownership only from trusted immutable provider IDs."""

    return (
        authenticated_user is not None
        and authenticated_user.github_user_id == target_github_user.github_user_id
    )


def derive_viewer_context(*, authenticated_user: User | None, target_github_user: GitHubUser) -> ViewerContext:
    owner = is_owner(authenticated_user=authenticated_user, target_github_user=target_github_user)
    return ViewerContext(is_owner=owner, mode="my_workspace" if owner else "explore")
