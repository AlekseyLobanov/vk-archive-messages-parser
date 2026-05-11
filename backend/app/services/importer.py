from collections.abc import Iterator
from pathlib import Path

import structlog
from sqlalchemy.orm import sessionmaker

from app.parsers.vk_html import VKHTMLParser
from app.repositories.storage import ConversationRepository, MessageRepository
from app.schemas.api import ImportDone, ImportProgress


class ImportService:
    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory
        self.parser = VKHTMLParser()
        self.logger = structlog.get_logger(__name__)

    def import_archive(
        self, root_path: Path
    ) -> Iterator[tuple[str, ImportProgress | ImportDone]]:
        if not root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {root_path}")

        html_files = sorted(root_path.rglob("messages*.html"))
        total = len(html_files)
        errors = 0
        imported = 0
        skipped = 0
        touched_user_ids: set[int] = set()

        self.logger.info("import.started", root_path=str(root_path), total_files=total)

        for index, html_file in enumerate(html_files):
            with self.session_factory() as session:
                try:
                    parsed_file = self.parser.parse_file(html_file)
                    message_repository = MessageRepository(session)
                    conversation_repository = ConversationRepository(session)

                    conversation_repository.ensure_conversation(parsed_file)
                    touched_user_ids.add(parsed_file.user_id)
                    inserted_count, skipped_count = message_repository.insert_messages(
                        parsed_file
                    )
                    session.commit()

                    imported += inserted_count
                    skipped += skipped_count
                    self.logger.info(
                        "import.file_processed",
                        file_path=str(html_file),
                        user_id=parsed_file.user_id,
                        display_name=parsed_file.display_name,
                        messages_in_file=len(parsed_file.messages),
                        imported=inserted_count,
                        skipped=skipped_count,
                        status="processed",
                    )
                except Exception as exc:
                    # Best-effort import is intentional: one bad file should not stop
                    # the rest of the local archive from being processed.
                    session.rollback()
                    errors += 1
                    self.logger.exception(
                        "import.file_failed",
                        file_path=str(html_file),
                        reason=str(exc),
                        status="failed",
                    )

            yield (
                "progress",
                ImportProgress(
                    total=total,
                    remains=total - index - 1,
                    errors=errors,
                    imported=imported,
                    skipped=skipped,
                ),
            )

        with self.session_factory() as session:
            ConversationRepository(session).refresh_from_import(touched_user_ids)
            session.commit()

        self.logger.info(
            "import.finished",
            root_path=str(root_path),
            total_files=total,
            errors=errors,
            imported=imported,
            skipped=skipped,
        )
        yield (
            "done",
            ImportDone(
                total=total,
                remains=0,
                errors=errors,
                imported=imported,
                skipped=skipped,
            ),
        )
