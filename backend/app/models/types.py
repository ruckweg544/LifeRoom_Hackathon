"""
Custom SQLAlchemy column type that guarantees timezone-aware UTC datetimes on
the way back out of the database - regardless of backend.

Why this exists: SQLite has no native timezone-aware storage. SQLAlchemy's
plain `DateTime(timezone=True)` happily accepts an aware datetime on write,
but SQLite's dialect returns a naive `datetime` on read. That silently mixes
naive and aware datetimes in the app (e.g. comparing a chore's `due_date` to
`datetime.now(timezone.utc)`), which raises `TypeError: can't compare
offset-naive and offset-aware datetimes` - exactly the kind of bug that only
shows up once you actually run the app against real data.

`UTCDateTime` always stores naive UTC internally (so both SQLite and
Postgres behave the same way) and always re-attaches `tzinfo=UTC` when a
value comes back out, so every datetime the rest of the app sees is
guaranteed to be timezone-aware UTC.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            # Treat naive input as already-UTC rather than guessing.
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
