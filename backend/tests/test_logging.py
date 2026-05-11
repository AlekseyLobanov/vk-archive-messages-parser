import logging
import os
from logging.config import fileConfig
from pathlib import Path

import structlog

from app.core.logging import configure_logging
from app.core.settings import LoggingSettings, base_dir


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


def test_logging_settings_resolve_relative_path_from_base_dir() -> None:
    settings = LoggingSettings(path="logs/backend.log")

    resolved = settings.resolved_path()

    assert resolved == base_dir() / "logs" / "backend.log"
    assert not os.path.isabs(settings.path)


def test_alembic_logger_does_not_propagate_to_root() -> None:
    fileConfig(base_dir() / "alembic.ini", disable_existing_loggers=False)

    logger = logging.getLogger("alembic")

    assert not logger.propagate
