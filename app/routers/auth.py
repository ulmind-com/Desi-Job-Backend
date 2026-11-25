import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.auth import (
    RegisterRequest, LoginRequest, FirebaseVerifyRequest,
    TokenResponse, AdminChangePasswordRequest, AdminLoginRequest
)
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    get_current_user_payload, require_admin
)
from app.core.firebase import verify_firebase_id_token
from app.core.config import settings
from app.services.seed_service import store

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    # Check if user already exists
    for u in store.users.values():
        if u["email"].lower() == req.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists"
            )
            
    now = datetime.now(timezone.utc)
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    new_user = {
        "id": user_id,
        "name": req.name,
        "email": req.email.lower(),
        "phone": req.phone or "",
        "hashed_password": get_password_hash(req.password),
        "role": req.role if req.role in ["job_seeker", "employer"] else "job_seeker",
        "avatar_url": None,
        "location": "Not specified",
        "headline": "Job Seeker" if req.role == "job_seeker" else "Hiring Manager",
        "about": "",
        "skills": [],
        "social_links": {},
        "is_active": True,
        "is_verified": False,
        "created_at": now,
        "updated_at": now
    }
    store.users[user_id] = new_user
    store.save_state()
    
    token = create_access_token({"sub": user_id, "email": new_user["email"], "role": new_user["role"], "name": new_user["name"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": new_user["name"],
            "email": new_user["email"],
            "role": new_user["role"],
            "avatar_url": new_user["avatar_url"],
            "phone": new_user["phone"]
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = None
    for u in store.users.values():
        if u["email"].lower() == req.email.lower():
            user = u
            break
            
    if not user or not verify_password(req.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is suspended. Please contact administrator."
        )

    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"], "name": user["name"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "avatar_url": user.get("avatar_url"),
            "phone": user.get("phone")
        }
    }

@router.post("/verify", response_model=TokenResponse)
async def verify_token(req: FirebaseVerifyRequest):
    """
    Verify Firebase token or ID token, auto-provision user if new, and return API access token.
    """
    claims = await verify_firebase_id_token(req.id_token)
    email = claims.get("email") if claims else req.email
    if not email:
        raise HTTPException(status_code=400, detail="Unable to retrieve valid email from authentication token")
        
    email = str(email).lower()
    user = None
    for u in store.users.values():
        if u["email"].lower() == email:
            user = u
            break

    now = datetime.now(timezone.utc)
    if not user:
        # Create user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {
            "id": user_id,
            "name": req.name or claims.get("name") or email.split("@")[0],
            "email": email,
            "phone": req.phone or "",
            "hashed_password": "",
            "role": req.role if req.role in ["job_seeker", "employer"] else "job_seeker",
            "avatar_url": req.avatar_url or claims.get("picture"),
            "location": "Not specified",
            "headline": "Job Seeker",
            "about": "",
            "skills": [],
            "social_links": {},
            "is_active": True,
            "is_verified": True,
            "created_at": now,
            "updated_at": now
        }
        store.users[user_id] = user
        store.save_state()

    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"], "name": user["name"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "avatar_url": user.get("avatar_url")
        }
    }

@router.get("/me")
async def get_current_user_profile(payload: dict = Depends(get_current_user_payload)):
    user_id = payload.get("sub")
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    safe_user = user.copy()
    safe_user.pop("hashed_password", None)
    return safe_user

@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(req: AdminLoginRequest):
    """
    Special Super Admin Authentication.
    """
    admin_user = None
    for u in store.users.values():
        if u["email"].lower() == req.email.lower() and u.get("role") in ["admin", "super_admin"]:
            admin_user = u
            break
            
    if not admin_user or not verify_password(req.password, admin_user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Super Admin credentials"
        )
        
    token = create_access_token({
        "sub": admin_user["id"],
        "email": admin_user["email"],
        "role": "admin",
        "name": admin_user["name"]
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": admin_user["id"],
            "name": admin_user["name"],
            "email": admin_user["email"],
            "role": "admin",
            "avatar_url": admin_user.get("avatar_url")
        }
    }

@router.post("/admin/change-password")
async def change_admin_password(
    req: AdminChangePasswordRequest,
    admin_payload: dict = Depends(require_admin)
):
    """
    Allows the Super Admin to safely change their login password.
    """
    admin_id = admin_payload.get("sub")
    admin_user = store.users.get(admin_id)
    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin account not found")

    if not verify_password(req.current_password, admin_user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Current password entered is incorrect")

    admin_user["hashed_password"] = get_password_hash(req.new_password)
    admin_user["updated_at"] = datetime.now(timezone.utc)
    
    # Log the action in Audit Logs
    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin_user["email"],
        "action": "ADMIN_PASSWORD_CHANGED",
        "resource_type": "SECURITY",
        "resource_id": admin_id,
        "details": "Super Admin successfully updated their master password.",
        "timestamp": datetime.now(timezone.utc)
    })
    store.save_state()

    return {"message": "Admin password successfully updated. Please use your new password on subsequent logins."}
