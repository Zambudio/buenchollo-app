from datetime import datetime
from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    body: str | None
    link_url: str | None
    deal_id: str | None
    alert_id: str | None
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}
