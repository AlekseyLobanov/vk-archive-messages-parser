from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models import Conversation, Message
from app.parsers.vk_html.parser import ParsedConversationFile, ParsedMessage
from app.repositories.storage import (
    ConversationRepository,
    MessageRepository,
    SearchRepository,
)
from app.schemas.api import ExportRequest, SearchRequest


def test_list_messages_returns_latest_slice_with_paging(
    imported_archive, session_factory
):
    with session_factory() as session:
        messages = session.scalars(
            select(Message)
            .where(Message.user_id == 303)
            .order_by(Message.timestamp.asc())
        ).all()
        response = MessageRepository(session).list_messages(
            user_id=303,
            limit=3,
            before=None,
            after=None,
            around=None,
        )

    expected_timestamps = [message.timestamp for message in messages[-3:]]

    assert [item.timestamp for item in response.items] == expected_timestamps
    assert response.paging.limit == 3
    assert response.paging.has_older is True
    assert response.paging.has_newer is False
    assert response.paging.next_before == expected_timestamps[0]
    assert response.paging.next_after == expected_timestamps[-1]
    assert response.context.mode == "slice"
    assert response.context.anchor_timestamp is None


def test_list_messages_around_anchor_returns_context_window(
    imported_archive, session_factory
) -> None:
    with session_factory() as session:
        messages = session.scalars(
            select(Message)
            .where(Message.user_id == 303)
            .order_by(Message.timestamp.asc())
        ).all()
        anchor = messages[4].timestamp
        response = MessageRepository(session).list_messages(
            user_id=303,
            limit=2,
            before=None,
            after=None,
            around=anchor,
        )

    assert len(response.items) == 5
    assert [item.timestamp for item in response.items] == [
        message.timestamp for message in messages[2:7]
    ]
    assert response.items[2].timestamp == anchor
    assert response.paging.has_older is True
    assert response.paging.has_newer is True
    assert response.context.mode == "around"
    assert response.context.anchor_timestamp == anchor
    assert response.context.highlighted_timestamp == anchor


def test_search_messages_supports_simple_and_fts_queries(
    imported_archive, session_factory
) -> None:
    with session_factory() as session:
        repository = SearchRepository(session)

        simple = repository.search_messages(
            SearchRequest(query="github", mode="simple", user_id=303)
        )
        fts = repository.search_messages(
            SearchRequest(query="github", mode="fts", user_id=303)
        )

    assert simple.total == 1
    assert fts.total == 1
    assert simple.items[0].timestamp == fts.items[0].timestamp
    assert "github.com" in simple.items[0].text


def test_search_messages_applies_filters_and_offset(
    imported_archive, session_factory
) -> None:
    with session_factory() as session:
        repository = SearchRepository(session)
        response = repository.search_messages(
            SearchRequest(
                query="https",
                mode="simple",
                user_id=202,
                date_from=datetime(2020, 9, 1, 0, 0, 0, tzinfo=UTC),
                date_to=datetime(2020, 9, 1, 23, 59, 59, tzinfo=UTC),
                limit=1,
                offset=0,
            )
        )

    assert response.total == 3
    assert len(response.items) == 1
    assert response.items[0].user_id == 202
    assert response.items[0].timestamp == datetime(2020, 9, 1, 23, 31, 45, tzinfo=UTC)
    assert "https://" in response.items[0].text


def test_search_messages_offset_returns_next_page(
    imported_archive, session_factory
) -> None:
    with session_factory() as session:
        repository = SearchRepository(session)
        first_page = repository.search_messages(
            SearchRequest(
                query="https",
                mode="simple",
                user_id=202,
                limit=1,
                offset=0,
            )
        )
        second_page = repository.search_messages(
            SearchRequest(
                query="https",
                mode="simple",
                user_id=202,
                limit=1,
                offset=1,
            )
        )

    assert first_page.total == second_page.total == 4
    assert len(first_page.items) == 1
    assert len(second_page.items) == 1
    assert first_page.items[0].user_id == second_page.items[0].user_id == 202
    assert first_page.items[0].timestamp > second_page.items[0].timestamp
    assert "https://" in first_page.items[0].text
    assert "https://" in second_page.items[0].text


def test_search_messages_rejects_queries_without_searchable_tokens(
    session_factory,
) -> None:
    with session_factory() as session:
        repository = SearchRepository(session)

        with pytest.raises(
            ValueError, match="Search query must contain at least one searchable token"
        ):
            repository.search_messages(SearchRequest(query="!!!", mode="simple"))


def test_refresh_from_import_updates_aggregates_and_display_name(
    session_factory,
) -> None:
    first_batch = ParsedConversationFile(
        user_id=777,
        owner_user_id=0,
        display_name="Old Name",
        messages=[
            ParsedMessage(
                timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
                direction="inbound",
                text="first",
                has_attachments=False,
            ),
            ParsedMessage(
                timestamp=datetime(2024, 1, 2, 10, 0, 0, tzinfo=UTC),
                direction="outbound",
                text="second",
                has_attachments=False,
            ),
        ],
    )
    second_batch = ParsedConversationFile(
        user_id=777,
        owner_user_id=0,
        display_name="New Name",
        messages=[
            ParsedMessage(
                timestamp=datetime(2024, 1, 2, 10, 0, 0, tzinfo=UTC),
                direction="outbound",
                text="second duplicate",
                has_attachments=False,
            ),
            ParsedMessage(
                timestamp=datetime(2024, 1, 3, 10, 0, 0, tzinfo=UTC),
                direction="inbound",
                text="third",
                has_attachments=False,
            ),
        ],
    )

    with session_factory() as session:
        conversation_repository = ConversationRepository(session)
        message_repository = MessageRepository(session)

        conversation_repository.ensure_conversation(first_batch)
        inserted, skipped = message_repository.insert_messages(first_batch)
        assert inserted == 2
        assert skipped == 0

        conversation_repository.ensure_conversation(second_batch)
        inserted, skipped = message_repository.insert_messages(second_batch)
        assert inserted == 1
        assert skipped == 1

        conversation_repository.refresh_from_import({777})
        session.commit()

        conversation = session.get(Conversation, 777)
        exported = message_repository.export_messages(
            ExportRequest(user_id=777, limit=10, format="json")
        )

    assert conversation is not None
    assert conversation.display_name == "New Name"
    assert conversation.message_count == 3
    assert conversation.first_message_at == datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
    assert conversation.last_message_at == datetime(2024, 1, 3, 10, 0, 0, tzinfo=UTC)
    assert [item.timestamp for item in exported] == [
        datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 2, 10, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 3, 10, 0, 0, tzinfo=UTC),
    ]
