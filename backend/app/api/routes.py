from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import ROOT_DIR
from app.repositories.storage import (
    ConversationRepository,
    MessageRepository,
    SearchRepository,
)
from app.schemas.api import (
    AddRequest,
    ConversationListResponse,
    ExportRequest,
    MessageListResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.exporter import export_messages
from app.services.importer import ImportService

router = APIRouter()


def get_session_factory(request: Request) -> sessionmaker:
    return request.app.state.session_factory


def get_session(request: Request) -> Iterator[Session]:
    session_factory = get_session_factory(request)
    with session_factory() as session:
        yield session


@router.post("/add")
def add_archive(request_data: AddRequest, request: Request) -> StreamingResponse:
    session_factory = get_session_factory(request)
    import_service = ImportService(session_factory)
    archive_path = Path(request_data.path)
    if not archive_path.is_absolute():
        archive_path = ROOT_DIR / archive_path

    if not archive_path.exists():
        raise HTTPException(status_code=400, detail="Import path does not exist")

    def event_stream() -> Iterator[str]:
        try:
            for event_name, payload in import_service.import_archive(archive_path):
                yield f"event: {event_name}\n"
                yield f"data: {payload.model_dump_json()}\n\n"
        except FileNotFoundError as exc:
            yield "event: error\n"
            yield f'data: {{"detail": "{str(exc)}"}}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    sort: str = "last_message_at",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),  # noqa: B008
) -> ConversationListResponse:
    repository = ConversationRepository(session)
    items, total = repository.list_conversations(
        sort=sort, order=order, limit=limit, offset=offset
    )
    return ConversationListResponse(items=items, total=total)


@router.get("/messages/{user_id}", response_model=MessageListResponse)
def list_messages(
    user_id: int,
    limit: int = 50,
    before: datetime | None = None,
    after: datetime | None = None,
    around: datetime | None = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> MessageListResponse:
    repository = MessageRepository(session)
    try:
        return repository.list_messages(
            user_id=user_id,
            limit=limit,
            before=before,
            after=after,
            around=around,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/search", response_model=SearchResponse)
def search_messages(
    request_data: SearchRequest,
    session: Session = Depends(get_session),  # noqa: B008
) -> SearchResponse:
    repository = SearchRepository(session)
    try:
        return repository.search_messages(request_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/export")
def export(
    request_data: ExportRequest,
    session: Session = Depends(get_session),  # noqa: B008
) -> Response:
    repository = MessageRepository(session)
    content, media_type, filename = export_messages(repository, request_data)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)
