from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.settings import (
    DatabaseSettings,
    LoggingSettings,
    ServerSettings,
    Settings,
)
from app.db.init_db import run_migrations
from app.db.session import create_engine, create_session_factory
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        database=DatabaseSettings(url=f"sqlite:///{tmp_path / 'test.db'}"),
        logging=LoggingSettings(
            level="INFO",
            path=str(tmp_path / "logs" / "backend.log"),
            max_bytes=1024,
            backup_count=2,
        ),
        server=ServerSettings(host="127.0.0.1", port=8001),
    )


@pytest.fixture
def app(test_settings: Settings):
    return create_app(test_settings)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session_factory(test_settings: Settings):
    run_migrations(test_settings)
    engine = create_engine(test_settings.database.resolved_url())
    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()


@pytest.fixture
def imported_archive(session_factory) -> None:
    from app.services.importer import ImportService

    service = ImportService(session_factory)
    list(service.import_archive(Path("messages")))


@pytest.fixture
def clean_fts(session_factory) -> None:
    with session_factory() as session:
        session.execute(text("DELETE FROM messages_fts"))
        session.commit()
