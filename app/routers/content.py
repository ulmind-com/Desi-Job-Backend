"""
Site content CMS.

Every section of the public website (hero, categories, steps, footer, blog, ...)
and every admin dashboard dataset is stored as one JSON document per section.
The public site reads it, the admin panel edits it.

Persistence: MongoDB (`site_content` collection) when connected, plus a JSON file
under `<backend>/data/site_content.json` so edits survive restarts in local/dev.
Sections missing from storage fall back to `app/data/default_site_content.json`.
"""
import copy
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.database import db_manager
from app.core.security import require_admin
from app.services.seed_service import store

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_PATH = BACKEND_ROOT / "app" / "data" / "default_site_content.json"
STORE_PATH = BACKEND_ROOT / "data" / "site_content.json"
MAX_SECTION_BYTES = 256 * 1024
ADMIN_PREFIX = "admin_"

router = APIRouter(tags=["Site Content CMS"])


def _load_defaults() -> Dict[str, Any]:
    with DEFAULTS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


DEFAULTS: Dict[str, Any] = _load_defaults()


class _ContentCache:
    """In-process cache of stored overrides (section -> data) with an update stamp."""

    def __init__(self) -> None:
        self.sections: Dict[str, Any] = {}
        self.updated_at: str = datetime.now(timezone.utc).isoformat()
        self.loaded = False

    def load_file(self) -> None:
        if STORE_PATH.exists():
            try:
                raw = json.loads(STORE_PATH.read_text(encoding="utf-8"))
                self.sections = raw.get("sections", {})
                self.updated_at = raw.get("updated_at", self.updated_at)
            except Exception as e:  # corrupted file should not take the site down
                logger.error(f"Could not read {STORE_PATH}: {e}")
        self.loaded = True

    def write_file(self) -> None:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STORE_PATH.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"updated_at": self.updated_at, "sections": self.sections}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(STORE_PATH)


cache = _ContentCache()


async def _ensure_loaded() -> None:
    if cache.loaded:
        return
    cache.load_file()
    if db_manager.is_connected and db_manager.db is not None:
        try:
            async for doc in db_manager.db.site_content.find({}):
                cache.sections[doc["_id"]] = doc.get("data")
        except Exception as e:
            logger.warning(f"Could not read site_content from MongoDB: {e}")


async def _persist(section: str) -> None:
    cache.updated_at = datetime.now(timezone.utc).isoformat()
    cache.write_file()
    if db_manager.is_connected and db_manager.db is not None:
        try:
            if section in cache.sections:
                await db_manager.db.site_content.replace_one(
                    {"_id": section}, {"_id": section, "data": cache.sections[section]}, upsert=True
                )
            else:
                await db_manager.db.site_content.delete_one({"_id": section})
        except Exception as e:
            logger.warning(f"Could not write site_content to MongoDB: {e}")


def _merged(section: str) -> Any:
    if section in cache.sections:
        return cache.sections[section]
    return copy.deepcopy(DEFAULTS[section])


def _require_known(section: str) -> None:
    if section not in DEFAULTS:
        raise HTTPException(status_code=404, detail=f"Unknown content section '{section}'")


def _audit(admin: dict, action: str, section: str) -> None:
    store.audit_logs.append({
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "admin_email": admin.get("email", "admin"),
        "action": action,
        "resource_type": "CONTENT",
        "resource_id": section,
        "details": f"{action.replace('_', ' ').title()} for section '{section}'",
        "timestamp": datetime.now(timezone.utc),
    })


# ---------------------------------------------------------------- public

@router.get("/content")
async def get_public_content():
    """All public website sections (admin_* dashboards are excluded)."""
    await _ensure_loaded()
    return {
        "updated_at": cache.updated_at,
        "sections": {k: _merged(k) for k in DEFAULTS if not k.startswith(ADMIN_PREFIX)},
    }


@router.get("/content/{section}")
async def get_public_section(section: str):
    _require_known(section)
    if section.startswith(ADMIN_PREFIX):
        raise HTTPException(status_code=404, detail=f"Unknown content section '{section}'")
    await _ensure_loaded()
    return _merged(section)


# ---------------------------------------------------------------- admin

@router.get("/admin/content")
async def get_all_content(admin: dict = Depends(require_admin)):
    await _ensure_loaded()
    return {
        "updated_at": cache.updated_at,
        "sections": {k: _merged(k) for k in DEFAULTS},
        "customized": sorted(cache.sections.keys()),
    }


@router.get("/admin/content/{section}")
async def get_admin_section(section: str, admin: dict = Depends(require_admin)):
    _require_known(section)
    await _ensure_loaded()
    return _merged(section)


@router.put("/admin/content/{section}")
async def update_section(section: str, data: Any = Body(...), admin: dict = Depends(require_admin)):
    _require_known(section)
    if type(data) is not type(DEFAULTS[section]):
        raise HTTPException(status_code=422, detail=f"Section '{section}' must be a JSON {type(DEFAULTS[section]).__name__}")
    if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > MAX_SECTION_BYTES:
        raise HTTPException(status_code=413, detail="Section content is too large")
    await _ensure_loaded()
    cache.sections[section] = data
    await _persist(section)
    _audit(admin, "CONTENT_UPDATED", section)
    return {"section": section, "data": data, "updated_at": cache.updated_at}


@router.post("/admin/content/{section}/reset")
async def reset_section(section: str, admin: dict = Depends(require_admin)):
    _require_known(section)
    await _ensure_loaded()
    cache.sections.pop(section, None)
    await _persist(section)
    _audit(admin, "CONTENT_RESET", section)
    return {"section": section, "data": _merged(section), "updated_at": cache.updated_at}
