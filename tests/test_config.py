from __future__ import annotations

import pytest

from app.config import ConfigurationError, DeepSeekSettings


def test_api_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="DEEPSEEK_API_KEY"):
        DeepSeekSettings.from_env()


def test_settings_use_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "test-model")

    settings = DeepSeekSettings.from_env()

    assert settings.api_key == "test-key"
    assert settings.model == "test-model"
