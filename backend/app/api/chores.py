from app.websocket.connection_manager import manager
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.message import Message

from app.core.deps import get_current_member
from app.database.session import get_db
from app.models.activity import ActivityType
from app.models.chore import Chore
from app.models.member import Member
from app.models.mixins import utcnow
from app.schemas.chore import ChoreOut, CreateChoreRequest, UpdateChoreRequest
from app.services.activity_service import log_activity

router = APIRouter(prefix="/api/chores", tags=["chores"])


def _to_out(chore: Chore, db: Session) -> ChoreOut:
    assigned = db.query(Member).filter(Member.id == chore.assigned_to_id).first() if chore.assigned_to_id else None
    creator = db.query(Member).filter(Member.id == chore.created_by_id).first()
    out = ChoreOut.model_validate(chore)
    out.assigned_to_name = assigned.display_name if assigned else None
    out.created_by_name = creator.display_name if creator else None
    return out


def _get_household_chore(db: Session, chore_id: str, household_id: str) -> Chore:
    chore = db.query(Chore).filter(Chore.id == chore_id, Chore.household_id == household_id).first()
    if chore is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chore not found")
    return chore


@router.get("", response_model=list[ChoreOut])
def list_chores(current_member: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    chores = (
        db.query(Chore)
        .filter(Chore.household_id == current_member.household_id)
        .order_by(Chore.completed.asc(), Chore.due_date.asc().nulls_last(), Chore.created_at.desc())
        .all()
    )
    return [_to_out(c, db) for c in chores]


@router.post("", response_model=ChoreOut, status_code=status.HTTP_201_CREATED)
async def create_chore(
    payload: CreateChoreRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    if payload.source_message_id is not None:
        source = db.query(Message).filter(
            Message.id == payload.source_message_id,
            Message.household_id == current_member.household_id,
        ).first()
        if source is None:
            raise HTTPException(404, "Message not found")
        if db.query(Chore).filter(Chore.source_message_id == source.id).first():
            raise HTTPException(409, "This message already has a chore")

    if payload.assigned_to_id is not None:
        assignee = (
            db.query(Member)
            .filter(Member.id == payload.assigned_to_id, Member.household_id == current_member.household_id)
            .first()
        )
        if assignee is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee is not a member of this household")

    chore = Chore(
        source_message_id=payload.source_message_id,
        household_id=current_member.household_id,
        title=payload.title,
        description=payload.description,
        assigned_to_id=payload.assigned_to_id,
        created_by_id=current_member.id,
        due_date=payload.due_date,
        priority=payload.priority,
    )
    db.add(chore)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if payload.source_message_id and db.query(Chore).filter(
            Chore.source_message_id == payload.source_message_id,
            Chore.household_id == current_member.household_id,
        ).first():
            raise HTTPException(409, "This message already has a chore") from None
        raise

    log_activity(
        db,
        current_member.household_id,
        ActivityType.chore_created,
        current_member.display_name,
        f'{current_member.display_name} added "{chore.title}"',
    )

    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
    db.refresh(chore)
    return _to_out(chore, db)


@router.patch("/{chore_id}", response_model=ChoreOut)
async def update_chore(
    chore_id: str,
    payload: UpdateChoreRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    chore = _get_household_chore(db, chore_id, current_member.household_id)

    if payload.assigned_to_id is not None:
        assignee = db.query(Member).filter(
            Member.id == payload.assigned_to_id,
            Member.household_id == current_member.household_id,
        ).first()
        if assignee is None:
            raise HTTPException(400, "Assignee is not a member of this household")

    was_completed = chore.completed

    data = payload.model_dump(exclude_unset=True)
    for field in ("title", "description", "assigned_to_id", "due_date", "priority"):
        if field in data:
            setattr(chore, field, data[field])

    if "completed" in data:
        chore.completed = data["completed"]
        chore.completed_at = utcnow() if chore.completed else None

    db.flush()

    if chore.completed and not was_completed:
        log_activity(
            db,
            current_member.household_id,
            ActivityType.chore_completed,
            current_member.display_name,
            f'{current_member.display_name} completed "{chore.title}"',
        )
    elif not chore.completed and was_completed:
        log_activity(
            db,
            current_member.household_id,
            ActivityType.chore_reopened,
            current_member.display_name,
            f'{current_member.display_name} reopened "{chore.title}"',
        )

    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
    db.refresh(chore)
    return _to_out(chore, db)


@router.delete("/{chore_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chore(
    chore_id: str,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    chore = _get_household_chore(db, chore_id, current_member.household_id)
    db.delete(chore)
    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
