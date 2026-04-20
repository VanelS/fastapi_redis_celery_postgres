"""
Configuration de l'application.
Charge les variables depuis .env et les expose via un objet typé.
"""
from functools import lru_cache
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application, chargés depuis .env."""

    # --- Application ---
    app_name: str = "FastAPI Celery Reports"
    debug: bool = False

    # --- PostgreSQL ---
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432

    # --- Redis ---
    redis_host: str = "redis"
    redis_port: int = 6379

    # --- Rapports ---
    reports_dir: str = "/app/reports"

    # --- URLs calculées à partir des variables ci-dessus ---
    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # --- Config Pydantic : d'où charger et comment ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # POSTGRES_USER == postgres_user
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Retourne un singleton des settings (créé une seule fois)."""
    return Settings()


# Instance globale pour les imports simples
settings = get_settings()