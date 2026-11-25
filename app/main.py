import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import db_manager
from app.core.firebase import init_firebase
from app.routers import (
    auth, users, jobs, applications, resumes,
    categories, admin, notifications, health, content, locations, analytics
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Desi Jobs Backend Engine...")
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "resumes"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "photos"), exist_ok=True)
    
    # Init Firebase SDK
    init_firebase()
    
    # Connect MongoDB
    await db_manager.connect()
    from app.services.seed_service import store
    await store.load_from_mongo()
    
    yield
    
    logger.info("Shutting down Desi Jobs Backend...")
    await db_manager.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-Ready Full-Stack Job Portal & Recruitment Platform REST API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads static directory
uploads_dir = settings.UPLOAD_DIR
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Health Check
app.include_router(health.router)

# Versioned API routes
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(jobs.router, prefix=api_prefix)
app.include_router(applications.router, prefix=api_prefix)
app.include_router(resumes.router, prefix=api_prefix)
app.include_router(categories.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)
app.include_router(notifications.router, prefix=api_prefix)
app.include_router(content.router, prefix=api_prefix)
app.include_router(locations.router, prefix=api_prefix)
app.include_router(analytics.router, prefix=api_prefix)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": "/health",
        "brand_color": settings.BRAND_COLOR,
        "super_admin_email": settings.SUPER_ADMIN_EMAIL
    }
