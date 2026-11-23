import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from app.core.security import get_password_hash
from app.core.config import settings

class InMemoryStore:
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.applications: Dict[str, Dict[str, Any]] = {}
        self.resumes: Dict[str, Dict[str, Any]] = {}
        self.notifications: Dict[str, Dict[str, Any]] = {}
        self.audit_logs: List[Dict[str, Any]] = []
        self.initialized = False

    def initialize_seed_data(self):
        if self.initialized:
            return
        
        now = datetime.now(timezone.utc)
        
        # 1. Super Admin Account
        admin_id = "user_admin_001"
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
        
        # 2. Sample Employer
        employer_id = "user_emp_001"
        self.users[employer_id] = {
            "id": employer_id,
            "name": "Sarah Jenkins",
            "email": "employer@techcorp.com",
            "phone": "+1 (555) 342-8890",
            "hashed_password": get_password_hash("Employer@123"),
            "role": "employer",
            "avatar_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150",
            "location": "San Francisco, CA",
            "headline": "Head of Talent Acquisition at TechCorp",
            "about": "Hiring top engineering and design talents across the globe.",
            "skills": ["Recruitment", "Talent Sourcing"],
            "social_links": {},
            "is_active": True,
            "is_verified": True,
            "created_at": now - timedelta(days=20),
            "updated_at": now
        }

        # 3. Sample Job Seeker
        seeker_id = "user_seeker_001"
        self.users[seeker_id] = {
            "id": seeker_id,
            "name": "Alex Dom Bringer",
            "email": "alex.dom@example.com",
            "phone": "+1 (555) 789-1029",
            "hashed_password": get_password_hash("Candidate@123"),
            "role": "job_seeker",
            "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150",
            "location": "New York, NY",
            "headline": "Senior Frontend Developer (React, Next.js, TypeScript)",
            "about": "Passionate frontend engineer with 5 years of modern web development experience.",
            "skills": ["React", "Next.js", "TypeScript", "Tailwind CSS", "Redux"],
            "social_links": {"github": "https://github.com", "linkedin": "https://linkedin.com"},
            "is_active": True,
            "is_verified": True,
            "default_resume_id": "res_001",
            "created_at": now - timedelta(days=15),
            "updated_at": now
        }

        # 4. Job Categories (Matching Reference Image 1 & Client Demand)
        categories_data = [
            {"name": "Hotel, Motel Front Desk", "slug": "hotel-motel-front-desk", "icon": "Hotel", "count": 8},
            {"name": "Dunkin, Tropical Drive-thru", "slug": "dunkin-tropical-drive-thru", "icon": "Coffee", "count": 12},
            {"name": "Gas Station / Corner Store", "slug": "gas-station-corner-store", "icon": "Fuel", "count": 15},
            {"name": "Indian Cook", "slug": "indian-cook", "icon": "CookingPot", "count": 9},
            {"name": "Automotive", "slug": "automotive", "icon": "Car", "count": 4},
            {"name": "Beauty and Personal Care", "slug": "beauty-personal-care", "icon": "Sparkles", "count": 2},
            {"name": "Business", "slug": "business", "icon": "Briefcase", "count": 4},
            {"name": "Cab Service", "slug": "cab-service", "icon": "CarTaxiFront", "count": 1},
            {"name": "Cafe & Hospitality", "slug": "cafe-hospitality", "icon": "Coffee", "count": 0},
            {"name": "Car care and Servicing", "slug": "car-care-servicing", "icon": "Wrench", "count": 2},
            {"name": "Car Dealers", "slug": "car-dealers", "icon": "KeyRound", "count": 1},
            {"name": "Car Driving", "slug": "car-driving", "icon": "Compass", "count": 1},
            {"name": "Cardiologist & Healthcare", "slug": "cardiologist-healthcare", "icon": "HeartPulse", "count": 0},
            {"name": "Carpenter & Craft", "slug": "carpenter-craft", "icon": "Hammer", "count": 1},
            {"name": "Software & IT", "slug": "software-it", "icon": "Code", "count": 8},
            {"name": "Remote Jobs", "slug": "remote-jobs", "icon": "Laptop", "count": 6},
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
                "jobs_count": cat["count"],
                "created_at": now,
                "updated_at": now
            }

        # 5. Sample Jobs
        sample_jobs = [
            {
                "id": "job_001",
                "title": "Sr. Full Stack Engineer",
                "company": "TechNova Labs",
                "company_logo": "https://images.unsplash.com/photo-1549923746-c502d488b3ea?w=100",
                "category": "Software & IT",
                "category_id": "cat_software-it",
                "description": "Looking for an experienced Senior Full Stack Engineer to lead our cloud web applications using Next.js and FastAPI.",
                "responsibilities": ["Lead frontend and API development", "Optimize database performance", "Conduct code reviews"],
                "requirements": ["5+ years experience with React/Next.js and Python", "Strong architectural skills"],
                "benefits": ["Health Insurance", "Remote Stipend", "401(k) Match"],
                "skills": ["Next.js", "Python", "FastAPI", "MongoDB", "TypeScript"],
                "location": "New York, NY",
                "country": "USA",
                "city": "New York",
                "work_mode": "Remote",
                "employment_type": "Full-time",
                "min_salary": 90000,
                "max_salary": 130000,
                "currency": "$",
                "salary_period": "Year",
                "openings": 3,
                "experience_level": "Senior",
                "min_experience_years": 4,
                "max_experience_years": 8,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 14,
                "views_count": 280,
                "created_at": now - timedelta(days=5),
                "updated_at": now
            },
            {
                "id": "job_002",
                "title": "Lead UI/UX Designer",
                "company": "PixelCraft Studios",
                "company_logo": "https://images.unsplash.com/photo-1572021335469-31706a17aaef?w=100",
                "category": "Business",
                "category_id": "cat_business",
                "description": "Design sleek modern interfaces and interactive dashboards for enterprise recruitment software.",
                "responsibilities": ["Build wireframes and interactive prototypes", "Create scalable design systems in Figma"],
                "requirements": ["3+ years experience with SaaS design", "Strong portfolio"],
                "benefits": ["Flexible Working Hours", "Wellness Allowance"],
                "skills": ["Figma", "Design Systems", "Prototyping", "UI/UX"],
                "location": "San Francisco, CA",
                "country": "USA",
                "city": "San Francisco",
                "work_mode": "Hybrid",
                "employment_type": "Full-time",
                "min_salary": 250,
                "max_salary": 380,
                "currency": "$",
                "salary_period": "Day",
                "openings": 2,
                "experience_level": "Mid-level",
                "min_experience_years": 3,
                "max_experience_years": 6,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 20,
                "views_count": 410,
                "created_at": now - timedelta(days=3),
                "updated_at": now
            },
            {
                "id": "job_003",
                "title": "Automotive Technician & Diagnostician",
                "company": "Apex Auto Center",
                "company_logo": "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=100",
                "category": "Automotive",
                "category_id": "cat_automotive",
                "description": "Certified automotive technician needed for electronic vehicle diagnostics and precision maintenance.",
                "responsibilities": ["Diagnose engine and electrical systems", "Perform safety inspections and tune-ups"],
                "requirements": ["ASE Certification", "2+ years automotive repair experience"],
                "benefits": ["Tool Allowance", "Overtime Bonus"],
                "skills": ["Engine Diagnostics", "Brake Systems", "Transmission"],
                "location": "Chicago, IL",
                "country": "USA",
                "city": "Chicago",
                "work_mode": "On-site",
                "employment_type": "Daily Wage",
                "min_salary": 180,
                "max_salary": 260,
                "currency": "$",
                "salary_period": "Day",
                "openings": 2,
                "experience_level": "Mid-level",
                "min_experience_years": 2,
                "max_experience_years": 5,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 8,
                "views_count": 190,
                "created_at": now - timedelta(days=2),
                "updated_at": now
            },
            {
                "id": "job_004",
                "title": "Customer Support & Success Specialist",
                "company": "CloudDesk Solutions",
                "company_logo": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=100",
                "category": "Remote Jobs",
                "category_id": "cat_remote-jobs",
                "description": "Provide empathetic customer support, ticket resolution, and onboarding assistance for global users.",
                "responsibilities": ["Answer client inquiries via chat & email", "Document FAQs and help guides"],
                "requirements": ["Fluency in English", "Friendly problem-solving attitude"],
                "benefits": ["Paid Time Off", "Home Office Equipment"],
                "skills": ["Zendesk", "Customer Support", "Communication"],
                "location": "Austin, TX",
                "country": "USA",
                "city": "Austin",
                "work_mode": "Remote",
                "employment_type": "Full-time",
                "min_salary": 22,
                "max_salary": 32,
                "currency": "$",
                "salary_period": "Hour",
                "openings": 4,
                "experience_level": "Entry-level",
                "min_experience_years": 1,
                "max_experience_years": 3,
                "employer_id": employer_id,
                "employer_name": "Sarah Jenkins",
                "status": "active",
                "moderation_status": "approved",
                "applications_count": 35,
                "views_count": 620,
                "created_at": now - timedelta(days=1),
                "updated_at": now
            },
            {
                "id": "job_005",
                "title": "Front Desk & Night Auditor",
                "company": "Comfort Inn & Suites",
                "company_logo": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=100",
                "category": "Hotel, Motel Front Desk",
                "category_id": "cat_hotel-motel-front-desk",
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
                "applications_count": 12,
                "views_count": 310,
                "created_at": now - timedelta(days=2),
                "updated_at": now
            },
            {
                "id": "job_006",
                "title": "Drive-Thru Crew & Beverage Associate",
                "company": "Dunkin & Tropical Blend",
                "company_logo": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=100",
                "category": "Dunkin, Tropical Drive-thru",
                "category_id": "cat_dunkin-tropical-drive-thru",
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
                "max_salary": 20,
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
                "applications_count": 28,
                "views_count": 480,
                "created_at": now - timedelta(days=3),
                "updated_at": now
            },
            {
                "id": "job_007",
                "title": "Gas Station Cashier & Store Associate",
                "company": "Express Mart & Fuel",
                "company_logo": "https://images.unsplash.com/photo-1527018601619-a508a2be00cd?w=100",
                "category": "Gas Station / Corner Store",
                "category_id": "cat_gas-station-corner-store",
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
                "applications_count": 19,
                "views_count": 390,
                "created_at": now - timedelta(days=4),
                "updated_at": now
            },
            {
                "id": "job_008",
                "title": "Head Indian Curry & Tandoor Cook",
                "company": "Royal Spice Indian Restaurant",
                "company_logo": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=100",
                "category": "Indian Cook",
                "category_id": "cat_indian-cook",
                "description": "Authentic Indian dining establishment looking for an experienced Curry and Tandoor Cook to prepare North/South Indian gravies, biryanis, and naan breads.",
                "responsibilities": ["Prepare signature Indian curries, gravies, and tandoori breads", "Maintain strict kitchen hygiene and quality standards", "Manage pantry stock and spice proportions"],
                "requirements": ["3+ years experience with authentic Indian cooking", "Knowledge of tandoor operation and spice blending"],
                "benefits": ["Accommodation Allowance", "Free Meals Provided", "Yearly Bonus"],
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
                "applications_count": 22,
                "views_count": 510,
                "created_at": now - timedelta(days=4),
                "updated_at": now
            }
        ]

        for job in sample_jobs:
            self.jobs[job["id"]] = job

        # 6. Sample Resume for Seeker
        self.resumes["res_001"] = {
            "id": "res_001",
            "user_id": seeker_id,
            "title": "Primary Technical Resume",
            "data": {
                "full_name": "Alex Dom Bringer",
                "email": "alex.dom@example.com",
                "phone": "+1 (555) 789-1029",
                "location": "New York, NY",
                "professional_summary": "Seasoned Frontend Developer with extensive expertise in Next.js, TypeScript, React Hook Form, and responsive design systems.",
                "education": [
                    {
                        "institution": "Columbia University",
                        "degree": "B.S. in Computer Science",
                        "department": "Engineering & Applied Science",
                        "graduation_year": "2021",
                        "grade_or_cgpa": "3.85 GPA"
                    }
                ],
                "experience": [
                    {
                        "company": "Vanguard Web Studios",
                        "title": "Frontend Engineer",
                        "start_date": "Aug 2021",
                        "end_date": "Present",
                        "is_current": True,
                        "responsibilities": [
                            "Built high-concurrency client portal in Next.js",
                            "Reduced bundle size by 40% using code splitting"
                        ]
                    }
                ],
                "skills": ["React", "Next.js", "TypeScript", "Tailwind CSS", "Zod", "REST APIs"],
                "soft_skills": ["Team Leadership", "Agile Sprints", "Clear Documentation"],
                "certifications": ["Meta Frontend Developer Professional Certificate"],
                "projects": [
                    {
                        "title": "E-Commerce Microfrontend",
                        "description": "Modular shopping flow with 99.9% uptime and zero latency spikes.",
                        "technologies": ["React", "TypeScript", "Tailwind"],
                        "link": "https://github.com"
                    }
                ],
                "languages": ["English", "Spanish"],
                "uncertain_fields": []
            },
            "is_default": True,
            "source_type": "manual",
            "source_image_url": None,
            "pdf_download_url": "/uploads/resumes/res_001.pdf",
            "created_at": now - timedelta(days=10),
            "updated_at": now
        }

        # 7. Sample Applications for Admin Dashboard
        app_candidates = [
            ("Alex Dom Bringer", "alex.dom@example.com", "+1 555-789-1029", "Shortlisted", "job_001"),
            ("Sarah Conner", "sarah.c@example.com", "+1 555-234-5678", "Interview Scheduled", "job_001"),
            ("Marcus Vance", "marcus.v@example.com", "+1 555-345-6789", "Screening", "job_002"),
            ("Priya Patel", "priya.p@example.com", "+1 555-456-7890", "Selected", "job_001"),
            ("David Kim", "david.k@example.com", "+1 555-567-8901", "Applied", "job_003"),
            ("Elena Rostova", "elena.r@example.com", "+1 555-678-9012", "Rejected", "job_004"),
        ]

        for idx, (c_name, c_email, c_phone, status, j_id) in enumerate(app_candidates):
            app_id = f"app_00{idx + 1}"
            target_job = self.jobs.get(j_id, sample_jobs[0])
            self.applications[app_id] = {
                "id": app_id,
                "job_id": j_id,
                "job_title": target_job["title"],
                "company_name": target_job["company"],
                "job_location": target_job["location"],
                "user_id": seeker_id if idx == 0 else f"cand_00{idx+1}",
                "full_name": c_name,
                "email": c_email,
                "phone": c_phone,
                "cover_letter": "I am thrilled to apply for this position and bring my hands-on technical skills to your team.",
                "resume_id": "res_001",
                "resume_snapshot": self.resumes["res_001"]["data"],
                "status": status,
                "employer_notes": "Strong background in relevant tech stack.",
                "created_at": now - timedelta(days=idx + 1),
                "updated_at": now - timedelta(hours=idx * 2)
            }

        # 8. Notifications
        self.notifications["notif_001"] = {
            "id": "notif_001",
            "user_id": seeker_id,
            "title": "Application Status Updated",
            "message": "Your application for Sr. Full Stack Engineer at TechNova Labs has been Shortlisted!",
            "type": "status_update",
            "link": "/dashboard?tab=applications",
            "is_read": False,
            "created_at": now - timedelta(hours=3)
        }

        # 9. Audit Logs
        self.audit_logs.append({
            "id": "log_001",
            "admin_email": settings.SUPER_ADMIN_EMAIL,
            "action": "SYSTEM_INITIALIZATION",
            "resource_type": "SYSTEM",
            "resource_id": "all",
            "details": "Platform seed database initialized with core configurations and roles.",
            "timestamp": now - timedelta(days=1)
        })

        self.initialized = True

store = InMemoryStore()
store.initialize_seed_data()
