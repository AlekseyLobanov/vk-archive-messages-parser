from datetime import datetime

from sqlalchemy import Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime


class Conversation(Base):
    __tablename__ = "conversations"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255))
    first_message_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
