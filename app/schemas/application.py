from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class ApplicationCreate(BaseModel):
    job_id: str
    resume_id: Optional[str] = None
    full_name: str
    email: EmailStr
    phone: str
    cover_letter: Optional[str] = None
    custom_resume_data: Optional[Dict[str, Any]] = None

class ApplicationStatusUpdate(BaseModel):
    status: str  # "Applied", "Under Review", "Shortlisted", "Interview Scheduled", "Selected", "Rejected", "Withdrawn"
    employer_notes: Optional[str] = None

class ApplicationOut(BaseModel):
    id: str
    job_id: str
    job_title: str
    company_name: str
    job_location: str
    user_id: str
    full_name: str
    email: str
    phone: str
    cover_letter: Optional[str] = None
    resume_id: Optional[str] = None
    resume_snapshot: Optional[Dict[str, Any]] = None
    status: str = "Applied"
    employer_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ApplicationListResponse(BaseModel):
    items: List[ApplicationOut]
    total: int
    page: int
    limit: int
    total_pages: int
