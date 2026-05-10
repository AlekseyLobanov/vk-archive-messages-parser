from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.logging import configure_logging
from app.core.settings import ROOT_DIR, Settings, get_settings
from app.db.init_db import init_db
from app.db.session import create_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    web_out_dir = ROOT_DIR / "web-out"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(
            app_settings.logging.level,
            str(app_settings.logging.resolved_path()),
            app_settings.logging.max_bytes,
            app_settings.logging.backup_count,
        )
        init_db(app_settings)
        engine = create_engine(app_settings.database.resolved_url())
        session_factory = create_session_factory(engine)

        app.state.settings = app_settings
        app.state.engine = engine
        app.state.session_factory = session_factory
        yield
        engine.dispose()

    app = FastAPI(title="VK Archive Messages Parser", lifespan=lifespan)
    app.include_router(router, prefix="/api/v1")
    if web_out_dir.exists():
        app.mount(
            "/assets", StaticFiles(directory=web_out_dir / "assets"), name="assets"
        )

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(web_out_dir / "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str) -> FileResponse:
            target = (web_out_dir / full_path).resolve()
            try:
                target.relative_to(web_out_dir.resolve())
            except ValueError as exc:
                raise HTTPException(status_code=404) from exc

            if target.is_file():
                return FileResponse(target)
            return FileResponse(web_out_dir / "index.html")

    return app


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
