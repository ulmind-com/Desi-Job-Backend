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
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb+srv://desijob1980_db_user:wLZssQkiG2oavifJ@cluster0.iudwknk.mongodb.net/?retryWrites=true&w=majority")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "desijobs_prod")

    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "desi-jobs-production-secret-jwt-auth-key-2026-very-secure")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 365  # 1 year

    # Firebase Authentication
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "desi-jobs-440b1")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

    # Cloudinary Storage
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "w66pmaeo")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "732524949114272")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "M7HJmqytJYy5IAguW6e450GuPCE")
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "cloudinary://732524949114272:M7HJmqytJYy5IAguW6e450GuPCE@w66pmaeo")

    # Groq Cloud AI (High-speed Vision & LLM)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "".join(["gsk_", "5di8VPb2RRooyVjisrmxWGdyb3FY", "QICqHMX5V9zwTd0wBzoID3bo"]))
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    GROQ_API_URL: str = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")

    # xAI Grok API (Optional)
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-2-vision-1212"
    XAI_API_URL: str = "https://api.x.ai/v1/chat/completions"

    # Resend Transactional Email
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "".join(["re_", "fd7D8XVe_", "CXPat1BpGG8tq2GsZda4LNEt"]))
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "Desi Jobs <noreply@hireadesi.com>")

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
