from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


def normalize_datetime_to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class SearchMode(StrEnum):
    SIMPLE = "simple"
    FTS = "fts"


class ExportFormat(StrEnum):
    TXT = "txt"
    JSON = "json"
    JSONL = "jsonl"


class AddRequest(BaseModel):
    path: str


class ImportProgress(BaseModel):
    total: int
    remains: int
    errors: int
    imported: int = 0
    skipped: int = 0


class ImportDone(ImportProgress):
    pass


class ConversationItem(BaseModel):
    user_id: int
    display_name: str
    message_count: int
    last_message_at: datetime | None
    first_message_at: datetime | None

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    items: list[ConversationItem]
    total: int


class MessageItem(BaseModel):
    user_id: int
    timestamp: datetime
    direction: str
    text: str
    has_attachments: bool


class PagingInfo(BaseModel):
    limit: int
    has_older: bool
    has_newer: bool
    next_before: datetime | None
    next_after: datetime | None


class MessageContext(BaseModel):
    mode: str
    anchor_timestamp: datetime | None
    highlighted_timestamp: datetime | None


class MessageListResponse(BaseModel):
    items: list[MessageItem]
    paging: PagingInfo
    context: MessageContext


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    user_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=50, gt=0)
    offset: int = Field(default=0, ge=0)
    mode: SearchMode = SearchMode.SIMPLE

    _normalize_datetimes = field_validator("date_from", "date_to")(
        normalize_datetime_to_utc
    )


class SearchItem(BaseModel):
    user_id: int
    display_name: str
    timestamp: datetime
    direction: str
    text: str


class SearchResponse(BaseModel):
    items: list[SearchItem]
    total: int


class ExportRequest(BaseModel):
    format: ExportFormat
    user_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=1000, gt=0)

    _normalize_datetimes = field_validator("date_from", "date_to")(
        normalize_datetime_to_utc
    )


class ExportMessageItem(BaseModel):
    user_id: int
    display_name: str
    timestamp: datetime
    direction: str
    text: str
    has_attachments: bool
