import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from app.schemas.admin import AdminDashboardKPIs, AuditLogOut
from app.schemas.job import JobModerationUpdate, JobCreate, JobOut
from app.core.security import require_admin
from app.services.seed_service import store

router = APIRouter(prefix="/admin", tags=["Super Admin"])

@router.get("/dashboard")
async def get_admin_dashboard_metrics(admin: dict = Depends(require_admin)):
    total_users = len(store.users)
    seekers = sum(1 for u in store.users.values() if u.get("role") == "job_seeker")
    employers = sum(1 for u in store.users.values() if u.get("role") == "employer")
    
    total_jobs = len(store.jobs)
    active_jobs = sum(1 for j in store.jobs.values() if j.get("status") == "active" and j.get("moderation_status") == "approved")
    pending_jobs = sum(1 for j in store.jobs.values() if j.get("moderation_status") == "pending")
    
    total_apps = len(store.applications)
    shortlisted = sum(1 for a in store.applications.values() if a.get("status") in ["Shortlisted", "Selected"])
    hired = sum(1 for a in store.applications.values() if a.get("status") == "Selected")
    rejected = sum(1 for a in store.applications.values() if a.get("status") == "Rejected")

    kpis = {
        "total_users": max(1534, total_users),
        "total_job_seekers": max(1242, seekers),
        "total_employers": max(292, employers),
        "total_jobs": max(104, total_jobs),
        "active_jobs": max(32, active_jobs),
        "pending_jobs": pending_jobs,
        "total_applications": max(1534, total_apps),
        "applications_today": 24,
        "total_categories": len(store.categories),
        "shortlisted_count": max(869, shortlisted),
        "hired_count": max(236, hired),
        "rejected_count": max(429, rejected),
        "cost_per_hire": 100.0,
        "offer_acceptance_rate": 80.0
    }

    # Recruitment Progress Funnel (from Image 2)
    funnel = [
        {"stage": "Applications", "count": 46200, "conversion_rate": "100%", "drop_off_rate": "0%"},
        {"stage": "Shortlisted", "count": 37500, "conversion_rate": "74%", "drop_off_rate": "-26%"},
        {"stage": "Interviews", "count": 29100, "conversion_rate": "63%", "drop_off_rate": "-22%"},
        {"stage": "Offers", "count": 18600, "conversion_rate": "40%", "drop_off_rate": "-36%"},
        {"stage": "Hires", "count": 12900, "conversion_rate": "28%", "drop_off_rate": "-31%"}
    ]

    # Hiring Sources Donut Chart (from Image 3)
    hiring_sources = [
        {"source": "LinkedIn", "percentage": 25.0, "color": "#17324D"},
        {"source": "Direct", "percentage": 22.0, "color": "#0284C7"},
        {"source": "Google", "percentage": 20.0, "color": "#F59E0B"},
        {"source": "Indeed", "percentage": 15.0, "color": "#10B981"},
        {"source": "WeWork", "percentage": 12.0, "color": "#8B5CF6"},
        {"source": "Internal", "percentage": 6.0, "color": "#EC4899"}
    ]

    # Applications by Department Donut Chart (from Image 4)
    departments = [
        {"department": "Engineering", "count": 120, "open_positions": 36},
        {"department": "Marketing", "count": 110, "open_positions": 18},
        {"department": "Sales", "count": 95, "open_positions": 22},
        {"department": "Customer Support", "count": 85, "open_positions": 12},
        {"department": "Finance", "count": 65, "open_positions": 8},
        {"department": "Human Resources", "count": 50, "open_positions": 6}
    ]

    # Application Pipeline Stage Matrix (from Image 3)
    pipeline_matrix = [
        {"position": "Sr. Full Stack Engineer", "lead": 14, "applicant": 8, "screening": 8, "first_round": 6, "second_round": 6, "final_round": 6, "offer": 5},
        {"position": "iOS Developer", "lead": 20, "applicant": 16, "screening": 14, "first_round": 14, "second_round": 12, "final_round": 8, "offer": 8},
        {"position": "Fresher Web Developer", "lead": 42, "applicant": 36, "screening": 36, "first_round": 32, "second_round": 28, "final_round": 20, "offer": 20},
        {"position": "Sr. Laravel Developer", "lead": 24, "applicant": 20, "screening": 20, "first_round": 18, "second_round": 16, "final_round": 16, "offer": 13},
        {"position": "Sr. UI/UX Designer", "lead": 48, "applicant": 48, "screening": 40, "first_round": 37, "second_round": 30, "final_round": 28, "offer": 20}
    ]

    # AI Insights: Top 3 candidates likely to convert (from Image 2)
    ai_top_candidates = [
        {"name": "Alex Dom Bringer", "role": "Frontend Developer", "conversion_likelihood": "66.2%", "confidence": 0.662, "rank": 1},
        {"name": "Elena Rostova", "role": "Full-Stack Engineer", "conversion_likelihood": "66.2%", "confidence": 0.662, "rank": 2},
        {"name": "Marcus Vance", "role": "UI/UX Designer", "conversion_likelihood": "66.2%", "confidence": 0.662, "rank": 3}
    ]

    return {
        "kpis": kpis,
        "funnel": funnel,
        "hiring_sources": hiring_sources,
        "departments": departments,
        "pipeline_matrix": pipeline_matrix,
        "ai_top_candidates": ai_top_candidates
    }

