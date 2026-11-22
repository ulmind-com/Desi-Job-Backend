from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class JobBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    company: str = Field(..., min_length=2, max_length=150)
    company_logo: Optional[str] = None
    category: str
    category_id: Optional[str] = None
    description: str
    responsibilities: List[str] = []
    requirements: List[str] = []
    benefits: List[str] = []
    skills: List[str] = []
    
    # Location & Work Mode
    location: str
    country: Optional[str] = "USA"
    city: Optional[str] = "New York"
    work_mode: str = "On-site"  # "Remote", "On-site", "Hybrid"
    employment_type: str = "Full-time"  # "Full-time", "Part-time", "Contract", "Daily Wage", "Freelance"
    
    # Salary & Rate
    min_salary: float
    max_salary: float
    currency: str = "$"
    salary_period: str = "Month"  # "Hour", "Day", "Week", "Month", "Year"
    
    # Position details
    openings: int = 1
    experience_level: str = "Mid-level"  # "Entry-level", "Mid-level", "Senior", "Expert"
    min_experience_years: int = 0
    max_experience_years: int = 5
    education_required: Optional[str] = "Bachelor's Degree or Equivalent"
    
    # Contact & Application
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    deadline: Optional[datetime] = None

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    company_logo: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    currency: Optional[str] = None
    salary_period: Optional[str] = None
    openings: Optional[int] = None
    experience_level: Optional[str] = None
    status: Optional[str] = None
    moderation_status: Optional[str] = None

class JobModerationUpdate(BaseModel):
    moderation_status: str  # "approved", "rejected", "pending"
    rejection_reason: Optional[str] = None

class JobOut(JobBase):
    id: str
    employer_id: str
    employer_name: Optional[str] = None
    status: str = "active"  # "active", "paused", "closed"
    moderation_status: str = "approved"  # "approved", "pending", "rejected"
    rejection_reason: Optional[str] = None
    applications_count: int = 0
    views_count: int = 0
    created_at: datetime
    updated_at: datetime

class JobListResponse(BaseModel):
    items: List[JobOut]
    total: int
    page: int
    limit: int
    total_pages: int
