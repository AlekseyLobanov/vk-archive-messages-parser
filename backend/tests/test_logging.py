import logging
import os
from logging.config import fileConfig
from pathlib import Path

import structlog

from app.core.logging import configure_logging
from app.core.settings import LoggingSettings, app_dir


def test_structlog_preserves_unicode_and_writes_file(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "backend.log"
    configure_logging("INFO", str(log_path), max_bytes=1024, backup_count=1)

    logger = structlog.get_logger("test")
    logger.info("unicode.test", display_name='Парфюмерная мастерская "Jujube Cat"')
    for handler in logging.getLogger().handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf-8")
    assert "Парфюмерная мастерская" in content
    assert "Jujube Cat" in content
    assert "\\u041f" not in content


def test_logging_settings_resolve_relative_path_from_config_dir(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("VK_ARCHIVE_CONFIG", str(config_path))
    settings = LoggingSettings(path="logs/backend.log")

    resolved = settings.resolved_path()

    assert resolved == tmp_path / "logs" / "backend.log"
    assert not os.path.isabs(settings.path)


def test_alembic_logger_does_not_propagate_to_root() -> None:
    fileConfig(app_dir() / "alembic.ini", disable_existing_loggers=False)

    logger = logging.getLogger("alembic")

    assert not logger.propagate


def test_uvicorn_loggers_write_once_with_formatted_exceptions(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "backend.log"
    configure_logging("INFO", str(log_path), max_bytes=1024, backup_count=1)

    logging.getLogger("uvicorn.access").info(
        '127.0.0.1:37588 - "GET /api/v1/conversations HTTP/1.1" 200 OK'
    )
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logging.getLogger("uvicorn.error").exception("request.failed")
    for handler in logging.getLogger().handlers:
        handler.flush()

    lines = log_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert "GET /api/v1/conversations" in lines[0]
    assert '"event": "request.failed"' in lines[1]
    assert "RuntimeError: boom" in lines[1]
