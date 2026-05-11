import argparse
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.logging import configure_logging
from app.core.settings import Settings, app_dir, get_settings
from app.db.init_db import init_db
from app.db.session import create_engine, create_session_factory


def _build_lifespan(app_settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(
            app_settings.logging.level,
            str(app_settings.logging.resolved_path()),
            app_settings.logging.max_bytes,
            app_settings.logging.backup_count,
        )
        init_db(app_settings)
        engine = create_engine(app_settings.database.url)
        session_factory = create_session_factory(engine)

        app.state.settings = app_settings
        app.state.engine = engine
        app.state.session_factory = session_factory
        yield
        engine.dispose()

    return lifespan


def create_app(
    settings: Settings | None = None, *, use_lifespan: bool = True
) -> FastAPI:
    app_settings = settings or get_settings()
    web_out_dir = app_dir() / "web-out"
    if not web_out_dir.exists():
        raise RuntimeError(f"Built frontend not found: {web_out_dir}")

    app = FastAPI(
        title="VK Archive Messages Parser",
        lifespan=_build_lifespan(app_settings) if use_lifespan else None,
    )
    app.include_router(router, prefix="/api/v1")
    app.mount("/assets", StaticFiles(directory=web_out_dir / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def index() -> Response:
        return Response(
            content=(web_out_dir / "index.html").read_text(encoding="utf-8"),
            media_type="text/html",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> Response:
        target = (web_out_dir / full_path).resolve()
        try:
            target.relative_to(web_out_dir.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404) from exc

        if target.is_file():
            return FileResponse(target)
        return Response(
            content=(web_out_dir / "index.html").read_text(encoding="utf-8"),
            media_type="text/html",
        )

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VK archive backend server.")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to TOML config. Overrides VK_ARCHIVE_CONFIG for this process.",
    )
    return parser.parse_args()


def load_settings(config_path: Path | None) -> Settings:
    if config_path is not None:
        os.environ["VK_ARCHIVE_CONFIG"] = str(config_path.expanduser().resolve())
    get_settings.cache_clear()
    return get_settings()


def main() -> None:
    args = parse_args()
    settings = load_settings(args.config)
    app_instance = create_app(settings)
    uvicorn.run(
        app_instance,
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
