from app.websocket.connection_manager import manager
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.deps import get_current_member
from app.database.session import get_db
from app.models.member import Member
from app.schemas.member import MemberOut
from app.services.presence import online_member_ids

router = APIRouter(prefix="/api/members", tags=["members"])


class MemberWithPresence(MemberOut):
    online: bool


class UpdateMemberRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)

    @field_validator("display_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("display name cannot be blank")
        return v.strip()


@router.get("", response_model=list[MemberWithPresence])
def list_members(current_member: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    members = (
        db.query(Member)
        .filter(Member.household_id == current_member.household_id)
        .order_by(Member.created_at.asc())
        .all()
    )
    online_ids = online_member_ids(current_member.household_id)
    return [
        MemberWithPresence(**MemberOut.model_validate(m).model_dump(), online=m.id in online_ids)
        for m in members
    ]


@router.patch("/me", response_model=MemberOut)
async def update_my_profile(
    payload: UpdateMemberRequest,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Member)
        .filter(
            Member.household_id == current_member.household_id,
            Member.display_name == payload.display_name,
            Member.id != current_member.id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That display name is already taken in this household")

    current_member.display_name = payload.display_name
    db.add(current_member)
    db.commit()
    await manager.broadcast(current_member.household_id, {"type": "household.changed"})
    db.refresh(current_member)
    return MemberOut.model_validate(current_member)
