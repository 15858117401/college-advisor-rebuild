"""Local environment configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigurationError(RuntimeError):
    """Raised when required local configuration is unavailable."""


@dataclass(frozen=True, slots=True)
class DeepSeekSettings:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"

    @classmethod
    def from_env(cls) -> "DeepSeekSettings":
        load_dotenv()

        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key or api_key == "your_deepseek_api_key_here":
            raise ConfigurationError(
                "DEEPSEEK_API_KEY is missing. Add it to the local .env file."
            )

        return cls(
            api_key=api_key,
            base_url=os.getenv(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
            ).rstrip("/"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip(),
        )
