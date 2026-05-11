from datetime import UTC, datetime

from sqlalchemy.types import String, TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    impl = String(64)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> str | None:
        if value is None:
            return None

        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        else:
            value = value.astimezone(UTC)

        return value.isoformat()

    def process_result_value(
        self, value: str | datetime | None, dialect
    ) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)

        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
