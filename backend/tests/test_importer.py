from sqlalchemy import select

from app.models import Conversation, Message
from app.services.importer import ImportService


def test_importer_imports_archive_and_is_idempotent(
    session_factory, archive_root
) -> None:
    service = ImportService(session_factory)

    events = list(service.import_archive(archive_root))
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

    events_second = list(service.import_archive(archive_root))
    done_event_second = events_second[-1][1]
    assert done_event_second.imported == 0
    assert done_event_second.skipped > 0

    with session_factory() as session:
        conversations = session.scalars(
            select(Conversation).order_by(Conversation.user_id)
        ).all()
        messages = session.scalars(select(Message)).all()

    assert len(conversations) == 3
    assert conversations[0].user_id == -101
    assert conversations[1].user_id == 202
    assert conversations[2].user_id == 303
    assert done_event.imported == 15
    assert len(messages) == done_event.imported
    assert sum(conversation.message_count for conversation in conversations) == len(
        messages
    )


def test_importer_raises_for_missing_archive(session_factory, tmp_path) -> None:
    service = ImportService(session_factory)

    missing_path = tmp_path / "missing"

    try:
        next(service.import_archive(missing_path))
    except FileNotFoundError as exc:
        assert str(exc) == f"Path does not exist: {missing_path}"
    else:
        raise AssertionError("Expected FileNotFoundError for missing archive path")


def test_importer_continues_after_single_file_failure(
    session_factory, monkeypatch, archive_root
) -> None:
    service = ImportService(session_factory)
    original_parse_file = service.parser.parse_file

    def parse_file_with_failure(path):
        if path.parent.name == "303" and path.name == "messages0.html":
            raise ValueError("broken sample file")
        return original_parse_file(path)

    monkeypatch.setattr(service.parser, "parse_file", parse_file_with_failure)

    events = list(service.import_archive(archive_root))
    done_event = events[-1][1]

    assert events[-1][0] == "done"
    assert done_event.total == 4
    assert done_event.errors == 1
    assert done_event.imported == 10
    assert done_event.skipped == 0

    with session_factory() as session:
        conversations = session.scalars(
            select(Conversation).order_by(Conversation.user_id)
        ).all()
        partial_conversation = session.get(Conversation, 303)
        messages = session.scalars(select(Message)).all()

    assert len(conversations) == 3
    assert partial_conversation is not None
    assert partial_conversation.display_name == "Alex Example"
    assert partial_conversation.message_count == 3
    assert len(messages) == 10
