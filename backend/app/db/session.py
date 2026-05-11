from pathlib import Path

from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

from app.core.settings import config_dir


def resolve_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return database_url
    database = url.database
    if database is None or database == ":memory:":
        return database_url
    path = Path(database)
    if not path.is_absolute():
        path = (config_dir() / path).resolve()
    return f"sqlite:///{path}"


def sqlite_database_file(database_url: str) -> Path | None:
    url = make_url(resolve_database_url(database_url))
    if url.get_backend_name() != "sqlite":
        return None
    database = url.database
    if database is None or database == ":memory:":
        return None
    return Path(database)


def create_engine(database_url: str) -> Engine:
    resolved_database_url = resolve_database_url(database_url)
    connect_args = {}
    if resolved_database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = sqlalchemy_create_engine(
        resolved_database_url, future=True, connect_args=connect_args
    )
    if resolved_database_url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)
    return engine


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
