import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Depends, Query
from app.core.security import require_admin
from app.services.seed_service import store
from app.services.email_service import send_email, send_status_update_email
from app.schemas.job import JobCreate, JobUpdate

router = APIRouter(prefix="/admin", tags=["Super Admin Panel"])


def _parse_dt(val) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


@router.get("/dashboard")
async def get_admin_dashboard_metrics(admin: dict = Depends(require_admin)):
    """Real-time analytics aggregated strictly from live store records (zero dummy data)."""
    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y-%m-%d")

    all_users = list(store.users.values())
    registered_users = [u for u in all_users if u.get("role") not in ["admin", "super_admin"]]
    seekers = [u for u in registered_users if u.get("role") == "job_seeker"]
    employers = [u for u in registered_users if u.get("role") == "employer"]

    all_jobs = list(store.jobs.values())
    active_jobs = [j for j in all_jobs if j.get("status") == "active" and j.get("moderation_status") == "approved"]
    pending_jobs = [j for j in all_jobs if j.get("moderation_status") == "pending"]
    closed_jobs = [j for j in all_jobs if j.get("status") != "active" or j.get("moderation_status") == "rejected"]

    all_apps = list(store.applications.values())
    applications_today = 0
    for a in all_apps:
        dt = _parse_dt(a.get("created_at"))
        if dt and dt.strftime("%Y-%m-%d") == today_key:
            applications_today += 1

    screening_cnt = sum(1 for a in all_apps if a.get("status") == "Screening")
    shortlisted_cnt = sum(1 for a in all_apps if a.get("status") == "Shortlisted")
    interview_cnt = sum(1 for a in all_apps if a.get("status") in ["Interview", "Interview Scheduled"])
    hired_cnt = sum(1 for a in all_apps if a.get("status") == "Selected")
    rejected_cnt = sum(1 for a in all_apps if a.get("status") == "Rejected")

    visits_data = store.visits or {}
    daily_visits_map = visits_data.get("daily", {})
    today_visit_entry = daily_visits_map.get(today_key, {})

    kpis = {
        "total_users": len(registered_users),
        "total_job_seekers": len(seekers),
        "total_employers": len(employers),
        "total_accounts": len(all_users),
        "total_jobs": len(all_jobs),
        "active_jobs": len(active_jobs),
        "pending_jobs": len(pending_jobs),
        "closed_jobs": len(closed_jobs),
        "total_applications": len(all_apps),
        "applications_today": applications_today,
        "screening_count": screening_cnt,
        "shortlisted_count": shortlisted_cnt + interview_cnt + hired_cnt,
        "interview_count": interview_cnt,
        "hired_count": hired_cnt,
        "rejected_count": rejected_cnt,
        "total_resumes": len(store.resumes),
        "total_visits": int(visits_data.get("total_visits", 0)),
        "unique_visitors": len(visits_data.get("unique_visitor_ids", [])),
        "visits_today": int(today_visit_entry.get("visits", 0)),
        "unique_visitors_today": len(today_visit_entry.get("unique_ids", [])),
        "total_job_views": sum(int(j.get("views_count", 0)) for j in all_jobs),
    }

    # Real recruitment funnel from actual application counts
    total_apps = len(all_apps)
    funnel = [
        {"stage": "Applied", "count": total_apps, "pct": 100 if total_apps else 0},
        {
            "stage": "Screening",
            "count": screening_cnt + shortlisted_cnt + interview_cnt + hired_cnt,
            "pct": round((screening_cnt + shortlisted_cnt + interview_cnt + hired_cnt) / total_apps * 100) if total_apps else 0,
        },
        {
            "stage": "Shortlisted",
            "count": shortlisted_cnt + interview_cnt + hired_cnt,
            "pct": round((shortlisted_cnt + interview_cnt + hired_cnt) / total_apps * 100) if total_apps else 0,
        },
        {
            "stage": "Interview",
            "count": interview_cnt + hired_cnt,
            "pct": round((interview_cnt + hired_cnt) / total_apps * 100) if total_apps else 0,
        },
        {
            "stage": "Hired",
            "count": hired_cnt,
            "pct": round(hired_cnt / total_apps * 100) if total_apps else 0,
        },
    ]

    # Real 7-day visit & application trends
    daily_visits = []
    daily_applications = []
    for offset in range(6, -1, -1):
        day_dt = now - timedelta(days=offset)
        day_str = day_dt.strftime("%Y-%m-%d")
        day_label = day_dt.strftime("%b %d")

        dv = daily_visits_map.get(day_str, {})
        daily_visits.append({
            "date": day_str,
            "label": day_label,
            "visits": int(dv.get("visits", 0)),
            "unique_visitors": len(dv.get("unique_ids", [])),
        })

        day_applied = 0
        day_shortlisted = 0
        for a in all_apps:
            dt = _parse_dt(a.get("created_at"))
            if dt and dt.strftime("%Y-%m-%d") == day_str:
                day_applied += 1
                if a.get("status") in ["Shortlisted", "Interview", "Interview Scheduled", "Selected"]:
                    day_shortlisted += 1
        daily_applications.append({
            "date": day_str,
            "label": day_label,
            "applied": day_applied,
            "shortlisted": day_shortlisted,
        })

    # Real category distribution based on actual jobs + actual applications
    cat_stats = {}
    for j in all_jobs:
        cat_name = j.get("category") or "Other"
        entry = cat_stats.setdefault(cat_name, {"name": cat_name, "jobs": 0, "applications": 0})
        if j.get("status") == "active":
            entry["jobs"] += 1
    for a in all_apps:
        job = store.jobs.get(a.get("job_id", ""), {})
        cat_name = job.get("category") or "Other"
        entry = cat_stats.setdefault(cat_name, {"name": cat_name, "jobs": 0, "applications": 0})
        entry["applications"] += 1
    categories_breakdown = sorted(
        cat_stats.values(),
        key=lambda c: (c["applications"], c["jobs"]),
        reverse=True,
    )

    # Real pipeline matrix across actual jobs
    pipeline_matrix = []
    for j in all_jobs:
        j_apps = [a for a in all_apps if a.get("job_id") == j.get("id")]
        pipeline_matrix.append({
            "id": j.get("id"),
            "role": j.get("title"),
            "company": j.get("company"),
            "location": j.get("location"),
            "category": j.get("category"),
            "employment_type": j.get("employment_type"),
            "salary": j.get("salary_display"),
            "status": j.get("status"),
            "moderation_status": j.get("moderation_status"),
            "applied": len(j_apps),
            "screening": sum(1 for a in j_apps if a.get("status") == "Screening"),
            "shortlisted": sum(1 for a in j_apps if a.get("status") == "Shortlisted"),
            "interview": sum(1 for a in j_apps if a.get("status") in ["Interview", "Interview Scheduled"]),
            "hired": sum(1 for a in j_apps if a.get("status") == "Selected"),
            "rejected": sum(1 for a in j_apps if a.get("status") == "Rejected"),
            "views": int(j.get("views_count", 0)),
        })
    pipeline_matrix.sort(key=lambda p: (p["applied"], p["views"]), reverse=True)

    # Real recent applications & recent users
    recent_apps = []
    for a in sorted(all_apps, key=lambda x: _parse_dt(x.get("created_at")) or now, reverse=True)[:15]:
        job = store.jobs.get(a.get("job_id", ""), {})
        recent_apps.append({
            "id": a.get("id"),
            "job_id": a.get("job_id"),
            "applicant_name": a.get("full_name"),
            "applicant_email": a.get("email"),
            "applicant_phone": a.get("phone"),
            "job_title": a.get("job_title") or job.get("title"),
            "company": a.get("company_name") or job.get("company"),
            "job_location": a.get("job_location") or job.get("location"),
            "employment_type": job.get("employment_type") or "Full-time",
            "status": a.get("status"),
            "cover_letter": a.get("cover_letter"),
            "resume_id": a.get("resume_id"),
            "resume_snapshot": a.get("resume_snapshot"),
            "created_at": a.get("created_at"),
        })

    recent_users = []
    for u in sorted(registered_users, key=lambda x: _parse_dt(x.get("created_at")) or now, reverse=True)[:15]:
        recent_users.append({
            "id": u.get("id"),
            "name": u.get("name"),
            "email": u.get("email"),
            "phone": u.get("phone"),
            "role": u.get("role"),
            "location": u.get("location"),
            "auth_provider": u.get("auth_provider", "email"),
            "is_active": u.get("is_active", True),
            "created_at": u.get("created_at"),
        })

    # Real activity stream constructed exclusively from real events
    activity_items = []
    for a in recent_apps[:8]:
        dt = _parse_dt(a.get("created_at")) or now
        activity_items.append({
            "type": "application",
            "text": f"{a.get('applicant_name') or 'Candidate'} applied for {a.get('job_title') or 'a job'}",
            "timestamp": dt,
        })
    for u in recent_users[:8]:
        dt = _parse_dt(u.get("created_at")) or now
        role_label = "Employer" if u.get("role") == "employer" else "Job Seeker"
        activity_items.append({
            "type": "user",
            "text": f"New {role_label} account created: {u.get('name')} ({u.get('email')})",
            "timestamp": dt,
        })
    for r in store.resumes.values():
        dt = _parse_dt(r.get("created_at")) or now
        owner = store.users.get(r.get("user_id", ""), {})
        full_name = (r.get("data") or {}).get("full_name") or owner.get("name") or "Candidate"
        activity_items.append({
            "type": "resume",
            "text": f"{full_name} saved resume: {r.get('title') or 'Resume'}",
            "timestamp": dt,
        })
    for log in store.audit_logs[-10:]:
        dt = _parse_dt(log.get("timestamp")) or now
        activity_items.append({
            "type": "admin",
            "text": log.get("details") or log.get("action"),
            "timestamp": dt,
        })

    activity_items.sort(key=lambda item: item["timestamp"], reverse=True)
    recent_activity = [
        {
            "type": item["type"],
            "text": item["text"],
            "timestamp": item["timestamp"].isoformat(),
        }
        for item in activity_items[:12]
    ]

    return {
        "kpis": kpis,
        "funnel": funnel,
        "daily_visits": daily_visits,
        "daily_applications": daily_applications,
        "categories_breakdown": categories_breakdown,
        "pipeline_matrix": pipeline_matrix,
        "recent_applications": recent_apps,
        "recent_users": recent_users,
        "recent_activity": recent_activity,
    }


