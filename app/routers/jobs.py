import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from app.schemas.job import JobCreate, JobUpdate, JobOut, JobListResponse
from app.core.security import get_current_user_payload, require_auth
from app.services.seed_service import store
from app.routers.locations import resolve_us_state

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("", response_model=JobListResponse)
async def list_jobs(
    q: Optional[str] = None,
    category: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    work_mode: Optional[str] = None,
    employment_type: Optional[str] = None,
    salary_period: Optional[str] = None,
    min_salary: Optional[float] = None,
    experience_level: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    resolved_state = resolve_us_state(state) if (state and state.lower() != "all") else None
    results = []
    for job in store.jobs.values():
        # Only show active and approved jobs to public
        if job.get("status") != "active" or job.get("moderation_status") != "approved":
            continue
            
        if q:
            query_lower = q.lower()
            text_corpus = f"{job['title']} {job['company']} {job['description']} {job.get('location', '')} {job.get('city', '')} {' '.join(job.get('skills', []))}".lower()
            if query_lower not in text_corpus:
                continue
                
        if category and category.lower() != "all":
            if job.get("category", "").lower() != category.lower() and job.get("category_id", "").lower() != category.lower():
                continue
                
        if country and country.lower() != "all":
            if country.lower() not in job.get("country", "").lower() and country.lower() not in job.get("location", "").lower():
                continue

        if state and state.lower() != "all":
            loc_str = job.get("location", "")
            job_state = job.get("state", "")
            if resolved_state:
                code_pat = rf"\b{re.escape(resolved_state['code'])}\b"
                name_lower = resolved_state["name"].lower()
                matched = (
                    re.search(code_pat, loc_str, re.IGNORECASE) is not None
                    or name_lower in loc_str.lower()
                    or job_state.lower() in (resolved_state["code"].lower(), name_lower)
                )
            else:
                matched = state.lower() in loc_str.lower() or state.lower() == job_state.lower()
            if not matched:
                continue

        if city and city.lower() != "all":
            if city.lower() not in job.get("city", "").lower() and city.lower() not in job.get("location", "").lower():
                continue

        if work_mode and work_mode.lower() != "all":
            if job.get("work_mode", "").lower() != work_mode.lower():
                continue

        if employment_type and employment_type.lower() != "all":
            if job.get("employment_type", "").lower() != employment_type.lower():
                continue

        if salary_period and salary_period.lower() != "all":
            if job.get("salary_period", "").lower() != salary_period.lower():
                continue

        if min_salary:
            if float(job.get("max_salary", 0)) < float(min_salary):
                continue

        if experience_level and experience_level.lower() != "all":
            if job.get("experience_level", "").lower() != experience_level.lower():
                continue

        results.append(job)

    # Sort recent first
    results.sort(key=lambda x: x.get("created_at"), reverse=True)
    
    total = len(results)
    total_pages = max(1, (total + limit - 1) // limit)
    start_idx = (page - 1) * limit
    paged_items = results[start_idx:start_idx + limit]

    return {
        "items": paged_items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

@router.get("/my/jobs")
async def get_my_posted_jobs(user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    my_jobs = [j for j in store.jobs.values() if j.get("employer_id") == user_id]
    my_jobs.sort(key=lambda x: x.get("created_at"), reverse=True)
    return my_jobs

@router.get("/{job_id}", response_model=JobOut)
async def get_job_details(job_id: str):
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job position not found")
    job["views_count"] = job.get("views_count", 0) + 1
    store.save_state()
    return job

@router.post("", response_model=JobOut)
async def create_job(req: JobCreate, user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    user_data = store.users.get(user_id, {})
    
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    
    new_job = req.model_dump()
    new_job.update({
        "id": job_id,
        "employer_id": user_id,
        "employer_name": user_data.get("name", user.get("name", "Employer")),
        "status": "active",
        "moderation_status": "approved",  # auto-approved or configurable
        "applications_count": 0,
        "views_count": 0,
        "created_at": now,
        "updated_at": now
    })
    
    store.jobs[job_id] = new_job
    store.save_state()
    return new_job

@router.patch("/{job_id}")
async def update_job(job_id: str, req: JobUpdate, user: dict = Depends(require_auth)):
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    user_id = user.get("sub")
    user_role = user.get("role")
    
    if job.get("employer_id") != user_id and user_role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="You do not have permission to modify this job")

    update_fields = req.model_dump(exclude_unset=True)
    for k, v in update_fields.items():
        if v is not None:
            job[k] = v
    job["updated_at"] = datetime.now(timezone.utc)
    store.save_state()
    return job

@router.delete("/{job_id}")
async def delete_job(job_id: str, user: dict = Depends(require_auth)):
    job = store.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    user_id = user.get("sub")
    user_role = user.get("role")
    
    if job.get("employer_id") != user_id and user_role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this job")

    del store.jobs[job_id]
    store.save_state()
    return {"message": "Job deleted successfully"}
