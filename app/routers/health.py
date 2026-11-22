from fastapi import APIRouter
from app.core.config import settings
from app.core.database import db_manager

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database_connected": db_manager.is_connected,
        "brand_color": settings.BRAND_COLOR,
        "environment": settings.ENVIRONMENT
    }
