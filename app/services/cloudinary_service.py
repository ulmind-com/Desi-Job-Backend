import logging
from typing import Optional, Dict, Any
import cloudinary
import cloudinary.uploader
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Cloudinary if credentials are configured
if getattr(settings, "CLOUDINARY_CLOUD_NAME", None) and getattr(settings, "CLOUDINARY_API_KEY", None):
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True
    )
    logger.info("Cloudinary SDK configured successfully.")

def upload_image(file_bytes: bytes, folder: str = "desijobs", public_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Uploads an image (photo resume, avatar, company logo) to Cloudinary CDN.
    Returns dictionary with secure_url, public_id, format, etc.
    """
    if not (getattr(settings, "CLOUDINARY_CLOUD_NAME", None) and getattr(settings, "CLOUDINARY_API_KEY", None)):
        logger.warning("Cloudinary credentials not set. Skipping Cloudinary upload.")
        return None

    try:
        options = {
            "folder": folder,
            "resource_type": "auto"
        }
        if public_id:
            options["public_id"] = public_id

        result = cloudinary.uploader.upload(file_bytes, **options)
        return {
            "url": result.get("secure_url") or result.get("url"),
            "public_id": result.get("public_id"),
            "format": result.get("format"),
            "width": result.get("width"),
            "height": result.get("height"),
            "bytes": result.get("bytes")
        }
    except Exception as e:
        logger.error(f"Error uploading image to Cloudinary: {e}")
        return None
