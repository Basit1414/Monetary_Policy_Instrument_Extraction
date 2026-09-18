"""Runtime configuration loaded without writing secrets to disk."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr

DEFAULT_MODEL = "gpt-5.6-terra"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RuntimeConfig(BaseModel):
    """Small, immutable runtime configuration object.

    Values are read from the process environment. This module intentionally does
    not load or write ``.env`` files, which keeps API-key persistence an explicit
    choice made outside the application.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(default=DEFAULT_MODEL, min_length=1)
    api_key: SecretStr | None = None
    prompt_dir: Path = PROJECT_ROOT / "prompts"

    @classmethod
    def from_env(cls) -> RuntimeConfig:
        """Build configuration from supported environment variables."""

        raw_key = os.getenv("OPENAI_API_KEY", "").strip()
        raw_model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        raw_prompt_dir = os.getenv("MPIE_PROMPT_DIR", "").strip()
        prompt_dir = (
            Path(raw_prompt_dir).expanduser() if raw_prompt_dir else PROJECT_ROOT / "prompts"
        )
        return cls(
            model=raw_model,
            api_key=SecretStr(raw_key) if raw_key else None,
            prompt_dir=prompt_dir,
        )

    def resolved_api_key(self, ephemeral_key: str = "") -> str | None:
        """Prefer a UI-supplied key without retaining it on this object."""

        supplied = ephemeral_key.strip()
        if supplied:
            return supplied
        return self.api_key.get_secret_value() if self.api_key else None
