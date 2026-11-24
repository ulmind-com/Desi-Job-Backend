from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class EducationItem(BaseModel):
    institution: str
    degree: str
    department: Optional[str] = None
    graduation_year: Optional[str] = None
    grade_or_cgpa: Optional[str] = None

class ExperienceItem(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = "Present"
    is_current: bool = False
    responsibilities: List[str] = []

class ProjectItem(BaseModel):
    title: str
    description: str
    technologies: List[str] = []
    link: Optional[str] = None

class ResumeStructuredData(BaseModel):
    full_name: str
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    age: Optional[str] = None
    current_job: Optional[str] = None
    total_experience: Optional[str] = None
    raw_notes: Optional[str] = None
    professional_summary: Optional[str] = None
    education: List[EducationItem] = []
    experience: List[ExperienceItem] = []
    skills: List[str] = []
    soft_skills: List[str] = []
    certifications: List[str] = []
    projects: List[ProjectItem] = []
    languages: List[str] = []
    uncertain_fields: List[str] = []

class ResumeCreate(BaseModel):
    title: str = "My Primary Resume"
    data: ResumeStructuredData
    is_default: bool = False
    source_type: str = "manual"  # "photo_ai", "manual", "uploaded_pdf"
    source_image_url: Optional[str] = None

class ResumeOut(BaseModel):
    id: str
    user_id: str
    title: str
    data: ResumeStructuredData
    is_default: bool
    source_type: str
    source_image_url: Optional[str] = None
    pdf_download_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
