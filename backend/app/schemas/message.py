from datetime import date, datetime

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


class ChoreSuggestion(BaseModel):
    title: str
    assigned_to_id: str | None = None
    due_date: date | None = None
    due_at: datetime | None = None


class MessageAnalysisOut(BaseModel):
    message_id: str
    is_task: bool
    suggestion: ChoreSuggestion | None = None
