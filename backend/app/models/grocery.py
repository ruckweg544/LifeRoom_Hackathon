from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.mixins import TimestampMixin, gen_uuid


class GroceryItem(TimestampMixin, Base):
    __tablename__ = "grocery_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"), index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    added_by_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    purchased: Mapped[bool] = mapped_column(default=False, nullable=False)
