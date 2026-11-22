import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Desi Jobs Portal & Recruitment Platform API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Brand
    BRAND_COLOR: str = "#17324D"
    BRAND_NAME: str = "Desi Jobs"

    # Server & CORS
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    FRONTEND_URL: str = "http://localhost:3000"
    ADMIN_URL: str = "http://localhost:3001"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "https://*.vercel.app",
        "*"
    ]

    # Database (MongoDB Atlas)
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "desijobs_db"

    # Security & JWT
    SECRET_KEY: str = "desi-jobs-production-secret-jwt-auth-key-2026-very-secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Firebase Authentication
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""

    # AI Integration (Grok / xAI)
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-2-vision-1212"
    XAI_API_URL: str = "https://api.x.ai/v1/chat/completions"

    # Super Admin Defaults
    SUPER_ADMIN_NAME: str = "Super Administrator"
    SUPER_ADMIN_EMAIL: str = "admin@desijobs.com"
    SUPER_ADMIN_DEFAULT_PASSWORD: str = "Admin@DesiJobs2026!"

    # File Storage
    UPLOAD_DIR: str = os.path.join(os.getcwd(), "uploads")
    MAX_UPLOAD_SIZE_MB: int = 15

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()
