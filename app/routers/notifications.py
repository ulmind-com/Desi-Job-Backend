from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.schemas.notification import NotificationOut, NotificationMarkRead
from app.core.security import require_auth
from app.services.seed_service import store

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("")
async def get_my_notifications(user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    notifs = [n for n in store.notifications.values() if n["user_id"] == user_id]
    notifs.sort(key=lambda x: x["created_at"], reverse=True)
    return notifs

@router.get("/unread-count")
async def get_unread_count(user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    count = sum(1 for n in store.notifications.values() if n["user_id"] == user_id and not n.get("is_read", False))
    return {"unread_count": count}

@router.patch("/mark-read")
async def mark_notifications_read(req: NotificationMarkRead, user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    ids_to_mark = set(req.notification_ids)
    
    for n in store.notifications.values():
        if n["user_id"] == user_id:
            if not ids_to_mark or n["id"] in ids_to_mark:
                n["is_read"] = True
                
    return {"message": "Notifications marked as read"}
