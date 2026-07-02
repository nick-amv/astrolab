"""Runtime configuration, loaded from environment / /etc/astrolab/env.

No secrets are ever committed — the deployed unit points EnvironmentFile at
/etc/astrolab/env on nikam. Locally, a .env is read if present.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ASTROLAB_",
        extra="ignore",
    )

    # --- Core -----------------------------------------------------------
    environment: str = "dev"
    database_url: str = "postgresql+psycopg://astrolab:astrolab@localhost:5432/astrolab"
    cors_origins: str = "*"  # comma-separated; tightened in prod env file

    # --- Privacy / retention (PRIVACY_MODEL.md) -------------------------
    retention_days: int = 90  # anonymous sessions purged after this
    report_ttl_days: int = 180  # /r/<token> share links expire after this

    # --- LLM (see app/llm; real calls land in Wave 3) -------------------
    # Backend selection is data, not hardcoded imports. Default backend is
    # the Max-subscription CLI ($0); openrouter is the paid fallback.
    llm_backend: str = "max_cli"  # max_cli | openrouter | disabled
    llm_timeout_s: float = 30.0
    llm_rate_limit_per_min: int = 30  # per-provider ceiling, enforced in queue
    llm_max_concurrency: int = 4

    # max_cli backend
    claude_cli_bin: str = ""  # resolved via PATH when empty
    claude_code_oauth_token: str = ""

    # openrouter backend
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_model: str = "openai/gpt-4o-mini"

    # --- Admin ----------------------------------------------------------
    admin_tg_ids: str = ""  # comma-separated tg ids for /admin gate (Wave 5+)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
