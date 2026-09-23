from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOCUMENT_INTELLIGENCE_", extra="ignore")
    environment: str = "development"
    data_dir: Path = Path(__file__).resolve().parents[3] / "data"
    max_document_bytes: int = 50 * 1024 * 1024
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "document_intelligence.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()
