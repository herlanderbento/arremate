import logging
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "arremate"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "arremate"
    SQL_ECHO: bool = False

    ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    COOKIE_SECURE: bool = True
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"
    ACCESS_TOKEN_COOKIE: str = "access_token"

    AUDIT_SECRET: str

    CATALOG_BASE_URL: str = "https://api.artic.edu/api/v1"
    CATALOG_TIMEOUT_SECONDS: float = 5.0
    CATALOG_CACHE_TTL_SECONDS: int = 300

    SETTLEMENT_WORKER_ENABLED: bool = True
    SETTLEMENT_INTERVAL_SECONDS: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _database_url_from_parts(self) -> "Settings":
        if self.POSTGRES_HOST:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{quote(self.POSTGRES_USER)}:{quote(self.POSTGRES_PASSWORD)}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.DATABASE_URL:
            raise ValueError("Set DATABASE_URL (or POSTGRES_HOST and the other POSTGRES_* vars)")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

MIN_SECRET_BYTES = 32  # RFC 7518 section 3.2 for HS256
for _name in ("JWT_SECRET_KEY", "AUDIT_SECRET"):
    if len(getattr(settings, _name).encode()) < MIN_SECRET_BYTES:
        logging.getLogger(__name__).warning(
            "%s is shorter than %d bytes; generate a longer random key "
            '(e.g. python -c "import secrets; print(secrets.token_urlsafe(48))").',
            _name,
            MIN_SECRET_BYTES,
        )
