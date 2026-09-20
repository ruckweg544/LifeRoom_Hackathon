import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid
from app.models.types import UTCDateTime


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Chore(TimestampMixin, Base):
    __tablename__ = "chores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True, nullable=False)

    source_message_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, unique=True)

    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    assigned_to_id: Mapped[Optional[str]] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"), nullable=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)

    due_date: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.medium, nullable=False)

    completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)
