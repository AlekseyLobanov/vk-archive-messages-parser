from sqlalchemy import select

from app.core.settings import app_dir
from app.models import Conversation, Message
from app.services.importer import ImportService


def test_importer_imports_archive_and_is_idempotent(session_factory) -> None:
    service = ImportService(session_factory)

    events = list(service.import_archive(app_dir() / "messages"))
    done_event = events[-1][1]
    progress_events = [
        payload for event_name, payload in events if event_name == "progress"
    ]

    assert events[0][0] == "progress"
    assert events[-1][0] == "done"
    assert done_event.total == 4
    assert done_event.errors == 0
    assert done_event.imported > 0
    assert progress_events[-1].imported == done_event.imported
    assert progress_events[-1].skipped == done_event.skipped

    events_second = list(service.import_archive(app_dir() / "messages"))
    done_event_second = events_second[-1][1]
    assert done_event_second.imported == 0
    assert done_event_second.skipped > 0

    with session_factory() as session:
        conversations = session.scalars(
            select(Conversation).order_by(Conversation.user_id)
        ).all()
        messages = session.scalars(select(Message)).all()

    assert len(conversations) == 3
    assert conversations[0].user_id == -17801455
    assert conversations[1].user_id == 4043901
    assert conversations[2].user_id == 2000000063
    assert len(messages) == done_event.imported
    assert sum(conversation.message_count for conversation in conversations) == len(
        messages
    )
