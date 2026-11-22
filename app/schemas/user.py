from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "job_seeker"
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    about: Optional[str] = None
    skills: List[str] = []
    social_links: dict = {}
    is_active: bool = True
    is_verified: bool = False

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    about: Optional[str] = None
    skills: Optional[List[str]] = None
    social_links: Optional[dict] = None

class UserOut(UserBase):
    id: str
    default_resume_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class UserDashboardStats(BaseModel):
    applied_jobs_count: int = 0
    saved_jobs_count: int = 0
    posted_jobs_count: int = 0
    resumes_count: int = 0
