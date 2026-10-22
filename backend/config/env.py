from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

INSECURE_DEV_SECRET = "dev-only-insecure-secret-key-change-me"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class AppSettings(BaseSettings):
    """Every environment variable the backend reads. Nothing else touches os.environ."""

    model_config = SettingsConfigDict(
        env_file=REPO_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    secret_key: SecretStr = SecretStr(INSECURE_DEV_SECRET)
    debug: bool = False
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_allowed_origins: str = "http://localhost:5173"
    csrf_trusted_origins: str = ""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    cache_url: str = ""

    osrm_base_url: str = "https://router.project-osrm.org"
    open_meteo_base_url: str = "https://api.open-meteo.com"
    photon_base_url: str = "https://photon.komoot.io"
    http_timeout_seconds: float = Field(default=12.0, gt=0, le=60)
    http_user_agent: str = "RouteIQ/1.0 (weather-aware truck routing)"

    truck_max_speed_mph: float = Field(default=65.0, ge=30, le=85)
    weather_cache_ttl_seconds: int = Field(default=1800, ge=0)
    geocode_cache_ttl_seconds: int = Field(default=86400, ge=0)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def allowed_hosts_list(self) -> list[str]:
        return _split_csv(self.allowed_hosts)

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return _split_csv(self.cors_allowed_origins)

    @property
    def csrf_trusted_origins_list(self) -> list[str]:
        return _split_csv(self.csrf_trusted_origins)

    @model_validator(mode="after")
    def _guard_production(self) -> "AppSettings":
        if not self.is_production:
            return self
        problems = []
        if self.secret_key.get_secret_value() in ("", INSECURE_DEV_SECRET):
            problems.append("SECRET_KEY must be set to a unique value")
        if self.debug:
            problems.append("DEBUG must be false")
        if not self.allowed_hosts_list or "*" in self.allowed_hosts_list:
            problems.append("ALLOWED_HOSTS must list explicit hosts")
        if problems:
            raise ValueError("Unsafe production config: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
