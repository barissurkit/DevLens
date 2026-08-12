from app.config import Settings, get_settings


def test_default_github_api_base_url() -> None:
    settings = Settings(_env_file=None)

    assert settings.github_api_base_url == "https://api.github.com"


def test_enviroment_variable_overrides_default(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_API_BASE_URL", "https://example.test")
    # monkeypatch.setenv() : pytest'in yerleşik fixture'ıdır. test süresince environment variable ekler ve test bitince değişikliği geri alır.

    settings = Settings(_env_file=None)
    # _env_file=None ile test sırasında proje root'undaki .env dosyasını devre dışı bırakır.

    assert settings.github_api_base_url == "https://example.test"


def test_get_settings_returns_cached_instance() -> None:

    first = get_settings()
    second = get_settings()

    assert first is second
