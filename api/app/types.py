from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import PlainSerializer
from sqlalchemy import DateTime, Dialect
from sqlalchemy.types import TypeDecorator


def to_utc(value: datetime) -> datetime:
    """Normalize to aware UTC. Naive datetimes are rejected rather than guessed."""
    if value.tzinfo is None:
        raise ValueError("naive datetime; pass a timezone-aware value")
    return value.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return to_utc(value).isoformat().replace("+00:00", "Z")


class UTCDateTime(TypeDecorator[datetime]):
    """Stores aware datetimes as naive UTC (SQLite has no tz) and returns aware UTC on read."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else to_utc(value).replace(tzinfo=None)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=timezone.utc)


# Use in response schemas so JSON timestamps are always ISO 8601 ending in "Z".
UTCDatetimeJSON = Annotated[datetime, PlainSerializer(iso_z, return_type=str, when_used="json")]
