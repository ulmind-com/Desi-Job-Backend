import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Response
from fastapi.responses import FileResponse
from app.schemas.resume import ResumeCreate, ResumeOut, ResumeStructuredData
from app.core.security import require_auth
from app.core.config import settings
from app.services.grok_service import extract_resume_from_image
from app.services.pdf_service import generate_resume_pdf
from app.services.seed_service import store

router = APIRouter(prefix="/resumes", tags=["AI Resumes"])

@router.post("/process-image")
async def process_resume_image(
    file: UploadFile = File(...),
    user: dict = Depends(require_auth)
):
    """
    Accepts JPG/PNG image of paper/handwritten resume, processes via Grok AI Vision,
    and returns editable structured resume JSON.
    """
    # Validate extension
    ext = file.filename.split(".")[-1].lower() if file.filename else "jpg"
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(status_code=400, detail="Allowed image formats: JPG, JPEG, PNG, WEBP")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB")

    # Save uploaded image locally
    photo_dir = os.path.join(settings.UPLOAD_DIR, "photos")
    os.makedirs(photo_dir, exist_ok=True)
    photo_id = f"photo_{uuid.uuid4().hex[:10]}.{ext}"
    photo_path = os.path.join(photo_dir, photo_id)
    with open(photo_path, "wb") as f:
        f.write(contents)

    # Call Grok AI / OCR extractor
    structured_data = await extract_resume_from_image(contents, file.filename or "photo.jpg")
    
    return {
        "status": "success",
        "message": "Resume extracted successfully by Grok AI. Please review and confirm your details.",
        "image_url": f"/uploads/photos/{photo_id}",
        "extracted_data": structured_data
    }

@router.post("", response_model=ResumeOut)
async def save_resume(req: ResumeCreate, user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    resume_id = f"res_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc)
    
    # Generate ATS PDF
    pdf_url = generate_resume_pdf(req.data.model_dump(), resume_id)
    
    resume_obj = {
        "id": resume_id,
        "user_id": user_id,
        "title": req.title,
        "data": req.data.model_dump(),
        "is_default": req.is_default,
        "source_type": req.source_type,
        "source_image_url": req.source_image_url,
        "pdf_download_url": pdf_url,
        "created_at": now,
        "updated_at": now
    }
    
    if req.is_default:
        for r in store.resumes.values():
            if r["user_id"] == user_id:
                r["is_default"] = False
        user_obj = store.users.get(user_id)
        if user_obj:
            user_obj["default_resume_id"] = resume_id

    store.resumes[resume_id] = resume_obj
    return resume_obj

@router.get("/my-resumes")
async def get_my_resumes(user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    resumes = [r for r in store.resumes.values() if r["user_id"] == user_id]
    resumes.sort(key=lambda x: x["created_at"], reverse=True)
    return resumes

@router.get("/{resume_id}")
async def get_resume_by_id(resume_id: str, user: dict = Depends(require_auth)):
    r = store.resumes.get(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
    return r

@router.patch("/{resume_id}/default")
async def set_default_resume(resume_id: str, user: dict = Depends(require_auth)):
    user_id = user.get("sub")
    target_res = store.resumes.get(resume_id)
    if not target_res or target_res["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Resume not found")

    for r in store.resumes.values():
        if r["user_id"] == user_id:
            r["is_default"] = (r["id"] == resume_id)

    user_obj = store.users.get(user_id)
    if user_obj:
        user_obj["default_resume_id"] = resume_id

    return {"message": "Default resume updated successfully"}

@router.get("/{resume_id}/download-pdf")
async def download_resume_pdf(resume_id: str):
    r = store.resumes.get(resume_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    pdf_filename = f"{resume_id}.pdf"
    file_path = os.path.join(settings.UPLOAD_DIR, "resumes", pdf_filename)
    if not os.path.exists(file_path):
        # Generate on the fly
        generate_resume_pdf(r["data"], resume_id)
        
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"Resume_{r['data'].get('full_name', 'Applicant').replace(' ', '_')}.pdf"
    )
