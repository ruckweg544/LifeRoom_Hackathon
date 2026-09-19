from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CreateMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message cannot be empty")
        return v.strip()


class MessageOut(BaseModel):
    id: str
    household_id: str
    member_id: str
    sender_name: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
