from __future__ import annotations

import argparse
import os
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from app.core.settings import Settings, get_settings
from app.db.init_db import run_migrations
from app.db.session import (
    create_engine,
    create_session_factory,
    resolve_database_url,
    sqlite_database_file,
)
from app.models import Conversation, Message


@dataclass(frozen=True)
class ConversationSeed:
    user_id: int
    display_name: str
    started_at: datetime
    topics: tuple[str, ...]
    incoming: tuple[str, ...]
    outgoing: tuple[str, ...]
    attachment_notes: tuple[str, ...]


@dataclass(frozen=True)
class DemoDataSummary:
    conversations: int
    messages: int
    database_url: str


SEED_CONVERSATIONS: tuple[ConversationSeed, ...] = (
    ConversationSeed(
        user_id=101001,
        display_name="Анна Петрова",
        started_at=datetime(2024, 11, 3, 9, 15, tzinfo=UTC),
        topics=("релиз", "макет", "демо", "таблица", "срок", "отчёт"),
        incoming=(
            "Смотри, я обновила {topic} и добавила комментарии.",
            "Можешь сегодня посмотреть {topic} после обеда?",
            "Я собрала промежуточную версию, там уже видно прогресс.",
            "Если успеем, давай завтра покажем это на демо.",
            "Проверь, пожалуйста, последний блок, я там ещё сомневаюсь.",
        ),
        outgoing=(
            "Да, беру в работу. Вернусь с правками через час.",
            "Посмотрел {topic}, там нужно чуть упростить формулировки.",
            "Давай так и сделаем, выглядит спокойнее и чище.",
            "Я добавил заметки по спорным местам прямо в документ.",
            "На демо покажем короткий сценарий без лишних деталей.",
        ),
        attachment_notes=(
            "Вложение: PDF с правками к релизу",
            "Вложение: скриншот обновлённого макета",
            "Вложение: таблица с задачами на неделю",
        ),
    ),
    ConversationSeed(
        user_id=101002,
        display_name="Илья Смирнов",
        started_at=datetime(2025, 1, 14, 20, 5, tzinfo=UTC),
        topics=("поездка", "маршрут", "билеты", "гостиница", "кофейня", "музей"),
        incoming=(
            "Я нашёл отличный {topic}, отправляю тебе вечером детали.",
            "Если выезжать пораньше, успеем и на {topic}, и на прогулку.",
            "Смотри, цены на {topic} снова немного изменились.",
            "Мне кажется, этот {topic} лучше оставить на субботу.",
            "Я отметил на карте пару мест, куда точно стоит зайти.",
        ),
        outgoing=(
            "Отлично, тогда я бронирую {topic} на себя.",
            "Давай без спешки, главное оставить время просто погулять.",
            "Если получится, хочу ещё зайти в местную книжную лавку.",
            "Да, такой {topic} мне подходит, выглядит удобно.",
            "Сохрани это, потом пригодится для финального плана.",
        ),
        attachment_notes=(
            "Вложение: фото улицы рядом с гостиницей",
            "Вложение: скрин расписания поездов",
            "Вложение: заметка с адресами кофеен",
        ),
    ),
    ConversationSeed(
        user_id=101003,
        display_name="Мама",
        started_at=datetime(2025, 2, 2, 7, 40, tzinfo=UTC),
        topics=("продукты", "врач", "посылка", "дача", "ужин", "погода"),
        incoming=(
            "Ты сегодня успеваешь заехать или лучше перенести?",
            "Я купила {topic}, но если надо, могу взять ещё.",
            "На даче снова тепло, думаю в выходные съездить.",
            "Не забудь, пожалуйста, написать после встречи.",
            "У меня всё спокойно, просто решила уточнить планы.",
        ),
        outgoing=(
            "Да, вечером наберу и всё уточним.",
            "После работы заеду, заодно завезу то, что обещал.",
            "Если погода не испортится, можно и правда выбраться.",
            "Спасибо, что напомнила, я чуть не забыл про {topic}.",
            "Напишу, как только освобожусь.",
        ),
        attachment_notes=(
            "Вложение: фото рассады на подоконнике",
            "Вложение: список покупок на неделю",
            "Вложение: фото пирога к ужину",
        ),
    ),
    ConversationSeed(
        user_id=101004,
        display_name="Олег Ким",
        started_at=datetime(2025, 3, 22, 18, 10, tzinfo=UTC),
        topics=("поход", "палатка", "тропа", "фонарь", "рюкзак", "костёр"),
        incoming=(
            "Я проверил {topic}, всё в хорошем состоянии.",
            "Если брать лёгкий рюкзак, будет намного комфортнее.",
            "На выходных обещают сухую погоду, шанс отличный.",
            "Мне нравится идея ночёвки у озера, место тихое.",
            "Я бы ещё взял запасной фонарь, на всякий случай.",
        ),
        outgoing=(
            "Хорошо, тогда я отвечаю за {topic} и еду.",
            "Согласен, перегружаться не хочется.",
            "Давай встречаться пораньше, чтобы выйти без спешки.",
            "Я возьму термос и аптечку, это точно пригодится.",
            "Маршрут нравится, особенно участок через сосны.",
        ),
        attachment_notes=(
            "Вложение: карта тропы в лесу",
            "Вложение: фото места для палатки",
            "Вложение: список снаряжения в заметках",
        ),
    ),
    ConversationSeed(
        user_id=101005,
        display_name="Марина Волкова",
        started_at=datetime(2025, 4, 8, 11, 30, tzinfo=UTC),
        topics=("ремонт", "плитка", "кухня", "смета", "доставка", "лампа"),
        incoming=(
            "Мастер прислал новую {topic}, там есть несколько правок.",
            "Я сравнила варианты, этот {topic} выглядит практичнее.",
            "Если хочешь, вечером созвонимся и быстро всё решим.",
            "Мне написали по доставке, окно снова сдвинулось.",
            "Я нашла лампу, которая хорошо подходит по цвету.",
        ),
        outgoing=(
            "Скинь {topic}, я посмотрю внимательно.",
            "Лучше взять спокойный вариант, чтобы не надоел через месяц.",
            "Созвон вечером подходит, после семи я на месте.",
            "Если доставка опять поедет, перенесём сборку кухни.",
            "Да, такая лампа хорошо впишется в общий вид.",
        ),
        attachment_notes=(
            "Вложение: коллаж с вариантами плитки",
            "Вложение: фото кухни после замеров",
            "Вложение: обновлённая смета в PDF",
        ),
    ),
    ConversationSeed(
        user_id=101006,
        display_name="Сергей Орлов",
        started_at=datetime(2025, 5, 5, 8, 50, tzinfo=UTC),
        topics=("статья", "подкаст", "черновик", "обложка", "ссылка", "эпизод"),
        incoming=(
            "Я дочитал {topic}, там сильное начало.",
            "Для подкаста нужно чуть живее вступление, как думаешь?",
            "Ссылка на черновик у тебя должна уже открываться.",
            "Если будет время, посмотри новый заголовок.",
            "Хочу сегодня добить монтаж, чтобы утром уже выложить.",
        ),
        outgoing=(
            "Да, после обеда открою {topic} и отмечу спорные места.",
            "Вступление можно сделать короче, так будет бодрее.",
            "Заголовок хороший, но я бы убрал одно длинное слово.",
            "Оставь текущую структуру, она нормально ведёт слушателя.",
            "Когда выложишь эпизод, я сделаю пару скриншотов для анонса.",
        ),
        attachment_notes=(
            "Вложение: аудиофайл с черновым монтажом",
            "Вложение: заметка с вариантами заголовка",
            "Вложение: обложка выпуска в PNG",
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill the local database with realistic Russian demo messages."
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to TOML config. Overrides VK_ARCHIVE_CONFIG for this process.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing demo database contents before generation.",
    )
    parser.add_argument(
        "--messages-per-conversation",
        type=int,
        default=36,
        help="How many messages to generate for each conversation.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for reproducible screenshots.",
    )
    return parser.parse_args()


def load_settings(config_path: Path | None) -> Settings:
    if config_path is None:
        return get_settings()

    os.environ["VK_ARCHIVE_CONFIG"] = str(config_path.expanduser().resolve())
    get_settings.cache_clear()
    return get_settings()


def build_message_text(
    seed: ConversationSeed,
    rng: random.Random,
    index: int,
    outgoing: bool,
) -> tuple[str, bool]:
    topic = rng.choice(seed.topics)
    pool = seed.outgoing if outgoing else seed.incoming
    text_value = rng.choice(pool).format(topic=topic)

    extras = [
        "Без спешки, но лучше закрыть это сегодня.",
        "Если что, вечером ещё вернёмся к деталям.",
        "Я пометил это как приоритет на ближайшие дни.",
        "Думаю, в таком виде уже можно показывать людям.",
        "Главное не переусложнить, сейчас и так выглядит хорошо.",
        "Оставлю это здесь, чтобы не потерять в потоке сообщений.",
    ]
    if index % 5 == 0:
        text_value = f"{text_value} {rng.choice(extras)}"

    has_attachments = index % 7 == 0
    if has_attachments:
        text_value = f"{text_value}\n{rng.choice(seed.attachment_notes)}"

    return text_value, has_attachments


def build_conversation_messages(
    seed: ConversationSeed,
    rng: random.Random,
    messages_per_conversation: int,
) -> list[Message]:
    timestamp = seed.started_at
    messages: list[Message] = []

    for index in range(messages_per_conversation):
        outgoing = index % 2 == 1
        text_value, has_attachments = build_message_text(seed, rng, index, outgoing)
        timestamp += timedelta(
            minutes=rng.randint(8, 180),
            hours=1 if index % 9 == 0 else 0,
            days=1 if index % 11 == 0 else 0,
        )
        messages.append(
            Message(
                user_id=seed.user_id,
                timestamp=timestamp,
                direction="outgoing" if outgoing else "incoming",
                text=text_value,
                has_attachments=has_attachments,
            )
        )

    return messages


def reset_database_if_needed(settings: Settings) -> None:
    sqlite_file = sqlite_database_file(settings.database.url)
    if sqlite_file is not None and sqlite_file.exists():
        sqlite_file.unlink()


def generate_demo_dataset(
    settings: Settings,
    *,
    reset: bool,
    messages_per_conversation: int,
    seed: int,
) -> DemoDataSummary:
    if messages_per_conversation <= 0:
        raise ValueError("messages_per_conversation must be greater than zero")

    if reset:
        reset_database_if_needed(settings)

    run_migrations(settings)
    engine = create_engine(settings.database.url)
    session_factory = create_session_factory(engine)
    rng = random.Random(seed)

    try:
        with session_factory() as session:
            if reset:
                session.execute(text("DELETE FROM messages_fts"))
                session.execute(text("DELETE FROM messages"))
                session.execute(text("DELETE FROM conversations"))
                session.commit()

            total_messages = 0
            for conversation_seed in SEED_CONVERSATIONS:
                messages = build_conversation_messages(
                    conversation_seed, rng, messages_per_conversation
                )
                conversation = Conversation(
                    user_id=conversation_seed.user_id,
                    display_name=conversation_seed.display_name,
                    first_message_at=messages[0].timestamp,
                    last_message_at=messages[-1].timestamp,
                    message_count=len(messages),
                )
                session.merge(conversation)
                session.add_all(messages)
                session.flush()

                session.execute(
                    text(
                        """
                        INSERT INTO messages_fts(message_id, user_id, timestamp, text)
                        VALUES (:message_id, :user_id, :timestamp, :text)
                        """
                    ),
                    [
                        {
                            "message_id": message.id,
                            "user_id": message.user_id,
                            "timestamp": message.timestamp.isoformat(),
                            "text": message.text,
                        }
                        for message in messages
                    ],
                )
                total_messages += len(messages)

            session.commit()
    finally:
        engine.dispose()

    return DemoDataSummary(
        conversations=len(SEED_CONVERSATIONS),
        messages=total_messages,
        database_url=resolve_database_url(settings.database.url),
    )


def main() -> None:
    args = parse_args()
    settings = load_settings(args.config)
    summary = generate_demo_dataset(
        settings,
        reset=args.reset,
        messages_per_conversation=args.messages_per_conversation,
        seed=args.seed,
    )
    print(
        "Generated demo dataset:",
        f"{summary.conversations} conversations, {summary.messages} messages,",
        f"database={summary.database_url}",
    )


if __name__ == "__main__":
    main()