@router.get("/visitors")
async def get_admin_visitors(admin: dict = Depends(require_admin)):
    """Real website visitor analytics tracked from the public frontend."""
    now = datetime.now(timezone.utc)
    today_key = now.strftime("%Y-%m-%d")
    visits_data = store.visits or {}
    daily_map = visits_data.get("daily", {})
    today_entry = daily_map.get(today_key, {})

    daily = []
    for offset in range(13, -1, -1):
        day_dt = now - timedelta(days=offset)
        day_str = day_dt.strftime("%Y-%m-%d")
        entry = daily_map.get(day_str, {})
        daily.append({
            "date": day_str,
            "label": day_dt.strftime("%b %d"),
            "visits": int(entry.get("visits", 0)),
            "unique_visitors": len(entry.get("unique_ids", [])),
        })

    recent = list(reversed(visits_data.get("recent", [])[-50:]))
    return {
        "total_visits": int(visits_data.get("total_visits", 0)),
        "unique_visitors": len(visits_data.get("unique_visitor_ids", [])),
        "visits_today": int(today_entry.get("visits", 0)),
        "unique_visitors_today": len(today_entry.get("unique_ids", [])),
        "daily": daily,
        "recent": recent,
    }


@router.get("/users")
async def get_all_users(
    role: Optional[str] = None,
    include_admins: bool = False,
    admin: dict = Depends(require_admin),
):
    now = datetime.now(timezone.utc)
    users_list = []
    for u in store.users.values():
        u_role = u.get("role")
        if not include_admins and u_role in ["admin", "super_admin"]:
            continue
        if role and role != "all" and u_role != role:
            continue
        safe = u.copy()
        safe.pop("hashed_password", None)
        safe["applications_count"] = sum(1 for a in store.applications.values() if a.get("user_id") == u.get("id"))
        safe["resumes_count"] = sum(1 for r in store.resumes.values() if r.get("user_id") == u.get("id"))
        safe["posted_jobs_count"] = sum(1 for j in store.jobs.values() if j.get("employer_id") == u.get("id"))
        users_list.append(safe)

    users_list.sort(key=lambda x: _parse_dt(x.get("created_at")) or now, reverse=True)
    return {"users": users_list, "total": len(users_list)}


