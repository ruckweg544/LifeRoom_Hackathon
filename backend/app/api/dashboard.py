from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_member
from app.database.session import get_db
from app.models.activity import Activity
from app.models.bill import Bill
from app.models.chore import Chore
from app.models.grocery import GroceryItem
from app.models.member import Member
from app.models.message import Message
from app.schemas.activity import ActivityOut
from app.schemas.bill import BillOut
from app.schemas.chore import ChoreOut
from app.schemas.dashboard import DashboardOut, DashboardSummary
from app.schemas.grocery import GroceryOut
from app.schemas.message import MessageOut
from app.services.presence import online_count

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(current_member: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    household_id = current_member.household_id
    members_by_id = {m.id: m for m in db.query(Member).filter(Member.household_id == household_id).all()}

    # --- Chores ---
    all_chores = (
        db.query(Chore)
        .filter(Chore.household_id == household_id, Chore.completed.is_(False))
        .order_by(Chore.due_date.asc().nulls_last(), Chore.created_at.desc())
        .all()
    )
    now = datetime.now(timezone.utc)
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    todays_chores_models = [c for c in all_chores if c.due_date is None or c.due_date <= end_of_today][:5]

    def chore_out(c: Chore):
        out = ChoreOut.model_validate(c)
        out.assigned_to_name = members_by_id.get(c.assigned_to_id).display_name if c.assigned_to_id in members_by_id else None
        out.created_by_name = members_by_id.get(c.created_by_id).display_name if c.created_by_id in members_by_id else None
        return out

    # --- Messages ---
    recent_messages = (
        db.query(Message)
        .filter(Message.household_id == household_id)
        .order_by(Message.created_at.desc())
        .limit(5)
        .all()
    )

    # --- Bills ---
    all_bills = db.query(Bill).options(selectinload(Bill.participants)).filter(Bill.household_id == household_id).order_by(Bill.created_at.desc()).all()

    def bill_out(b: Bill):
        out = BillOut.model_validate(b)
        payer = members_by_id.get(b.paid_by_id)
        out.paid_by_name = payer.display_name if payer else None
        for p in out.participants:
            m = members_by_id.get(p.member_id)
            p.member_name = m.display_name if m else None
        return out

    you_owe_cents = 0
    you_are_owed_cents = 0
    for b in all_bills:
        for p in b.participants:
            if p.settled:
                continue
            if p.member_id == current_member.id and b.paid_by_id != current_member.id:
                you_owe_cents += p.share_cents
            if b.paid_by_id == current_member.id and p.member_id != current_member.id:
                you_are_owed_cents += p.share_cents

    # --- Groceries ---
    needed_items = (
        db.query(GroceryItem)
        .filter(GroceryItem.household_id == household_id, GroceryItem.purchased.is_(False))
        .order_by(GroceryItem.created_at.desc())
        .all()
    )

    def grocery_out(g: GroceryItem):
        out = GroceryOut.model_validate(g)
        added_by = members_by_id.get(g.added_by_id)
        out.added_by_name = added_by.display_name if added_by else None
        return out

    # --- Activity ---
    recent_activity = (
        db.query(Activity)
        .filter(Activity.household_id == household_id)
        .order_by(Activity.created_at.desc())
        .limit(10)
        .all()
    )

    summary = DashboardSummary(
        chores_due=len(all_chores),
        you_owe_cents=you_owe_cents,
        you_are_owed_cents=you_are_owed_cents,
        groceries_needed=len(needed_items),
        members_online=online_count(household_id),
        members_total=len(members_by_id),
    )

    return DashboardOut(
        summary=summary,
        todays_chores=[chore_out(c) for c in todays_chores_models],
        recent_messages=[MessageOut.model_validate(m) for m in reversed(recent_messages)],
        upcoming_bills=[bill_out(b) for b in all_bills[:5]],
        grocery_preview=[grocery_out(g) for g in needed_items[:6]],
        recent_activity=[ActivityOut.model_validate(a) for a in recent_activity],
    )
