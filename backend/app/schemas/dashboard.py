from pydantic import BaseModel

from app.schemas.activity import ActivityOut
from app.schemas.bill import BillOut
from app.schemas.chore import ChoreOut
from app.schemas.grocery import GroceryOut
from app.schemas.message import MessageOut


class DashboardSummary(BaseModel):
    chores_due: int
    you_owe_cents: int
    you_are_owed_cents: int
    groceries_needed: int
    members_online: int
    members_total: int


class DashboardOut(BaseModel):
    summary: DashboardSummary
    todays_chores: list[ChoreOut]
    recent_messages: list[MessageOut]
    upcoming_bills: list[BillOut]
    grocery_preview: list[GroceryOut]
    recent_activity: list[ActivityOut]
