from app.websocket.connection_manager import manager
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_member
from app.core.security import (
    generate_room_code,
    generate_session_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.database.session import get_db
from app.models.activity import ActivityType
from app.models.household import Household
from app.models.member import Member
from app.schemas.household import (
    CreateHouseholdRequest,
    HouseholdOut,
    JoinHouseholdRequest,
    SessionOut,
)
from app.schemas.member import MemberOut
from app.services.activity_service import log_activity

router = APIRouter(prefix="/api/households", tags=["households"])


def _unique_room_code(db: Session) -> str:
    for _ in range(25):
        code = generate_room_code()
        if not db.query(Household).filter(Household.room_code == code).first():
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique room code, please retry")


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_household(payload: CreateHouseholdRequest, db: Session = Depends(get_db)):
    household = Household(
        name=payload.household_name,
        room_code=_unique_room_code(db),
        password_hash=hash_password(payload.password) if payload.password else None,
    )
    db.add(household)
    db.flush()

    token = generate_session_token()
    member = Member(
        household_id=household.id,
        display_name=payload.display_name,
        session_token=hash_token(token),
        is_owner=True,
    )
    db.add(member)
    db.flush()

    household.created_by_member_id = member.id

    log_activity(
        db,
        household.id,
        ActivityType.household_created,
        member.display_name,
        f"{member.display_name} created {household.name}",
    )

    db.commit()
    await manager.broadcast(household.id, {"type": "household.changed"})
    db.refresh(household)
    db.refresh(member)

    return SessionOut(
        household=HouseholdOut.model_validate(household),
        member=MemberOut.model_validate(member),
        session_token=token,
        members=[MemberOut.model_validate(member)],
    )


@router.post("/join", response_model=SessionOut)
async def join_household(payload: JoinHouseholdRequest, db: Session = Depends(get_db)):
    household = (
        db.query(Household).filter(Household.room_code == payload.room_code.upper()).first()
    )
    if household is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No household found with that room code")

    if household.has_password:
        if not payload.password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This household requires a password")
        if not verify_password(payload.password, household.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")

    existing = (
        db.query(Member)
        .filter(Member.household_id == household.id, Member.display_name == payload.display_name)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That display name is already taken in this household",
        )

    token = generate_session_token()
    member = Member(
        household_id=household.id,
        display_name=payload.display_name,
        session_token=hash_token(token),
        is_owner=False,
    )
    db.add(member)
    db.flush()

    log_activity(
        db,
        household.id,
        ActivityType.member_joined,
        member.display_name,
        f"{member.display_name} joined the household",
    )

    db.commit()
    await manager.broadcast(household.id, {"type": "household.changed"})
    db.refresh(household)
    db.refresh(member)

    all_members = (
        db.query(Member).filter(Member.household_id == household.id).order_by(Member.created_at.asc()).all()
    )

    return SessionOut(
        household=HouseholdOut.model_validate(household),
        member=MemberOut.model_validate(member),
        session_token=token,
        members=[MemberOut.model_validate(m) for m in all_members],
    )


@router.get("/me", response_model=SessionOut)
def get_my_household(
    request: Request,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    household = db.query(Household).filter(Household.id == current_member.household_id).first()
    if household is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")

    all_members = (
        db.query(Member).filter(Member.household_id == household.id).order_by(Member.created_at.asc()).all()
    )

    return SessionOut(
        household=HouseholdOut.model_validate(household),
        member=MemberOut.model_validate(current_member),
        session_token=request.headers["authorization"].split()[1],
        members=[MemberOut.model_validate(m) for m in all_members],
    )
