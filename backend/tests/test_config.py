from app.core.config import Settings


def test_defaults():
    settings = Settings(_env_file=None)
    assert settings.anthropic_model == "claude-opus-5-5"
    assert settings.check_interval_sec == 60


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("CHECK_INTERVAL_SEC", "30")
    monkeypatch.setenv("CORS_ORIGINS", '["https://pult.example"]')
    settings = Settings(_env_file=None)
    assert settings.check_interval_sec == 30
    assert settings.cors_origins == ["https://pult.example"]
