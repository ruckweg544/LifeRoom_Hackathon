from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CreateBillRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, le=10000000, max_digits=10, decimal_places=2, allow_inf_nan=False, description="Exact dollar amount")
    paid_by_id: str
    participant_ids: list[str] = Field(min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be blank")
        return v.strip()

    @field_validator("participant_ids")
    @classmethod
    def unique_participants(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Duplicate participants")
        return value


class BillParticipantOut(BaseModel):
    id: str
    member_id: str
    member_name: str | None = None
    share_cents: int
    settled: bool

    model_config = {"from_attributes": True}


class BillOut(BaseModel):
    id: str
    household_id: str
    title: str
    amount_cents: int
    paid_by_id: str
    paid_by_name: str | None = None
    created_by_id: str
    created_at: datetime
    participants: list[BillParticipantOut]

    model_config = {"from_attributes": True}
