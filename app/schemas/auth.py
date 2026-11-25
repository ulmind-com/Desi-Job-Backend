from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)
    role: str = "job_seeker"  # "job_seeker" or "employer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class FirebaseVerifyRequest(BaseModel):
    id_token: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = "job_seeker"
    avatar_url: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class AdminChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
