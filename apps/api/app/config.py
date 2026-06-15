from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./storage/verisynth.db"
    storage_path: str = "./storage"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    cors_origins: str = "http://localhost:3000"

    @property
    def storage_dir(self) -> Path:
        path = Path(self.storage_path)
        path.mkdir(parents=True, exist_ok=True)
        (path / "uploads").mkdir(parents=True, exist_ok=True)
        (path / "synthetic").mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
