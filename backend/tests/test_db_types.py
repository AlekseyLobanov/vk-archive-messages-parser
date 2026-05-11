from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy import select, text

from app.models import Message


def test_utc_datetime_normalizes_aware_values_to_utc(session_factory) -> None:
    source_timestamp = datetime(
        2024, 1, 1, 15, 0, 0, tzinfo=timezone(timedelta(hours=3))
    )

    with session_factory() as session:
        session.add(
            Message(
                user_id=1,
                timestamp=source_timestamp,
                direction="inbound",
                text="hello",
                has_attachments=False,
            )
        )
        session.commit()

        stored = session.scalar(select(Message.timestamp))
        raw = session.execute(text("SELECT timestamp FROM messages")).scalar_one()

    assert stored == datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert isinstance(raw, str)
    assert raw == "2024-01-01 12:00:00.000000"


def test_utc_datetime_marks_naive_sqlite_values_as_utc(session_factory) -> None:
    with session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO conversations (
                    user_id, display_name, message_count, created_at, updated_at
                ) VALUES (
                    2, 'Test User', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            )
        )
        session.execute(
            text(
                """
                INSERT INTO messages (
                    user_id, timestamp, direction, text, has_attachments
                ) VALUES (
                    2, '2024-01-01 12:00:00.000000', 'outbound', 'hello', 0
                )
                """
            )
        )
        session.commit()

        stored = session.scalar(select(Message.timestamp).where(Message.user_id == 2))

    assert stored == datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
