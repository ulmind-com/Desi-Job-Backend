import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from app.schemas.application import (
    ApplicationCreate, ApplicationStatusUpdate, ApplicationOut, ApplicationListResponse
)
from app.core.security import require_auth
from app.services.seed_service import store

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("", response_model=ApplicationOut)
async def submit_application(req: ApplicationCreate, user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    
    # Check if job exists and is active
    job = store.jobs.get(req.job_id)
    if not job or job.get("status") != "active":
        raise HTTPException(status_code=400, detail="This job opening is no longer active or accepting applications")

    # Prevent duplicate applications
    for app in store.applications.values():
        if app.get("job_id") == req.job_id and app.get("user_id") == user_id:
            raise HTTPException(status_code=400, detail="You have already applied for this position")

    # Locate resume snapshot
    resume_snapshot = None
    resume_id = req.resume_id
    if not resume_id:
        # Check user's default resume
        user_obj = store.users.get(user_id, {})
        resume_id = user_obj.get("default_resume_id")
        
    if resume_id and resume_id in store.resumes:
        resume_snapshot = store.resumes[resume_id]["data"]
    elif req.custom_resume_data:
        resume_snapshot = req.custom_resume_data

    app_id = f"app_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    
    application = {
        "id": app_id,
        "job_id": req.job_id,
        "job_title": job["title"],
        "company_name": job["company"],
        "job_location": job["location"],
        "user_id": user_id,
        "full_name": req.full_name,
        "email": req.email,
        "phone": req.phone,
        "cover_letter": req.cover_letter,
        "resume_id": resume_id,
        "resume_snapshot": resume_snapshot,
        "status": "Applied",
        "employer_notes": None,
        "created_at": now,
        "updated_at": now
    }
    
    store.applications[app_id] = application
    job["applications_count"] = job.get("applications_count", 0) + 1
    
    # Trigger notification to job owner/employer
    employer_id = job.get("employer_id")
    if employer_id:
        store.notifications[f"notif_{uuid.uuid4().hex[:8]}"] = {
            "id": f"notif_{uuid.uuid4().hex[:8]}",
            "user_id": employer_id,
            "title": f"New Application: {job['title']}",
            "message": f"{req.full_name} has just applied for '{job['title']}'.",
            "type": "application",
            "link": f"/dashboard?tab=applications",
            "is_read": False,
            "created_at": now
        }
        
    return application

@router.get("/my-applications", response_model=ApplicationListResponse)
async def get_my_applications(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(require_auth)
):
    user_id = user.get("sub")
    apps = [a for a in store.applications.values() if a["user_id"] == user_id]
    apps.sort(key=lambda x: x["created_at"], reverse=True)
    
    total = len(apps)
    total_pages = max(1, (total + limit - 1) // limit)
    start_idx = (page - 1) * limit
    
    return {
        "items": apps[start_idx:start_idx + limit],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

@router.get("/job/{job_id}")
async def get_applications_for_job(job_id: str, user: dict = Depends(require_auth)):
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    user_id = user.get("sub")
    role = user.get("role")
    
    if job.get("employer_id") != user_id and role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized to view applicants for this job")
        
    apps = [a for a in store.applications.values() if a["job_id"] == job_id]
    apps.sort(key=lambda x: x["created_at"], reverse=True)
    return apps

@router.patch("/{application_id}/status")
async def update_application_status(
    application_id: str,
    req: ApplicationStatusUpdate,
    user: dict = Depends(require_auth)
):
    app = store.applications.get(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    job = store.jobs.get(app["job_id"])
    user_id = user.get("sub")
    role = user.get("role")
    
    if job and job.get("employer_id") != user_id and role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Unauthorized to modify application status")

    app["status"] = req.status
    if req.employer_notes is not None:
        app["employer_notes"] = req.employer_notes
    now = datetime.now(timezone.utc)
    app["updated_at"] = now
    
    # Notify applicant
    store.notifications[f"notif_{uuid.uuid4().hex[:8]}"] = {
        "id": f"notif_{uuid.uuid4().hex[:8]}",
        "user_id": app["user_id"],
        "title": "Application Status Update",
        "message": f"Your application for '{app['job_title']}' has been updated to '{req.status}'.",
        "type": "status_update",
        "link": "/dashboard?tab=applications",
        "is_read": False,
        "created_at": now
    }

    return app

@router.post("/{application_id}/withdraw")
async def withdraw_application(application_id: str, user: dict = Depends(require_auth)):
    app = store.applications.get(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    user_id = user.get("sub")
    if app["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    app["status"] = "Withdrawn"
    app["updated_at"] = datetime.now(timezone.utc)
    return {"message": "Application withdrawn successfully"}
