from app.websocket.connection_manager import manager
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_member
from app.database.session import get_db
from app.models.activity import ActivityType
from app.models.bill import Bill, BillParticipant
from app.models.member import Member
from app.schemas.bill import BillOut, CreateBillRequest
from app.services.activity_service import log_activity
from app.services.money import dollars_to_cents, format_cents_usd, split_equally

router = APIRouter(prefix="/api/bills", tags=["bills"])


def _to_out(bill: Bill, db: Session, member_names=None) -> BillOut:
    if member_names is None:
        member_names = {m.id: m.display_name for m in db.query(Member).filter(Member.household_id == bill.household_id).all()}
    out = BillOut.model_validate(bill)
    out.paid_by_name = member_names.get(bill.paid_by_id)
    for p in out.participants:
        p.member_name = member_names.get(p.member_id)
    return out


@router.get("", response_model=list[BillOut])
def list_bills(current_member: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    bills = (
        db.query(Bill).options(selectinload(Bill.participants))
        .filter(Bill.household_id == current_member.household_id)
        .order_by(Bill.created_at.desc())
        .all()
    )
    names = {m.id: m.display_name for m in db.query(Member).filter(Member.household_id == current_member.household_id).all()}
    return [_to_out(b, db, names) for b in bills]


@router.post("", response_model=BillOut, status_code=status.HTTP_201_CREATED)
async def create_bill(
    payload: CreateBillRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    household_member_ids = {
        m.id for m in db.query(Member).filter(Member.household_id == current_member.household_id).all()
    }

    if payload.paid_by_id not in household_member_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payer is not a member of this household")

    unique_participant_ids = sorted(payload.participant_ids)
    for pid in unique_participant_ids:
        if pid not in household_member_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more participants are not members of this household")

    amount_cents = dollars_to_cents(payload.amount)
    shares = split_equally(amount_cents, len(unique_participant_ids))

    bill = Bill(
        household_id=current_member.household_id,
        title=payload.title,
        amount_cents=amount_cents,
        paid_by_id=payload.paid_by_id,
        created_by_id=current_member.id,
    )
    db.add(bill)
    db.flush()

    for member_id, share_cents in zip(unique_participant_ids, shares):
        participant = BillParticipant(
            bill_id=bill.id,
            member_id=member_id,
            share_cents=share_cents,
            # The payer's own share is automatically settled - they already paid it.
            settled=(member_id == payload.paid_by_id),
        )
        db.add(participant)

    db.flush()

    log_activity(
        db,
        current_member.household_id,
        ActivityType.bill_created,
        current_member.display_name,
        f'{current_member.display_name} added "{bill.title}" ({format_cents_usd(amount_cents)})',
    )

    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
    db.refresh(bill)
    return _to_out(bill, db)


@router.patch("/{bill_id}/participants/{participant_id}", response_model=BillOut)
async def update_participant_settlement(
    bill_id: str,
    participant_id: str,
    settled: bool,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.household_id == current_member.household_id).first()
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    participant = db.query(BillParticipant).filter(BillParticipant.id == participant_id, BillParticipant.bill_id == bill.id).first()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found on this bill")

    if participant.member_id == bill.paid_by_id and not settled:
        raise HTTPException(400, "The payer has already paid their own share")
    participant.settled = settled
    db.flush()

    if settled:
        log_activity(
            db,
            current_member.household_id,
            ActivityType.bill_settled,
            current_member.display_name,
            f'{current_member.display_name} marked their share of "{bill.title}" as paid',
        )

    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
    db.refresh(bill)
    return _to_out(bill, db)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bill(
    bill_id: str,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.household_id == current_member.household_id).first()
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    db.delete(bill)
    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
