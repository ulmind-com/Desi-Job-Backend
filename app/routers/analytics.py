from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.services.seed_service import store

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class VisitPayload(BaseModel):
    path: str = "/"
    visitor_id: Optional[str] = None
    referrer: Optional[str] = None


@router.post("/visit")
async def record_website_visit(req: VisitPayload, request: Request):
    """Record a real website page visit from the public frontend."""
    visitor_id = req.visitor_id
    if not visitor_id and request.client:
        visitor_id = f"ip_{request.client.host}"

    stats = store.record_visit(
        path=req.path or "/",
        visitor_id=visitor_id,
        referrer=req.referrer,
    )
    return {"ok": True, **stats}
