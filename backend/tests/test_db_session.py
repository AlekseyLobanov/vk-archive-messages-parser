from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import Message


def test_sqlite_connections_enable_foreign_keys(session_factory) -> None:
    with session_factory() as session:
        foreign_keys = session.execute(text("PRAGMA foreign_keys")).scalar_one()

    assert foreign_keys == 1


def test_message_insert_rejects_missing_conversation(session_factory) -> None:
    with session_factory() as session:
        session.add(
            Message(
                user_id=999999,
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
                direction="inbound",
                text="orphan",
                has_attachments=False,
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()
