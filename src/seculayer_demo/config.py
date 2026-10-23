"""Demo settings, read from the environment and the repository's .env file.

The OpenAI key is a SecretStr: it is never printed, logged, recorded or sent to the browser.
"""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

Mode = Literal["replay", "live"]


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: SecretStr = Field(default=SecretStr(""), alias="OPENAI_API_KEY")
    mode: Mode = Field(default="replay", alias="SECULAYER_MODE")
    model: str = Field(default="gpt-5.4-mini-2026-03-17", alias="SECULAYER_MODEL")
    compare_model: str = Field(default="gpt-5.4-2026-03-05", alias="SECULAYER_COMPARE_MODEL")
    judge_model: str = Field(default="gpt-5.4-mini-2026-03-17", alias="SECULAYER_JUDGE_MODEL")
    host: str = Field(default="127.0.0.1", alias="SECULAYER_HOST")
    port: int = Field(default=8765, alias="SECULAYER_PORT", ge=1, le=65535)
    token_budget: int = Field(default=1_500_000, alias="SECULAYER_TOKEN_BUDGET", ge=0)
    classifier_dir: Path = Field(
        default=Path("models/prompt-guard-2-22m"), alias="SECULAYER_CLASSIFIER_DIR"
    )
    log_level: Literal["debug", "info", "warning", "error"] = Field(
        default="info", alias="SECULAYER_LOG_LEVEL"
    )

    @field_validator("host")
    @classmethod
    def _host_is_loopback(cls, value: str) -> str:
        if not is_loopback(value):
            raise ValueError(f"SECULAYER_HOST must be a loopback address, not {value!r}")
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def _lowercase_level(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value

    @property
    def has_api_key(self) -> bool:
        return bool(self.openai_api_key.get_secret_value().strip())

    @property
    def classifier_path(self) -> Path:
        path = self.classifier_dir
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def data_dir(self) -> Path:
        return REPO_ROOT / "data"

    @property
    def recordings_dir(self) -> Path:
        return self.data_dir / "recordings"

    @property
    def spend_log(self) -> Path:
        return self.data_dir / "spend.jsonl"

    @property
    def web_dist(self) -> Path:
        return REPO_ROOT / "web" / "dist"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
