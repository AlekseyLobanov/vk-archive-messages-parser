from alembic import context
from app.db.base import Base
from sqlalchemy import engine_from_config, pool, text

config = context.config

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()
            connection.execute(
                text(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
                    USING fts5(
                        message_id UNINDEXED,
                        user_id UNINDEXED,
                        timestamp UNINDEXED,
                        text,
                        tokenize = 'unicode61'
                    )
                    """
                )
            )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
