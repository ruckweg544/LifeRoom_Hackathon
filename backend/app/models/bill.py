from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class Bill(TimestampMixin, Base):
    """A shared expense. Amounts are stored in CENTS (integers) to avoid float rounding bugs."""

    __tablename__ = "bills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(120), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    paid_by_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)

    participants: Mapped[list["BillParticipant"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )


class BillParticipant(Base):
    """One member's equal-split share of a bill, and whether they've settled it."""

    __tablename__ = "bill_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    bill_id: Mapped[str] = mapped_column(ForeignKey("bills.id", ondelete="CASCADE"), index=True, nullable=False)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)

    share_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    settled: Mapped[bool] = mapped_column(default=False, nullable=False)

    bill: Mapped["Bill"] = relationship(back_populates="participants")
