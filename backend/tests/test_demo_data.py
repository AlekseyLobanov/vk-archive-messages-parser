from sqlalchemy import func, select

from app.db.session import create_engine, create_session_factory
from app.models import Conversation, Message
from app.repositories.storage import SearchRepository
from app.schemas.api import SearchRequest
from scripts.generate_demo_data import generate_demo_dataset


def test_generate_demo_dataset_populates_database(test_settings) -> None:
    summary = generate_demo_dataset(
        test_settings,
        reset=True,
        messages_per_conversation=12,
        seed=7,
    )

    assert summary.conversations == 6
    assert summary.messages == 72

    engine = create_engine(test_settings.database.url)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            assert session.scalar(select(func.count()).select_from(Conversation)) == 6
            assert session.scalar(select(func.count()).select_from(Message)) == 72

            search_payload = SearchRepository(session).search_messages(
                SearchRequest(query="скриншотов", mode="simple", limit=10)
            )
            assert search_payload.total >= 1
    finally:
        engine.dispose()
