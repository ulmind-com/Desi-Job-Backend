import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.core.security import require_admin
from app.services.seed_service import store

router = APIRouter(prefix="/categories", tags=["Job Categories"])

@router.get("")
async def list_categories():
    # Update live count
    for cat_id, cat in store.categories.items():
        cat_name = cat["name"]
        live_count = sum(1 for j in store.jobs.values() if (j.get("category") == cat_name or j.get("category_id") == cat_id) and j.get("status") == "active")
        cat["jobs_count"] = live_count
    
    cats = list(store.categories.values())
    cats.sort(key=lambda x: x.get("display_order", 0))
    return cats

@router.post("")
async def create_category(req: CategoryCreate, admin: dict = Depends(require_admin)):
    cat_id = f"cat_{req.slug}"
    if cat_id in store.categories:
        raise HTTPException(status_code=400, detail="Category with this slug already exists")
        
    now = datetime.now(timezone.utc)
    new_cat = {
        "id": cat_id,
        "name": req.name,
        "slug": req.slug,
        "icon": req.icon or "Briefcase",
        "description": req.description,
        "is_active": req.is_active,
        "display_order": req.display_order,
        "jobs_count": 0,
        "created_at": now,
        "updated_at": now
    }
    store.categories[cat_id] = new_cat
    store.save_state()
    return new_cat

@router.patch("/{category_id}")
async def update_category(category_id: str, req: CategoryUpdate, admin: dict = Depends(require_admin)):
    cat = store.categories.get(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
        
    data = req.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            cat[k] = v
    cat["updated_at"] = datetime.now(timezone.utc)
    store.save_state()
    return cat

@router.delete("/{category_id}")
async def delete_category(category_id: str, admin: dict = Depends(require_admin)):
    if category_id not in store.categories:
        raise HTTPException(status_code=404, detail="Category not found")
    del store.categories[category_id]
    store.save_state()
    return {"message": "Category deleted successfully"}
