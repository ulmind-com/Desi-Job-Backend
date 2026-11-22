from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationOut(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str  # "application", "status_update", "job_moderation", "system"
    link: Optional[str] = None
    is_read: bool = False
    created_at: datetime

class NotificationMarkRead(BaseModel):
    notification_ids: list[str] = []
