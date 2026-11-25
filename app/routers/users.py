from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.user import UserUpdateRequest, UserDashboardStats
from app.core.security import get_current_user_payload
from app.services.seed_service import store

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me")
async def get_my_profile(payload: dict = Depends(get_current_user_payload)):
    user_id = payload.get("sub")
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    safe = user.copy()
    safe.pop("hashed_password", None)
    return safe

@router.patch("/me")
async def update_my_profile(req: UserUpdateRequest, payload: dict = Depends(get_current_user_payload)):
    user_id = payload.get("sub")
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = req.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if v is not None:
            user[k] = v
    user["updated_at"] = datetime.now(timezone.utc)
    store.save_state()
    
    safe = user.copy()
    safe.pop("hashed_password", None)
    return safe

@router.get("/me/dashboard", response_model=UserDashboardStats)
async def get_user_dashboard(payload: dict = Depends(get_current_user_payload)):
    user_id = payload.get("sub")
    
    apps_count = sum(1 for a in store.applications.values() if a["user_id"] == user_id)
    posted_count = sum(1 for j in store.jobs.values() if j.get("employer_id") == user_id)
    res_count = sum(1 for r in store.resumes.values() if r["user_id"] == user_id)
    
    return {
        "applied_jobs_count": apps_count,
        "saved_jobs_count": 0,
        "posted_jobs_count": posted_count,
        "resumes_count": res_count
    }

@router.get("/{user_id}")
async def get_user_public_profile(user_id: str):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user["id"],
        "name": user["name"],
        "headline": user.get("headline"),
        "location": user.get("location"),
        "about": user.get("about"),
        "skills": user.get("skills", []),
        "avatar_url": user.get("avatar_url")
    }
