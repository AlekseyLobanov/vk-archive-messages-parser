import json
from datetime import UTC, datetime

from app.repositories.storage import MessageRepository
from app.schemas.api import ExportFormat, ExportRequest
from app.services.exporter import export_messages


def test_export_messages_supports_all_formats(
    imported_archive, session_factory
) -> None:
    with session_factory() as session:
        repository = MessageRepository(session)
        request = ExportRequest(format=ExportFormat.JSON, user_id=303, limit=2)

        content, media_type, filename = export_messages(repository, request)

        payload = json.loads(content)
        assert media_type == "application/json"
        assert filename == "messages.json"
        assert len(payload) == 2
        assert [item["timestamp"] for item in payload] == [
            "2017-08-09T11:31:26Z",
            "2017-08-09T11:32:27Z",
        ]
        assert all(item["display_name"] == "Alex Example" for item in payload)

        content, media_type, filename = export_messages(
            repository,
            ExportRequest(format=ExportFormat.JSONL, user_id=303, limit=2),
        )

        lines = [json.loads(line) for line in content.splitlines()]
        assert media_type == "application/jsonl"
        assert filename == "messages.jsonl"
        assert len(lines) == 2
        assert [item["timestamp"] for item in lines] == [
            "2017-08-09T11:31:26Z",
            "2017-08-09T11:32:27Z",
        ]

        content, media_type, filename = export_messages(
            repository,
            ExportRequest(format=ExportFormat.TXT, user_id=-101, limit=1),
        )

        assert media_type == "text/plain; charset=utf-8"
        assert filename == "messages.txt"
        assert content.startswith("[2018-12-03T17:44:05+00:00] Store Bot (outbound): ")
        assert "Здравствуйте!" in content


def test_export_messages_applies_filters_and_keeps_chronological_order(
    imported_archive, session_factory
) -> None:
    with session_factory() as session:
        repository = MessageRepository(session)
        content, _, _ = export_messages(
            repository,
            ExportRequest(
                format=ExportFormat.JSON,
                user_id=202,
                date_from=datetime(2020, 9, 1, 0, 0, 0, tzinfo=UTC),
                date_to=datetime(2020, 9, 1, 23, 59, 59, tzinfo=UTC),
                limit=20,
            ),
        )

    payload = json.loads(content)

    assert payload
    assert all(item["user_id"] == 202 for item in payload)
    assert [item["timestamp"] for item in payload] == sorted(
        item["timestamp"] for item in payload
    )
    assert payload[0]["timestamp"] == "2020-09-01T16:28:26Z"
    assert payload[-1]["timestamp"] == "2020-09-01T23:31:45Z"