@router.patch("/users/{user_id}/status")
async def update_user_status(user_id: str, is_active: bool, admin: dict = Depends(require_admin)):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["is_active"] = is_active
    user["updated_at"] = datetime.now(timezone.utc)

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "USER_STATUS_UPDATED",
        "resource_type": "USER",
        "resource_id": user_id,
        "details": f"Set user {user['email']} active status to {is_active}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()

    return {"message": "User status updated", "is_active": is_active}


@router.patch("/users/{user_id}")
async def admin_update_user(
    user_id: str,
    payload: Dict[str, Any] = Body(...),
    admin: dict = Depends(require_admin),
):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    allowed = {"name", "email", "phone", "role", "location", "headline", "is_active", "is_verified"}
    for k, v in payload.items():
        if k in allowed and v is not None:
            if k == "role" and user.get("role") in ["admin", "super_admin"]:
                continue
            user[k] = v
    user["updated_at"] = datetime.now(timezone.utc)

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "USER_UPDATED_ADMIN",
        "resource_type": "USER",
        "resource_id": user_id,
        "details": f"Updated account details for {user.get('email')}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    safe = user.copy()
    safe.pop("hashed_password", None)
    return {"message": "User updated", "user": safe}


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, admin: dict = Depends(require_admin)):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("role") in ["admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="Cannot delete Super Admin account")

    email = user.get("email", user_id)
    del store.users[user_id]
    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "USER_DELETED_ADMIN",
        "resource_type": "USER",
        "resource_id": user_id,
        "details": f"Deleted user account: {email}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    return {"message": "User deleted successfully"}


@router.get("/jobs")
async def get_all_jobs_admin(
    moderation_status: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    now = datetime.now(timezone.utc)
    jobs = list(store.jobs.values())
    if moderation_status:
        jobs = [j for j in jobs if j.get("moderation_status") == moderation_status]

    # Attach exact real application counts per job
    enriched = []
    for j in jobs:
        j_copy = j.copy()
        j_copy["applications_count"] = sum(1 for a in store.applications.values() if a.get("job_id") == j.get("id"))
        enriched.append(j_copy)

    enriched.sort(key=lambda x: _parse_dt(x.get("created_at")) or now, reverse=True)
    return {"jobs": enriched, "total": len(enriched)}


@router.patch("/jobs/{job_id}/moderation")
async def moderate_job(
    job_id: str,
    status: str = Query(..., pattern="^(approved|rejected|pending)$"),
    admin: dict = Depends(require_admin),
):
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job["moderation_status"] = status
    if status == "rejected":
        job["status"] = "closed"
    elif status == "approved":
        job["status"] = "active"
    job["updated_at"] = datetime.now(timezone.utc)

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": f"JOB_{status.upper()}",
        "resource_type": "JOB",
        "resource_id": job_id,
        "details": f"Admin {status} job posting: {job['title']} at {job['company']}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()

    return {"message": f"Job moderation status updated to {status}", "job": job}


@router.post("/jobs")
async def admin_create_job(req: JobCreate, admin: dict = Depends(require_admin)):
    """Allows Super Admin to directly create and auto-approve job postings (with AI duplicate check)."""
    from app.services.grok_service import analyze_duplicate_job

    dup = await analyze_duplicate_job(req.model_dump(), list(store.jobs.values()))
    if dup.get("is_duplicate"):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "This job has already been posted.",
                "reason": dup.get("reason"),
                "confidence": dup.get("confidence"),
                "matched_job": dup.get("matched_job"),
            },
        )

    job_id = f"job_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)

    new_job = req.model_dump()
    new_job.update({
        "id": job_id,
        "employer_id": admin.get("sub"),
        "employer_name": req.company or "Desi Jobs Official",
        "status": "active",
        "moderation_status": "approved",
        "applications_count": 0,
        "views_count": 0,
        "created_at": now,
        "updated_at": now,
    })

    store.jobs[job_id] = new_job
    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "JOB_CREATED_ADMIN",
        "resource_type": "JOB",
        "resource_id": job_id,
        "details": f"Super Admin posted new job: {new_job['title']}",
        "timestamp": now,
    })
    store.save_state()
    return new_job


