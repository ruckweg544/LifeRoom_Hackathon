from datetime import datetime

from pydantic import BaseModel

from app.models.activity import ActivityType


class ActivityOut(BaseModel):
    id: str
    household_id: str
    type: ActivityType
    actor_name: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
