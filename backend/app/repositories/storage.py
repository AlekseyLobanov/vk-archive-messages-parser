import re
from datetime import datetime

from sqlalchemy import bindparam, desc, func, select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.types import UTCDateTime
from app.models import Conversation, Message
from app.parsers.vk_html.parser import ParsedConversationFile
from app.schemas.api import (
    ConversationItem,
    ExportMessageItem,
    ExportRequest,
    MessageContext,
    MessageItem,
    MessageListResponse,
    PagingInfo,
    SearchItem,
    SearchRequest,
    SearchResponse,
)


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_conversations(
        self, sort: str, order: str, limit: int, offset: int
    ) -> tuple[list[ConversationItem], int]:
        sort_column = (
            Conversation.last_message_at
            if sort == "last_message_at"
            else Conversation.message_count
        )
        direction = desc(sort_column) if order == "desc" else sort_column.asc()
        query = (
            select(Conversation)
            .order_by(direction, Conversation.user_id)
            .offset(offset)
            .limit(limit)
        )
        items = self.session.scalars(query).all()
        total = self.session.scalar(select(func.count()).select_from(Conversation)) or 0
        return [ConversationItem.model_validate(item) for item in items], total

    def ensure_conversation(self, parsed_file: ParsedConversationFile) -> Conversation:
        conversation = self.session.get(Conversation, parsed_file.user_id)
        if conversation is None:
            conversation = Conversation(
                user_id=parsed_file.user_id,
                display_name=parsed_file.display_name,
                first_message_at=None,
                last_message_at=None,
                message_count=0,
            )
            self.session.add(conversation)
            self.session.flush()
        else:
            conversation.display_name = parsed_file.display_name
        return conversation

    def refresh_from_import(self, user_ids: set[int]) -> None:
        if not user_ids:
            return

        stats_rows = self.session.execute(
            select(
                Message.user_id,
                func.count(Message.id),
                func.min(Message.timestamp),
                func.max(Message.timestamp),
            )
            .where(Message.user_id.in_(user_ids))
            .group_by(Message.user_id)
        ).all()
        stats_by_user_id = {
            row.user_id: (row[1] or 0, row[2], row[3]) for row in stats_rows
        }

        conversations = self.session.scalars(
            select(Conversation).where(Conversation.user_id.in_(user_ids))
        ).all()
        for conversation in conversations:
            message_count, first_message_at, last_message_at = stats_by_user_id.get(
                conversation.user_id, (0, None, None)
            )
            conversation.first_message_at = first_message_at
            conversation.last_message_at = last_message_at
            conversation.message_count = message_count


class MessageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_messages(self, parsed_file: ParsedConversationFile) -> tuple[int, int]:
        payload = [
            {
                "user_id": parsed_file.user_id,
                "timestamp": message.timestamp,
                "direction": message.direction,
                "text": message.text,
                "has_attachments": message.has_attachments,
            }
            for message in parsed_file.messages
        ]
        if not payload:
            return 0, 0

        statement = (
            sqlite_insert(Message)
            .values(payload)
            .on_conflict_do_nothing(index_elements=["user_id", "timestamp"])
            .returning(Message.id, Message.user_id, Message.timestamp, Message.text)
        )
        inserted_rows = self.session.execute(statement).all()
        skipped = len(payload) - len(inserted_rows)

        if inserted_rows:
            self.session.execute(
                text(
                    """
                    INSERT INTO messages_fts(message_id, user_id, timestamp, text)
                    VALUES (:message_id, :user_id, :timestamp, :text)
                    """
                ),
                [
                    {
                        "message_id": row.id,
                        "user_id": row.user_id,
                        "timestamp": row.timestamp.isoformat(),
                        "text": row.text,
                    }
                    for row in inserted_rows
                ],
            )

        return len(inserted_rows), skipped

    def list_messages(
        self,
        user_id: int,
        limit: int,
        before: datetime | None,
        after: datetime | None,
        around: datetime | None,
    ) -> MessageListResponse:
        if around and (before or after):
            raise ValueError("'around' cannot be combined with 'before' or 'after'")
        if limit <= 0:
            raise ValueError("'limit' must be greater than zero")

        if around:
            older = self.session.scalars(
                select(Message)
                .where(Message.user_id == user_id, Message.timestamp < around)
                .order_by(Message.timestamp.desc())
                .limit(limit + 1)
            ).all()
            anchor = self.session.scalar(
                select(Message)
                .where(Message.user_id == user_id, Message.timestamp == around)
                .limit(1)
            )
            newer = self.session.scalars(
                select(Message)
                .where(Message.user_id == user_id, Message.timestamp > around)
                .order_by(Message.timestamp.asc())
                .limit(limit + 1)
            ).all()

            has_older = len(older) > limit
            has_newer = len(newer) > limit
            items = list(reversed(older[:limit]))
            if anchor is not None:
                items.append(anchor)
            items.extend(newer[:limit])

            return self._build_response(
                items=items,
                limit=limit,
                has_older=has_older,
                has_newer=has_newer,
                mode="around",
                anchor_timestamp=around,
            )

        query = select(Message).where(Message.user_id == user_id)
        is_forward = after is not None

        if before:
            query = query.where(Message.timestamp < before)
        if after:
            query = query.where(Message.timestamp > after)
        order_by = Message.timestamp.asc() if is_forward else Message.timestamp.desc()

        items = self.session.scalars(query.order_by(order_by).limit(limit + 1)).all()
        has_more = len(items) > limit
        items = list(items[:limit])

        if not is_forward:
            items = list(reversed(items))
            has_older = has_more
            has_newer = (
                before is not None
                or bool(
                    self.session.scalar(
                        select(func.count())
                        .select_from(Message)
                        .where(
                            Message.user_id == user_id,
                            Message.timestamp > items[-1].timestamp,
                        )
                    )
                )
                if items
                else False
            )
        else:
            has_newer = has_more
            has_older = (
                after is not None
                or bool(
                    self.session.scalar(
                        select(func.count())
                        .select_from(Message)
                        .where(
                            Message.user_id == user_id,
                            Message.timestamp < items[0].timestamp,
                        )
                    )
                )
                if items
                else False
            )

        return self._build_response(
            items=items,
            limit=limit,
            has_older=has_older,
            has_newer=has_newer,
            mode="slice",
            anchor_timestamp=None,
        )

    def export_messages(self, request: ExportRequest) -> list[ExportMessageItem]:
        query = select(Message, Conversation.display_name).join(
            Conversation, Conversation.user_id == Message.user_id
        )
        if request.user_id is not None:
            query = query.where(Message.user_id == request.user_id)
        if request.date_from is not None:
            query = query.where(Message.timestamp >= request.date_from)
        if request.date_to is not None:
            query = query.where(Message.timestamp <= request.date_to)

        rows = self.session.execute(
            query.order_by(Message.timestamp.asc()).limit(request.limit)
        ).all()
        return [
            ExportMessageItem(
                user_id=message.user_id,
                display_name=display_name,
                timestamp=message.timestamp,
                direction=message.direction,
                text=message.text,
                has_attachments=message.has_attachments,
            )
            for message, display_name in rows
        ]

    def _build_response(
        self,
        items: list[Message],
        limit: int,
        has_older: bool,
        has_newer: bool,
        mode: str,
        anchor_timestamp: datetime | None,
    ) -> MessageListResponse:
        payload = [
            MessageItem(
                user_id=item.user_id,
                timestamp=item.timestamp,
                direction=item.direction,
                text=item.text,
                has_attachments=item.has_attachments,
            )
            for item in items
        ]
        paging = PagingInfo(
            limit=limit,
            has_older=has_older,
            has_newer=has_newer,
            next_before=payload[0].timestamp if payload else None,
            next_after=payload[-1].timestamp if payload else None,
        )
        context = MessageContext(
            mode=mode,
            anchor_timestamp=anchor_timestamp,
            highlighted_timestamp=anchor_timestamp,
        )
        return MessageListResponse(items=payload, paging=paging, context=context)


class SearchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search_messages(self, request: SearchRequest) -> SearchResponse:
        search_query = self._build_search_query(request.query, request.mode)
        filters = ["messages_fts.text MATCH :fts_query"]
        params: dict[str, object] = {
            "fts_query": search_query,
            "limit": request.limit,
            "offset": request.offset,
        }

        if request.user_id is not None:
            filters.append("m.user_id = :user_id")
            params["user_id"] = request.user_id
        if request.date_from is not None:
            filters.append("m.timestamp >= :date_from")
            params["date_from"] = request.date_from
        if request.date_to is not None:
            filters.append("m.timestamp <= :date_to")
            params["date_to"] = request.date_to

        where_clause = " AND ".join(filters)
        search_statement = text(
            f"""
            SELECT m.user_id, c.display_name, m.timestamp, m.direction, m.text
            FROM messages_fts
            JOIN messages m ON m.id = messages_fts.message_id
            JOIN conversations c ON c.user_id = m.user_id
            WHERE {where_clause}
            ORDER BY m.timestamp DESC
            LIMIT :limit OFFSET :offset
            """
        )
        total_statement = text(
            f"""
            SELECT COUNT(*)
            FROM messages_fts
            JOIN messages m ON m.id = messages_fts.message_id
            WHERE {where_clause}
            """
        )
        if request.date_from is not None:
            search_statement = search_statement.bindparams(
                bindparam("date_from", type_=UTCDateTime())
            )
            total_statement = total_statement.bindparams(
                bindparam("date_from", type_=UTCDateTime())
            )
        if request.date_to is not None:
            search_statement = search_statement.bindparams(
                bindparam("date_to", type_=UTCDateTime())
            )
            total_statement = total_statement.bindparams(
                bindparam("date_to", type_=UTCDateTime())
            )
        rows = self.session.execute(
            search_statement.columns(
                user_id=Message.user_id.type,
                display_name=Conversation.display_name.type,
                timestamp=UTCDateTime(),
                direction=Message.direction.type,
                text=Message.text.type,
            ),
            params,
        ).all()
        total = self.session.scalar(
            total_statement,
            params,
        )

        items = [
            SearchItem(
                user_id=row.user_id,
                display_name=row.display_name,
                timestamp=row.timestamp,
                direction=row.direction,
                text=row.text,
            )
            for row in rows
        ]
        return SearchResponse(items=items, total=total or 0)

    def _build_search_query(self, query: str, mode: str) -> str:
        if mode == "fts":
            return query

        tokens = re.findall(r"\w+", query, flags=re.UNICODE)
        if not tokens:
            raise ValueError("Search query must contain at least one searchable token")
        return " AND ".join(f'"{token}"' for token in tokens)
