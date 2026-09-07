"""Twelve-factor configuration.

Every value the application needs comes from the environment. There are no
defaults that point at a provider, and no secret has a default at all — a
missing secret is a startup failure, not a silent fallback to something weak.

The adapter files in `adapters/` are the only place a provider is ever named.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- identity of this deployment -----------------------------------------
    app_name: str = "itc531-app"
    environment: str = Field(default="local", description="local | cloud")
    port: int = 8000

    # --- storage (S3 API) -----------------------------------------------------
    s3_endpoint_url: str
    s3_bucket: str
    s3_region: str = "us-east-1"

    # --- relational ------------------------------------------------------------
    database_url: str

    # Who owns the schema.
    #
    # True  (default) — the app creates its tables at startup. Right for a
    #                   scratch stack you tear down every session.
    # False           — something else owns the schema, and the app must not
    #                   touch it. Right the moment you have migrations, because
    #                   two things creating tables is how a schema silently
    #                   diverges from the migration history that is supposed to
    #                   describe it.
    #
    # Module 2 turns this off in compose.module2.yml. It is a flag rather than a
    # code edit on purpose: the app source is shared by every module, so an edit
    # here would follow you into Modules 3-7 and break them.
    auto_create_tables: bool = True

    # --- messaging -------------------------------------------------------------
    amqp_url: str = "amqp://guest:guest@broker:5672/"

    # --- security --------------------------------------------------------------
    # No default. If this is unset the app refuses to start, which is the
    # correct behavior and is what a hardcoded fallback prevents you from
    # learning.
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30

    # --- CORS ------------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
