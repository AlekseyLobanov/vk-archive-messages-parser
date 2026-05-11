from alembic import command
from alembic.config import Config

from app.core.settings import Settings, base_dir
from app.db.session import resolve_database_url, sqlite_database_file


def init_db(settings: Settings) -> None:
    sqlite_file = sqlite_database_file(settings.database.url)
    if sqlite_file is not None and sqlite_file.exists():
        return

    if sqlite_file is not None:
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)

    run_migrations(settings)


def run_migrations(settings: Settings) -> None:
    current_base_dir = base_dir()
    config = Config(str(current_base_dir / "alembic.ini"))
    config.set_main_option(
        "script_location", str(current_base_dir / "deploy/migrations")
    )
    config.set_main_option(
        "sqlalchemy.url", resolve_database_url(settings.database.url)
    )
    command.upgrade(config, "head")
