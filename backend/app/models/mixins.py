import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import UTCDateTime


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
