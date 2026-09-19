from datetime import datetime

from pydantic import BaseModel


class MemberOut(BaseModel):
    id: str
    display_name: str
    initials: str
    is_owner: bool
    created_at: datetime

    model_config = {"from_attributes": True}
