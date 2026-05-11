from pathlib import Path

from app.core import settings as settings_module
from app.db.session import resolve_database_url


def test_base_dir_prefers_config_parent(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "custom.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("VK_ARCHIVE_CONFIG", str(config_path))

    assert settings_module.base_dir() == config_path.parent.resolve()


def test_config_path_returns_none_without_env(monkeypatch) -> None:
    monkeypatch.delenv("VK_ARCHIVE_CONFIG", raising=False)

    assert settings_module._config_path() is None


def test_config_path_uses_env_var(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("VK_ARCHIVE_CONFIG", str(config_path))

    assert settings_module._config_path() == config_path.resolve()


def test_resolve_database_url_uses_base_dir(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "custom.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("VK_ARCHIVE_CONFIG", str(config_path))

    assert resolve_database_url("sqlite:///data/app.db") == (
        f"sqlite:///{(config_path.parent / 'data' / 'app.db').resolve()}"
    )
