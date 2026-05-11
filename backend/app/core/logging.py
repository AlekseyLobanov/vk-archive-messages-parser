import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog
from structlog.stdlib import ProcessorFormatter


def _json_dumps(event: dict, **kwargs) -> str:
    kwargs.setdefault("ensure_ascii", False)
    return json.dumps(event, **kwargs)


def _shared_formatter() -> ProcessorFormatter:
    return ProcessorFormatter(
        processors=[
            ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(serializer=_json_dumps),
        ],
        foreign_pre_chain=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_log_level,
        ],
    )


def configure_logging(level: str, path: str, max_bytes: int, backup_count: int) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    shared_processor = _shared_formatter()
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        ),
    ]
    for handler in handlers:
        handler.setFormatter(shared_processor)

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=handlers,
        force=True,
    )
    level_value = getattr(logging, level.upper(), logging.INFO)
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers = handlers
        logger.setLevel(level_value)
        logger.propagate = False

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_log_level,
            structlog.processors.format_exc_info,
            ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
