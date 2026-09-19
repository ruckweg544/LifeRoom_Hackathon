import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class ActivityType(str, enum.Enum):
    chore_created = "CHORE_CREATED"
    chore_completed = "CHORE_COMPLETED"
    chore_reopened = "CHORE_REOPENED"
    bill_created = "BILL_CREATED"
    bill_settled = "BILL_SETTLED"
    grocery_added = "GROCERY_ADDED"
    grocery_purchased = "GROCERY_PURCHASED"
    member_joined = "MEMBER_JOINED"
    household_created = "HOUSEHOLD_CREATED"


class Activity(TimestampMixin, Base):
    """A simple, flat activity log used to power the Dashboard feed. Not event-sourced."""

    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True, nullable=False)

    type: Mapped[ActivityType] = mapped_column(Enum(ActivityType), nullable=False)
    actor_name: Mapped[str] = mapped_column(String(60), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
