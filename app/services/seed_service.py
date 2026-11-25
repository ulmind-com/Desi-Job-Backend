import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.security import get_password_hash
from app.core.config import settings
from app.core.database import db_manager

logger = logging.getLogger(__name__)

STORE_FILE_PATH = Path(__file__).resolve().parents[2] / "data" / "store_state.json"

DATETIME_KEYS = {"created_at", "updated_at", "timestamp", "applied_at"}


def _serialize_value(val: Any) -> Any:
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize_value(v) for v in val]
    return val


def _deserialize_value(val: Any, key: Optional[str] = None) -> Any:
    if isinstance(val, str) and key in DATETIME_KEYS:
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return val
    if isinstance(val, dict):
        return {k: _deserialize_value(v, k) for k, v in val.items()}
    if isinstance(val, list):
        return [_deserialize_value(v, key) for v in val]
    return val


def _default_visits() -> Dict[str, Any]:
    return {
        "total_visits": 0,
        "unique_visitor_ids": [],
        "daily": {},
        "recent": [],
    }


class InMemoryStore:
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.applications: Dict[str, Dict[str, Any]] = {}
        self.resumes: Dict[str, Dict[str, Any]] = {}
        self.notifications: Dict[str, Dict[str, Any]] = {}
        self.audit_logs: List[Dict[str, Any]] = []
        self.visits: Dict[str, Any] = _default_visits()
        self.initialized = False

    def export_state(self) -> Dict[str, Any]:
        return _serialize_value({
            "users": self.users,
            "categories": self.categories,
            "jobs": self.jobs,
            "applications": self.applications,
            "resumes": self.resumes,
            "notifications": self.notifications,
            "audit_logs": self.audit_logs,
            "visits": self.visits,
        })

    def import_state(self, raw: Dict[str, Any]) -> bool:
        if not isinstance(raw, dict) or not raw.get("users"):
            return False
        self.users = _deserialize_value(raw.get("users", {}))
        self.categories = _deserialize_value(raw.get("categories", {}))
        self.jobs = _deserialize_value(raw.get("jobs", {}))
        self.applications = _deserialize_value(raw.get("applications", {}))
        self.resumes = _deserialize_value(raw.get("resumes", {}))
        self.notifications = _deserialize_value(raw.get("notifications", {}))
        self.audit_logs = _deserialize_value(raw.get("audit_logs", []))
        visits = raw.get("visits") or {}
        self.visits = {
            "total_visits": int(visits.get("total_visits", 0)),
            "unique_visitor_ids": list(visits.get("unique_visitor_ids", [])),
            "daily": dict(visits.get("daily", {})),
            "recent": list(visits.get("recent", [])),
        }
        return True

    def save_state(self) -> None:
        """Persist current store state to JSON file and schedule MongoDB sync if connected."""
        payload = self.export_state()
        try:
            STORE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = STORE_FILE_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(STORE_FILE_PATH)
        except Exception as e:
            logger.warning(f"Could not write {STORE_FILE_PATH}: {e}")

        if db_manager.is_connected and db_manager.db is not None:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.save_to_mongo(payload))
            except RuntimeError:
                pass

    def load_state_from_file(self) -> bool:
        if not STORE_FILE_PATH.exists():
            return False
        try:
            raw = json.loads(STORE_FILE_PATH.read_text(encoding="utf-8"))
            return self.import_state(raw)
        except Exception as e:
            logger.warning(f"Could not read {STORE_FILE_PATH}: {e}")
            return False

    async def save_to_mongo(self, payload: Optional[Dict[str, Any]] = None) -> None:
        if not db_manager.is_connected or db_manager.db is None:
            return
        try:
            doc = payload if payload is not None else self.export_state()
            await db_manager.db.app_state.replace_one(
                {"_id": "primary"},
                {"_id": "primary", "state": doc, "updated_at": datetime.now(timezone.utc).isoformat()},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Failed saving store state to MongoDB: {e}")

    async def load_from_mongo(self) -> None:
        if not db_manager.is_connected or db_manager.db is None:
            return
        try:
            doc = await db_manager.db.app_state.find_one({"_id": "primary"})
            if doc and isinstance(doc.get("state"), dict):
                self.import_state(doc["state"])
                logger.info("Restored store state from MongoDB.")
            else:
                await self.save_to_mongo()
        except Exception as e:
            logger.warning(f"Failed loading store state from MongoDB: {e}")

    def record_visit(
        self,
        path: str = "/",
        visitor_id: Optional[str] = None,
        referrer: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        today_key = now.strftime("%Y-%m-%d")

        self.visits["total_visits"] = int(self.visits.get("total_visits", 0)) + 1
        uid = (visitor_id or "").strip()
        if uid and uid not in self.visits["unique_visitor_ids"]:
            self.visits["unique_visitor_ids"].append(uid)

        daily = self.visits.setdefault("daily", {})
        day_entry = daily.setdefault(today_key, {"visits": 0, "unique_ids": []})
        day_entry["visits"] = int(day_entry.get("visits", 0)) + 1
        if uid and uid not in day_entry["unique_ids"]:
            day_entry["unique_ids"].append(uid)

        recent = self.visits.setdefault("recent", [])
        recent.append({
            "path": (path or "/")[:200],
            "visitor_id": uid or "anonymous",
            "referrer": (referrer or "")[:200] or None,
            "timestamp": now.isoformat(),
        })
        if len(recent) > 200:
            self.visits["recent"] = recent[-200:]

        self.save_state()
        return {
            "total_visits": self.visits["total_visits"],
            "unique_visitors": len(self.visits["unique_visitor_ids"]),
            "visits_today": day_entry["visits"],
            "unique_visitors_today": len(day_entry["unique_ids"]),
        }

    def initialize_seed_data(self):
        if self.initialized:
            return

        if self.load_state_from_file():
            self.initialized = True
            return

        now = datetime.now(timezone.utc)
        
        # 1. Super Admin Account (Required for Admin Console login)
        admin_id = "user_admin_001"
        employer_id = admin_id
        self.users[admin_id] = {
            "id": admin_id,
            "name": settings.SUPER_ADMIN_NAME,
            "email": settings.SUPER_ADMIN_EMAIL,
            "phone": "+1 (555) 019-2834",
            "hashed_password": get_password_hash(settings.SUPER_ADMIN_DEFAULT_PASSWORD),
            "role": "admin",
            "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
            "location": "Global Headquarters",
            "headline": "Lead System Architect & Super Admin",
            "about": "Platform Administrator overseeing Desi Jobs recruitment pipelines, moderation, and infrastructure.",
            "skills": ["Management", "Platform Security", "Infrastructure"],
            "social_links": {},
            "is_active": True,
            "is_verified": True,
            "created_at": now - timedelta(days=30),
            "updated_at": now
        }

        # 4. Job Categories (Matching Reference Image 1 & Client Demand)
        categories_data = [
            {"name": "Hotel, Motel Front Desk Jobs", "slug": "hotel-motel-front-desk-jobs", "icon": "Hotel", "count": 28},
            {"name": "Dunkin, Tropical Drive-Thru Jobs", "slug": "dunkin-tropical-drive-thru-jobs", "icon": "Coffee", "count": 34},
            {"name": "Gas Station / Corner Store Jobs", "slug": "gas-station-corner-store-jobs", "icon": "Fuel", "count": 42},
            {"name": "Indian Cook & Kitchen Staff", "slug": "indian-cook-kitchen-staff", "icon": "CookingPot", "count": 25},
            {"name": "Warehouse & Packaging", "slug": "warehouse-packaging", "icon": "Truck", "count": 29},
            {"name": "Restaurant Server & Busser", "slug": "restaurant-server-busser", "icon": "Utensils", "count": 22},
            {"name": "Housekeeping & Hotel Cleaning", "slug": "housekeeping-hotel-cleaning", "icon": "Home", "count": 18},
            {"name": "Delivery & Truck Driver", "slug": "delivery-truck-driver", "icon": "CarTaxiFront", "count": 36},
            {"name": "Convenience Store Cashier", "slug": "convenience-store-cashier", "icon": "Store", "count": 31},
            {"name": "Handyman & Maintenance", "slug": "handyman-maintenance", "icon": "Wrench", "count": 15},
            {"name": "Automotive & Mechanic", "slug": "automotive-mechanic", "icon": "Car", "count": 14},
            {"name": "Bakery & Sweet Maker", "slug": "bakery-sweet-maker", "icon": "UtensilsCrossed", "count": 11},
            {"name": "Security Guard & Night Watch", "slug": "security-guard-night-watch", "icon": "ShieldCheck", "count": 16},
            {"name": "Salon & Beauty Services", "slug": "salon-beauty-services", "icon": "Sparkles", "count": 12},
            {"name": "Construction & General Labor", "slug": "construction-general-labor", "icon": "Hammer", "count": 20},
            {"name": "Electrician & Wireman", "slug": "electrician-wireman", "icon": "Zap", "count": 9},
            {"name": "Plumbing & Pipe Fitting", "slug": "plumbing-pipe-fitting", "icon": "Droplets", "count": 8},
            {"name": "Moving & Packing Services", "slug": "moving-packing-services", "icon": "Truck", "count": 13},
            {"name": "Laundry & Dry Cleaning", "slug": "laundry-dry-cleaning", "icon": "Shirt", "count": 10},
            {"name": "Farm & Landscaping Worker", "slug": "farm-landscaping-worker", "icon": "Leaf", "count": 9},
        ]
        
        for idx, cat in enumerate(categories_data):
            c_id = f"cat_{cat['slug']}"
            self.categories[c_id] = {
                "id": c_id,
                "name": cat["name"],
                "slug": cat["slug"],
                "icon": cat["icon"],
                "description": f"Verified open positions and providers in {cat['name']}",
                "is_active": True,
                "display_order": idx + 1,
                "jobs_count": 0,
                "created_at": now,
                "updated_at": now
            }

        # 5. Sample Jobs (Focused exclusively on blue-collar, hospitality, retail & cook roles)
        sample_jobs = [
            {
                "id": "job_001",
                "title": "Front Desk & Night Auditor",
                "company": "Comfort Inn & Suites",
                "company_logo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=100",
                "category": "Hotel, Motel Front Desk Jobs",
                "category_id": "cat_hotel-motel-front-desk-jobs",
                "description": "Seeking a responsible and polite Front Desk Associate / Night Auditor for guest check-ins, reservations management, and audit reporting.",
                "responsibilities": ["Guest check-in & check-out", "Handle phone reservations", "Perform nightly audit reconciliation"],
                "requirements": ["Basic computer knowledge", "Polite communication in English", "Night shift availability"],
                "benefits": ["Free Parking", "Overtime Pay", "Employee Room Discounts"],
                "skills": ["Front Desk", "Hotel Management", "Customer Service", "Audit"],
                "location": "Dallas, TX",
                "country": "USA",
                "city": "Dallas",
                "work_mode": "On-site",
                "employment_type": "Full-time",
                "min_salary": 18,
                "max_salary": 24,
                "currency": "$",
                "salary_period": "Hour",
                "openings": 2,
                "experience_level": "Entry-level",
                "min_experience_years": 1,
                "max_experience_years": 3,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 18,
                "views_count": 420,
                "created_at": now - timedelta(days=1),
                "updated_at": now
            },
            {
                "id": "job_002",
                "title": "Drive-Thru Server & Beverage Crew",
                "company": "Dunkin & Tropical Blend",
                "company_logo": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=100",
                "category": "Dunkin, Tropical Drive-Thru Jobs",
                "category_id": "cat_dunkin-tropical-drive-thru-jobs",
                "description": "Fast-paced drive-thru crew position preparing coffees, smoothies, and breakfast items with accuracy and high energy.",
                "responsibilities": ["Take drive-thru headset orders accurately", "Prepare beverages and hot breakfast items", "Maintain cleanliness at drive-thru window"],
                "requirements": ["Punctual and energetic", "Ability to work morning or afternoon shifts"],
                "benefits": ["Weekly Pay", "Free Meals on Shift", "Flexible Schedule"],
                "skills": ["Drive-Thru", "Cash Handling", "Customer Service", "Food Prep"],
                "location": "Orlando, FL",
                "country": "USA",
                "city": "Orlando",
                "work_mode": "On-site",
                "employment_type": "Full-time",
                "min_salary": 16,
                "max_salary": 21,
                "currency": "$",
                "salary_period": "Hour",
                "openings": 5,
                "experience_level": "Entry-level",
                "min_experience_years": 0,
                "max_experience_years": 2,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 32,
                "views_count": 510,
                "created_at": now - timedelta(days=2),
                "updated_at": now
            },
            {
                "id": "job_003",
                "title": "Gas Station Cashier & Store Associate",
                "company": "Express Mart & Fuel",
                "company_logo": "https://images.unsplash.com/photo-1527018601619-a508a2be00cd?w=100",
                "category": "Gas Station / Corner Store Jobs",
                "category_id": "cat_gas-station-corner-store-jobs",
                "description": "Looking for a trustworthy Cashier & Convenience Store Associate to oversee register sales, restock merchandise, and assist fuel customers.",
                "responsibilities": ["Operate POS register and lottery machine", "Restock drinks and snacks shelves", "Keep store premises clean and organized"],
                "requirements": ["Honest and dependable", "Basic math and register skills"],
                "benefits": ["Overtime Bonus", "Paid Break Time"],
                "skills": ["POS Register", "Inventory Restock", "Customer Care"],
                "location": "Atlanta, GA",
                "country": "USA",
                "city": "Atlanta",
                "work_mode": "On-site",
                "employment_type": "Full-time",
                "min_salary": 17,
                "max_salary": 22,
                "currency": "$",
                "salary_period": "Hour",
                "openings": 3,
                "experience_level": "Entry-level",
                "min_experience_years": 1,
                "max_experience_years": 3,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 21,
                "views_count": 390,
                "created_at": now - timedelta(days=2),
                "updated_at": now
            },
            {
                "id": "job_004",
                "title": "Head Indian Curry & Tandoor Cook",
                "company": "Royal Spice Indian Restaurant",
                "company_logo": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=100",
                "category": "Indian Cook & Kitchen Staff",
                "category_id": "cat_indian-cook-kitchen-staff",
                "description": "Authentic Indian dining establishment looking for an experienced Curry and Tandoor Cook to prepare North/South Indian gravies, biryanis, and naan breads.",
                "responsibilities": ["Prepare signature Indian curries, gravies, and tandoori breads", "Maintain strict kitchen hygiene and quality standards", "Manage pantry stock and spice proportions"],
                "requirements": ["3+ years experience with authentic Indian cooking", "Knowledge of tandoor operation and spice blending"],
                "benefits": ["Accommodation Provided", "Free Daily Meals", "Yearly Bonus"],
                "skills": ["Indian Cuisine", "Tandoor", "Curry Preparation", "Kitchen Hygiene"],
                "location": "Chicago, IL",
                "country": "USA",
                "city": "Chicago",
                "work_mode": "On-site",
                "employment_type": "Full-time",
                "min_salary": 3800,
                "max_salary": 5200,
                "currency": "$",
                "salary_period": "Month",
                "openings": 2,
                "experience_level": "Mid-level",
                "min_experience_years": 3,
                "max_experience_years": 7,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 25,
                "views_count": 540,
                "created_at": now - timedelta(days=3),
                "updated_at": now
            },
            {
                "id": "job_005",
                "title": "Motel Front Desk & Operations Associate",
                "company": "Budget Lodge & Inn",
                "company_logo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=100",
                "category": "Hotel, Motel Front Desk Jobs",
                "category_id": "cat_hotel-motel-front-desk-jobs",
                "description": "Family-managed motel seeking a polite front desk attendant. Day and evening shifts available. Friendly working environment.",
                "responsibilities": ["Welcome walk-in guests", "Manage key cards and payments", "Coordinate with housekeeping"],
                "requirements": ["Good spoken English (Hindi/Gujarati/Punjabi an asset)", "Reliable attendance"],
                "benefits": ["Housing Accommodation Available", "Weekly Paycheck"],
                "skills": ["Front Desk", "Hospitality", "Cashier"],
                "location": "Houston, TX",
                "country": "USA",
                "city": "Houston",
                "work_mode": "On-site",
                "employment_type": "Full-time",
                "min_salary": 19,
                "max_salary": 25,
                "currency": "$",
                "salary_period": "Hour",
                "openings": 2,
                "experience_level": "Entry-level",
                "min_experience_years": 1,
                "max_experience_years": 3,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 14,
                "views_count": 290,
                "created_at": now - timedelta(days=3),
                "updated_at": now
            },
            {
                "id": "job_006",
                "title": "Tropical Drive-Thru Cashier & Smoothie Maker",
                "company": "Tropical Smoothie & Cafe",
                "company_logo": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=100",
                "category": "Dunkin, Tropical Drive-Thru Jobs",
                "category_id": "cat_dunkin-tropical-drive-thru-jobs",
                "description": "Join our friendly drive-thru team making tropical fruit smoothies, wraps, and sandwiches with fast drive-thru window service.",
                "responsibilities": ["Blend smoothies according to recipes", "Handle drive-thru cash and card payments", "Keep prep stations sanitized"],
                "requirements": ["Friendly demeanor", "Quick on feet and good team player"],
                "benefits": ["Employee Discounts", "Flexible Shifts", "Tip Sharing"],
                "skills": ["Drive-Thru", "Smoothie Prep", "Customer Service"],
                "location": "Tampa, FL",
                "country": "USA",
                "city": "Tampa",
                "work_mode": "On-site",
                "employment_type": "Full-time",
                "min_salary": 16,
                "max_salary": 20,
                "currency": "$",
                "salary_period": "Hour",
                "openings": 4,
                "experience_level": "Entry-level",
                "min_experience_years": 0,
                "max_experience_years": 2,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 16,
                "views_count": 310,
                "created_at": now - timedelta(days=4),
                "updated_at": now
            },
            {
                "id": "job_007",
                "title": "Corner Store Shift Supervisor",
                "company": "Seven Star Corner Store",
                "company_logo": "https://images.unsplash.com/photo-1527018601619-a508a2be00cd?w=100",
                "category": "Gas Station / Corner Store Jobs",
                "category_id": "cat_gas-station-corner-store-jobs",
                "description": "Convenience store supervisor needed to oversee daily inventory deliveries, checkout registers, and customer satisfaction.",
                "responsibilities": ["Open or close the store", "Supervise cashier shifts", "Manage inventory receiving"],
                "requirements": ["2+ years retail or store experience", "Honest and dependable"],
                "benefits": ["Paid Sick Days", "Yearly Bonus", "Health Benefit Option"],
                "skills": ["Retail Supervision", "POS Registers", "Inventory Control"],
                "location": "Edison, NJ",
                "country": "USA",
                "city": "Edison",
                "work_mode": "On-site",
                "employment_type": "Full-time",
                "min_salary": 20,
                "max_salary": 26,
                "currency": "$",
                "salary_period": "Hour",
                "openings": 2,
                "experience_level": "Mid-level",
                "min_experience_years": 2,
                "max_experience_years": 5,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 19,
                "views_count": 400,
                "created_at": now - timedelta(days=5),
                "updated_at": now
            },
            {
                "id": "job_008",
                "title": "Indian Restaurant Assistant Cook & Naan Maker",
                "company": "Taj Curry Palace",
                "company_logo": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=100",
                "category": "Indian Cook & Kitchen Staff",
                "category_id": "cat_indian-cook-kitchen-staff",
                "description": "Busy Indian restaurant hiring an assistant cook to assist chef with tandoor breads, samosas, appetizers, and daily curry gravies.",
                "responsibilities": ["Make fresh tandoori naan and rotis", "Prep vegetables, chicken, and meats", "Assist head cook during peak dinner hours"],
                "requirements": ["1+ year experience in Indian commercial kitchen", "Hardworking and hygienic"],
                "benefits": ["Accommodation Available", "Free Meals on Shift", "Overtime Tips"],
                "skills": ["Naan Making", "Tandoor", "Food Preparation"],
                "location": "New York, NY",
                "country": "USA",
                "city": "New York",
                "work_mode": "On-site",
                "employment_type": "Full-time",
                "min_salary": 3500,
                "max_salary": 4800,
                "currency": "$",
                "salary_period": "Month",
                "openings": 3,
                "experience_level": "Entry-level",
                "min_experience_years": 1,
                "max_experience_years": 4,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 27,
                "views_count": 490,
                "created_at": now - timedelta(days=5),
                "updated_at": now
            }
        ]

        for job in sample_jobs:
            job["employer_id"] = admin_id
            job["employer_name"] = job.get("company", "Desi Jobs Official")
            job["applications_count"] = 0
            job["views_count"] = 0
            self.jobs[job["id"]] = job

        # Update category jobs_count strictly from actual jobs
        for cat_id, cat in self.categories.items():
            cat_name = cat["name"]
            cat["jobs_count"] = sum(
                1 for j in self.jobs.values()
                if (j.get("category") == cat_name or j.get("category_id") == cat_id) and j.get("status") == "active"
            )

        # No fake resumes, applications, or candidate notifications seeded!
        self.audit_logs.append({
            "id": "log_001",
            "admin_email": settings.SUPER_ADMIN_EMAIL,
            "action": "SYSTEM_INITIALIZATION",
            "resource_type": "SYSTEM",
            "resource_id": "all",
            "details": "Platform initialized with live tracking enabled and zero dummy user/applicant data.",
            "timestamp": now
        })

        self.initialized = True
        self.save_state()

store = InMemoryStore()
store.initialize_seed_data()
