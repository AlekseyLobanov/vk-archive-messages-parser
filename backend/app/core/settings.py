import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource
from sqlalchemy.engine import make_url

ROOT_DIR = Path(__file__).resolve().parents[3]


def _config_path() -> Path:
    configured_path = os.getenv("VK_ARCHIVE_CONFIG")
    if configured_path:
        path = Path(configured_path)
        if not path.is_absolute():
            path = (ROOT_DIR / path).resolve()
        return path
    return ROOT_DIR / "config.toml"


class DatabaseSettings(BaseModel):
    url: str = "sqlite:///data/vk_messages.db"

    def resolved_url(self) -> str:
        url = make_url(self.url)
        if url.get_backend_name() != "sqlite":
            return self.url
        database = url.database
        if database is None or database == ":memory:":
            return self.url
        path = Path(database)
        if not path.is_absolute():
            path = (ROOT_DIR / path).resolve()
        return f"sqlite:///{path}"

    def sqlite_file_path(self) -> Path | None:
        url = make_url(self.url)
        if url.get_backend_name() != "sqlite":
            return None
        database = url.database
        if database is None or database == ":memory:":
            return None
        path = Path(database)
        if not path.is_absolute():
            path = (ROOT_DIR / path).resolve()
        return path


class LoggingSettings(BaseModel):
    level: str = "INFO"
    path: str = "logs/backend.log"
    max_bytes: int = 1_048_576
    backup_count: int = 3

    def resolved_path(self) -> Path:
        path = Path(self.path)
        if not path.is_absolute():
            path = (ROOT_DIR / path).resolve()
        return path


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VK_ARCHIVE_",
        extra="ignore",
    )

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls, _config_path()),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
