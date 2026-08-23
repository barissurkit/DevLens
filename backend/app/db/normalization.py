GITHUB_USERNAME_MAX_LENGTH = 39


def normalize_github_username(username: str) -> str:
    """Return the stable case-insensitive key used by GitHub snapshot lookups."""
    normalized = username.strip().lower()
    if not normalized:
        raise ValueError("GitHub username must not be empty.")
    if len(normalized) > GITHUB_USERNAME_MAX_LENGTH:
        raise ValueError("GitHub username must be at most 39 characters.")
    return normalized
