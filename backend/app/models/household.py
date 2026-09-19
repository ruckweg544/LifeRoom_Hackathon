from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid, utcnow


class Household(TimestampMixin, Base):
    """A private shared-living space. Every household-owned record links back here."""

    __tablename__ = "households"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Short, human-shareable code roommates use to join (e.g. "FRX482").
    room_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)

    # Optional password, stored as a bcrypt hash only - never plaintext.
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_by_member_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    members: Mapped[list["Member"]] = relationship(back_populates="household", cascade="all, delete-orphan")  # noqa: F821

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None
