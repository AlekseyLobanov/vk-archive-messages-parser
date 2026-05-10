from alembic import command
from alembic.config import Config

from app.core.settings import ROOT_DIR, Settings


def init_db(settings: Settings) -> None:
    sqlite_file = settings.database.sqlite_file_path()
    if sqlite_file is not None and sqlite_file.exists():
        return

    if sqlite_file is not None:
        sqlite_file.parent.mkdir(parents=True, exist_ok=True)

    run_migrations(settings)


def run_migrations(settings: Settings) -> None:
    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "deploy/migrations"))
    config.set_main_option("sqlalchemy.url", settings.database.resolved_url())
    command.upgrade(config, "head")
