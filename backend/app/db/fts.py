from sqlalchemy import Column, Integer, Table, Text

from app.db.base import Base
from app.db.types import UTCDateTime

messages_fts = Table(
    "messages_fts",
    Base.metadata,
    Column("message_id", Integer),
    Column("user_id", Integer),
    Column("timestamp", UTCDateTime()),
    Column("text", Text),
)
