from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.member import MemberOut


class CreateHouseholdRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    household_name: str = Field(min_length=1, max_length=120)
    password: Optional[str] = Field(default=None, max_length=100)

    @field_validator("display_name", "household_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("cannot be blank")
        return v.strip()

    @field_validator("password")
    @classmethod
    def blank_password_is_none(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            return None
        if v is not None and len(v.encode()) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return v


class JoinHouseholdRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    room_code: str = Field(min_length=1, max_length=12)
    password: Optional[str] = Field(default=None, max_length=100)

    @field_validator("display_name", "room_code")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("cannot be blank")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_byte_limit(cls, v):
        if v is not None and len(v.encode()) > 72:
            raise ValueError("Password must be at most 72 UTF-8 bytes")
        return v


class HouseholdOut(BaseModel):
    id: str
    name: str
    room_code: str
    has_password: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    """Returned on create/join: the household plus a bearer token for the new member."""

    household: HouseholdOut
    member: MemberOut
    session_token: str
    members: list[MemberOut]
