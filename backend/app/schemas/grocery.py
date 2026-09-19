from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CreateGroceryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: int = Field(default=1, ge=1, le=999)

    @field_validator("name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("item name cannot be blank")
        return v.strip()


class UpdateGroceryRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    quantity: int | None = Field(default=None, ge=1, le=999)
    purchased: bool | None = None

    @field_validator("name", "quantity", "purchased")
    @classmethod
    def required_if_present(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError("Field cannot be null or blank")
        return value.strip() if isinstance(value, str) else value


class GroceryOut(BaseModel):
    id: str
    household_id: str
    name: str
    quantity: int
    added_by_id: str
    added_by_name: str | None = None
    purchased: bool
    created_at: datetime

    model_config = {"from_attributes": True}
