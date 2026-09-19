from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.chore import Priority


class CreateChoreRequest(BaseModel):
    source_message_id: Optional[str] = Field(default=None, min_length=1, max_length=36)
    title: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    assigned_to_id: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Priority = Priority.medium

    @field_validator("title")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be blank")
        return v.strip()


class UpdateChoreRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    assigned_to_id: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[Priority] = None
    completed: Optional[bool] = None

    @field_validator("title", "priority", "completed")
    @classmethod
    def required_if_present(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError("Field cannot be null or blank")
        return value.strip() if isinstance(value, str) else value


class ChoreOut(BaseModel):
    source_message_id: Optional[str] = None
    id: str
    household_id: str
    title: str
    description: Optional[str]
    assigned_to_id: Optional[str]
    assigned_to_name: Optional[str] = None
    created_by_id: str
    created_by_name: Optional[str] = None
    due_date: Optional[datetime]
    priority: Priority
    completed: bool
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