@router.patch("/jobs/{job_id}")
async def admin_update_job(
    job_id: str,
    req: JobUpdate,
    admin: dict = Depends(require_admin),
):
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_fields = req.model_dump(exclude_unset=True)
    for k, v in update_fields.items():
        if v is not None:
            job[k] = v
    job["updated_at"] = datetime.now(timezone.utc)

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "JOB_UPDATED_ADMIN",
        "resource_type": "JOB",
        "resource_id": job_id,
        "details": f"Updated job: {job.get('title')} at {job.get('company')}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    return {"message": "Job updated", "job": job}


@router.delete("/jobs/{job_id}")
async def admin_delete_job(job_id: str, admin: dict = Depends(require_admin)):
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    title = job.get("title", job_id)
    del store.jobs[job_id]
    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "JOB_DELETED_ADMIN",
        "resource_type": "JOB",
        "resource_id": job_id,
        "details": f"Deleted job listing: {title}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    return {"message": "Job deleted successfully"}


@router.get("/applications")
async def get_all_applications_admin(admin: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    apps = list(store.applications.values())
    apps.sort(key=lambda x: _parse_dt(x.get("created_at")) or now, reverse=True)

    enriched = []
    for a in apps:
        job = store.jobs.get(a.get("job_id", ""), {})
        enriched.append({
            "id": a.get("id"),
            "job_id": a.get("job_id"),
            "user_id": a.get("user_id"),
            "applicant_name": a.get("full_name"),
            "applicant_email": a.get("email"),
            "applicant_phone": a.get("phone"),
            "job_title": a.get("job_title") or job.get("title"),
            "company": a.get("company_name") or job.get("company"),
            "job_location": a.get("job_location") or job.get("location"),
            "employment_type": job.get("employment_type") or "Full-time",
            "status": a.get("status"),
            "cover_letter": a.get("cover_letter"),
            "resume_id": a.get("resume_id"),
            "resume_snapshot": a.get("resume_snapshot"),
            "employer_notes": a.get("employer_notes"),
            "created_at": a.get("created_at"),
            "updated_at": a.get("updated_at"),
        })
    return {"applications": enriched, "total": len(enriched)}


@router.patch("/applications/{application_id}/status")
async def admin_update_application_status(
    application_id: str,
    status: str = Query(...),
    notes: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    app = store.applications.get(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    old_status = app.get("status")
    app["status"] = status
    if notes is not None:
        app["employer_notes"] = notes
    app["updated_at"] = datetime.now(timezone.utc)

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "APPLICATION_STATUS_UPDATED",
        "resource_type": "APPLICATION",
        "resource_id": application_id,
        "details": f"Changed {app.get('full_name')}'s status from {old_status} to {status}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    if app.get("status") != old_status:
        send_status_update_email(
            applicant_email=app.get("email", ""),
            applicant_name=app.get("full_name", "Candidate"),
            job_title=app.get("job_title", "Position"),
            new_status=status,
        )
    return {"message": "Application status updated", "application": app}


@router.patch("/applications/{application_id}")
async def admin_update_application(
    application_id: str,
    payload: Dict[str, Any] = Body(...),
    admin: dict = Depends(require_admin),
):
    app = store.applications.get(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    for k in ["full_name", "email", "phone", "status", "cover_letter", "employer_notes"]:
        if k in payload and payload[k] is not None:
            app[k] = payload[k]
    app["updated_at"] = datetime.now(timezone.utc)

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "APPLICATION_UPDATED_ADMIN",
        "resource_type": "APPLICATION",
        "resource_id": application_id,
        "details": f"Edited application for {app.get('full_name')}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    return {"message": "Application updated", "application": app}


@router.delete("/applications/{application_id}")
async def admin_delete_application(application_id: str, admin: dict = Depends(require_admin)):
    app = store.applications.get(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    applicant_name = app.get("full_name", application_id)
    job = store.jobs.get(app.get("job_id", ""))
    if job and int(job.get("applications_count", 0)) > 0:
        job["applications_count"] = int(job.get("applications_count", 0)) - 1
    del store.applications[application_id]

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "APPLICATION_DELETED_ADMIN",
        "resource_type": "APPLICATION",
        "resource_id": application_id,
        "details": f"Deleted application from {applicant_name}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    return {"message": "Application deleted successfully"}


@router.get("/resumes")
async def get_all_resumes_admin(admin: dict = Depends(require_admin)):
    """Returns all real saved resumes (from Resume Builder / profile + any unlinked application resume snapshots)."""
    now = datetime.now(timezone.utc)
    items = []
    seen_ids = set()

    for r in store.resumes.values():
        seen_ids.add(r.get("id"))
        owner = store.users.get(r.get("user_id", ""), {})
        r_data = r.get("data") or {}
        r_copy = r.copy()
        r_copy["owner_name"] = owner.get("name") or r_data.get("full_name") or "Candidate"
        r_copy["owner_email"] = owner.get("email") or r_data.get("email") or ""
        r_copy["owner_avatar"] = owner.get("avatar_url") or r_data.get("photo_url")
        r_copy["location"] = r_data.get("location") or owner.get("location") or "USA"
        items.append(r_copy)

    # Also surface any application resume snapshots not yet stored in store.resumes
    for a in store.applications.values():
        snap = a.get("resume_snapshot")
        rid = a.get("resume_id")
        if snap and (not rid or rid not in seen_ids):
            owner = store.users.get(a.get("user_id", ""), {})
            synth_id = rid or f"app_snap_{a.get('id')}"
            if synth_id in seen_ids:
                continue
            seen_ids.add(synth_id)
            items.append({
                "id": synth_id,
                "user_id": a.get("user_id"),
                "title": f"{a.get('full_name') or 'Candidate'} — {a.get('job_title') or 'Application'}",
                "data": snap,
                "is_default": False,
                "source_type": "application",
                "owner_name": owner.get("name") or a.get("full_name") or "Candidate",
                "owner_email": owner.get("email") or a.get("email") or "",
                "owner_avatar": owner.get("avatar_url") or (snap.get("photo_url") if isinstance(snap, dict) else None),
                "location": (snap.get("location") if isinstance(snap, dict) else None) or a.get("job_location") or owner.get("location") or "USA",
                "created_at": a.get("created_at"),
                "updated_at": a.get("updated_at"),
            })

    items.sort(key=lambda x: _parse_dt(x.get("created_at")) or now, reverse=True)
    return {"resumes": items, "total": len(items)}


@router.patch("/resumes/{resume_id}")
async def admin_update_resume(
    resume_id: str,
    payload: Dict[str, Any] = Body(...),
    admin: dict = Depends(require_admin),
):
    r = store.resumes.get(resume_id)
    if not r and resume_id.startswith("app_snap_"):
        app_id = resume_id.replace("app_snap_", "", 1)
        app = store.applications.get(app_id)
        if app and isinstance(app.get("resume_snapshot"), dict):
            snap = app["resume_snapshot"]
            for field in ["full_name", "email", "phone", "location", "headline", "professional_summary", "skills"]:
                if field in payload and payload[field] is not None:
                    snap[field] = payload[field]
            app["updated_at"] = datetime.now(timezone.utc)
            store.save_state()
            return {"message": "Resume snapshot updated", "resume": {"id": resume_id, "title": payload.get("title") or app.get("job_title"), "data": snap}}
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")

    if "title" in payload and payload["title"] is not None:
        r["title"] = payload["title"]
    if "source_type" in payload and payload["source_type"] is not None:
        r["source_type"] = payload["source_type"]
    data = r.setdefault("data", {})
    for field in ["full_name", "email", "phone", "location", "headline", "professional_summary", "skills"]:
        if field in payload and payload[field] is not None:
            data[field] = payload[field]
    r["updated_at"] = datetime.now(timezone.utc)

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "RESUME_UPDATED_ADMIN",
        "resource_type": "RESUME",
        "resource_id": resume_id,
        "details": f"Updated resume: {r.get('title')}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    return {"message": "Resume updated", "resume": r}


@router.delete("/resumes/{resume_id}")
async def admin_delete_resume(resume_id: str, admin: dict = Depends(require_admin)):
    r = store.resumes.get(resume_id)
    if not r and resume_id.startswith("app_snap_"):
        app_id = resume_id.replace("app_snap_", "", 1)
        app = store.applications.get(app_id)
        if app and app.get("resume_snapshot") is not None:
            app["resume_snapshot"] = None
            app["updated_at"] = datetime.now(timezone.utc)
            store.save_state()
            return {"message": "Application resume snapshot deleted successfully"}
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")

    title = r.get("title", resume_id)
    del store.resumes[resume_id]
    for u in store.users.values():
        if u.get("default_resume_id") == resume_id:
            u["default_resume_id"] = None

    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email"),
        "action": "RESUME_DELETED_ADMIN",
        "resource_type": "RESUME",
        "resource_id": resume_id,
        "details": f"Deleted resume: {title}",
        "timestamp": datetime.now(timezone.utc),
    })
    store.save_state()
    return {"message": "Resume deleted successfully"}


@router.post("/test-email")
async def admin_send_test_email(
    payload: Dict[str, Any] = Body(...),
    admin: dict = Depends(require_admin),
):
    to_email = str(payload.get("to") or "").strip()
    if not to_email:
        raise HTTPException(status_code=400, detail="Recipient email 'to' is required")
    subject = str(payload.get("subject") or "Desi Jobs Email Delivery Test")
    html = str(payload.get("html") or "<p>Hello from Desi Jobs (noreply@hireadesi.com) via Resend!</p>")
    result = await send_email(to=to_email, subject=subject, html=html)
    if not result.get("sent"):
        raise HTTPException(status_code=502, detail=result)
    return result


@router.get("/audit-logs")
async def get_audit_logs(admin: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    logs = store.audit_logs.copy()
    logs.sort(key=lambda x: _parse_dt(x.get("timestamp")) or now, reverse=True)
    return {"logs": logs, "total": len(logs)}
