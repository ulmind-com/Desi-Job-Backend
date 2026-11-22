from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class AdminDashboardKPIs(BaseModel):
    total_users: int = 0
    total_job_seekers: int = 0
    total_employers: int = 0
    total_jobs: int = 0
    active_jobs: int = 0
    pending_jobs: int = 0
    total_applications: int = 0
    applications_today: int = 0
    total_categories: int = 0
    shortlisted_count: int = 0
    hired_count: int = 0
    rejected_count: int = 0
    cost_per_hire: float = 100.0

class RecruitmentFunnelStage(BaseModel):
    stage: str
    count: int
    conversion_rate: Optional[str] = None
    drop_off_rate: Optional[str] = None

class HiringSourceMetric(BaseModel):
    source: str
    count: int
    percentage: float
    color: str

class DepartmentMetric(BaseModel):
    department: str
    count: int
    open_positions: int

class PipelinePositionMetric(BaseModel):
    position: str
    lead: int
    applicant: int
    screening: int
    first_round: int
    second_round: int
    final_round: int
    offer: int

class AIInsightCandidate(BaseModel):
    name: str
    role: str
    conversion_likelihood: str
    confidence: float
    avatar: Optional[str] = None
    rank: int

class AuditLogOut(BaseModel):
    id: str
    admin_email: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime
