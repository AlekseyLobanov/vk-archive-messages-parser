from pathlib import Path

from app.core import settings as settings_module
from app.db.session import resolve_database_url
from app.main import load_settings as load_app_settings
from scripts.generate_demo_data import load_settings as load_demo_settings


def test_config_dir_uses_config_parent(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "custom.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("VK_ARCHIVE_CONFIG", str(config_path))

    assert settings_module.config_dir() == config_path.parent.resolve()


def test_config_path_returns_none_without_env(monkeypatch) -> None:
    monkeypatch.delenv("VK_ARCHIVE_CONFIG", raising=False)

    assert settings_module._config_path() is None


def test_config_path_uses_env_var(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("VK_ARCHIVE_CONFIG", str(config_path))

    assert settings_module._config_path() == config_path.resolve()


def test_config_path_resolves_relative_env_from_pwd(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("VK_ARCHIVE_CONFIG", "config.toml")
    monkeypatch.setenv("PWD", str(tmp_path))

    assert settings_module._config_path() == config_path.resolve()


def test_resolve_database_url_uses_config_dir(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "custom.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("VK_ARCHIVE_CONFIG", str(config_path))

    assert resolve_database_url("sqlite:///data/app.db") == (
        f"sqlite:///{(config_path.parent / 'data' / 'app.db').resolve()}"
    )


def test_app_dir_finds_repository_root() -> None:
    assert (settings_module.app_dir() / "alembic.ini").exists()
    assert (settings_module.app_dir() / "web-out").exists()


def test_app_load_settings_resolves_relative_config_path(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[database]\nurl = "sqlite:///data/app.db"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VK_ARCHIVE_CONFIG", raising=False)

    settings = load_app_settings(Path("config.toml"))

    assert settings.database.url == "sqlite:///data/app.db"
    assert settings_module._config_path() == config_path.resolve()


def test_demo_load_settings_resolves_relative_config_path(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[database]\nurl = "sqlite:///data/app.db"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VK_ARCHIVE_CONFIG", raising=False)

    settings = load_demo_settings(Path("config.toml"))

    assert settings.database.url == "sqlite:///data/app.db"
    assert settings_module._config_path() == config_path.resolve()
