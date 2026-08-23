import pytest

from app.config import Settings
from app.db.constants import ANALYSIS_SNAPSHOT_SCHEMA_VERSION, INTERPRETATION_SNAPSHOT_SCHEMA_VERSION
from app.db.database import DatabaseNotConfiguredError, get_engine
from app.db.normalization import normalize_github_username


def test_database_url_is_optional() -> None:
    assert Settings(_env_file=None).database_url is None


def test_database_engine_fails_only_when_explicitly_used_without_url() -> None:
    with pytest.raises(DatabaseNotConfiguredError):
        get_engine()


@pytest.mark.parametrize(
    ("value", "expected"),
    [(" OctoCat ", "octocat"), ("OCTOCAT", "octocat")],
)
def test_github_username_normalization(value: str, expected: str) -> None:
    assert normalize_github_username(value) == expected


def test_snapshot_schema_versions_are_explicit() -> None:
    assert ANALYSIS_SNAPSHOT_SCHEMA_VERSION == "v1"
    assert INTERPRETATION_SNAPSHOT_SCHEMA_VERSION == "v1"