@router.get("/users")
async def get_all_users(
    role: Optional[str] = None,
    q: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    users_list = []
    for u in store.users.values():
        if role and role != "all" and u.get("role") != role:
            continue
        if q:
            corpus = f"{u['name']} {u['email']} {u.get('phone', '')}".lower()
            if q.lower() not in corpus:
                continue
        safe = u.copy()
        safe.pop("hashed_password", None)
        users_list.append(safe)
        
    users_list.sort(key=lambda x: x["created_at"], reverse=True)
    return users_list

@router.patch("/users/{user_id}/status")
async def toggle_user_status(user_id: str, is_active: bool, admin: dict = Depends(require_admin)):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user["is_active"] = is_active
    user["updated_at"] = datetime.now(timezone.utc)
    
    # Audit log
    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email", "admin"),
        "action": "USER_STATUS_UPDATE",
        "resource_type": "USER",
        "resource_id": user_id,
        "details": f"Set user active status to {is_active}",
        "timestamp": datetime.now(timezone.utc)
    })
    
    return {"message": f"User status updated to {'active' if is_active else 'suspended'}"}

@router.get("/jobs")
async def get_admin_jobs(
    status: Optional[str] = None,
    moderation_status: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    jobs_list = []
    for j in store.jobs.values():
        if status and status != "all" and j.get("status") != status:
            continue
        if moderation_status and moderation_status != "all" and j.get("moderation_status") != moderation_status:
            continue
        jobs_list.append(j)
        
    jobs_list.sort(key=lambda x: x["created_at"], reverse=True)
    return jobs_list

@router.patch("/jobs/{job_id}/moderation")
async def moderate_job(
    job_id: str,
    req: JobModerationUpdate,
    admin: dict = Depends(require_admin)
):
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job["moderation_status"] = req.moderation_status
    if req.rejection_reason:
        job["rejection_reason"] = req.rejection_reason
    job["updated_at"] = datetime.now(timezone.utc)

    # Audit log
    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email", "admin"),
        "action": f"JOB_MODERATION_{req.moderation_status.upper()}",
        "resource_type": "JOB",
        "resource_id": job_id,
        "details": f"Moderated job '{job['title']}' to {req.moderation_status}",
        "timestamp": datetime.now(timezone.utc)
    })

    return job

@router.post("/jobs", response_model=JobOut)
async def admin_create_job(req: JobCreate, admin: dict = Depends(require_admin)):
    admin_id = admin.get("sub")
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    
    new_job = req.model_dump()
    new_job.update({
        "id": job_id,
        "employer_id": admin_id,
        "employer_name": "Super Admin",
        "status": "active",
        "moderation_status": "approved",
        "applications_count": 0,
        "views_count": 0,
        "created_at": now,
        "updated_at": now
    })
    store.jobs[job_id] = new_job
    return new_job

@router.get("/applications")
async def get_all_applications(
    status: Optional[str] = None,
    job_id: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    apps = []
    for a in store.applications.values():
        if status and status != "all" and a.get("status") != status:
            continue
        if job_id and job_id != "all" and a.get("job_id") != job_id:
            continue
        apps.append(a)
        
    apps.sort(key=lambda x: x["created_at"], reverse=True)
    return apps

@router.get("/audit-logs", response_model=List[AuditLogOut])
async def get_audit_logs(admin: dict = Depends(require_admin)):
    logs = store.audit_logs.copy()
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs
