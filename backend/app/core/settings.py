import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource


def _config_path() -> Path | None:
    configured_path = os.getenv("VK_ARCHIVE_CONFIG")
    if not configured_path:
        return None
    path = Path(configured_path).expanduser()
    if path.is_absolute():
        return path.resolve()

    working_dir = Path(os.getenv("PWD", Path.cwd())).expanduser().resolve()
    return (working_dir / path).resolve()


def config_dir() -> Path:
    config_path = _config_path()
    if config_path is None:
        raise RuntimeError("VK_ARCHIVE_CONFIG must point to a TOML config file")
    return config_path.parent


def app_dir() -> Path:
    current = Path(__file__).resolve()
    for directory in current.parents:
        if (directory / "alembic.ini").exists() and (directory / "web-out").exists():
            return directory
    raise RuntimeError(f"Could not locate app directory from {current}")


class DatabaseSettings(BaseModel):
    url: str


class LoggingSettings(BaseModel):
    level: str = "INFO"
    path: str = "logs/backend.log"
    max_bytes: int = 1_048_576
    backup_count: int = 3

    def resolved_path(self) -> Path:
        path = Path(self.path)
        if not path.is_absolute():
            path = (config_dir() / path).resolve()
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
        sources = [
            init_settings,
            env_settings,
        ]
        config_path = _config_path()
        if config_path is not None:
            sources.append(TomlConfigSettingsSource(settings_cls, config_path))
        sources.append(file_secret_settings)
        return tuple(sources)


@lru_cache
def get_settings() -> Settings:
    return Settings()
