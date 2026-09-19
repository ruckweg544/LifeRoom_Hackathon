from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class Member(TimestampMixin, Base):
    """A person belonging to exactly one household (MVP: no multi-household accounts)."""

    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True, nullable=False)

    display_name: Mapped[str] = mapped_column(String(60), nullable=False)

    # SHA-256 digest only; raw bearer token is returned once to the client.
    session_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    is_owner: Mapped[bool] = mapped_column(default=False, nullable=False)

    household: Mapped["Household"] = relationship(back_populates="members")  # noqa: F821

    @property
    def initials(self) -> str:
        parts = self.display_name.strip().split()
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()
