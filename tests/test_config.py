from __future__ import annotations

from mpie.config import DEFAULT_MODEL, RuntimeConfig


def test_runtime_config_masks_environment_key_and_prefers_ephemeral_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "environment-secret")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    config = RuntimeConfig.from_env()

    assert config.model == DEFAULT_MODEL
    assert config.resolved_api_key() == "environment-secret"
    assert config.resolved_api_key("ui-secret") == "ui-secret"
    assert "environment-secret" not in repr(config)
    assert "ui-secret" not in repr(config)
