from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("user_id", "timestamp", name="uq_messages_user_timestamp"),
        Index("ix_messages_user_timestamp_desc", "user_id", "timestamp"),
        Index("ix_messages_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.user_id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    has_attachments: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), nullable=False
    )

    conversation = relationship("Conversation", back_populates="messages")
