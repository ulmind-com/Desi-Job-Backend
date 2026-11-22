# Desi Jobs — Enterprise Backend API Engine

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248.svg?style=for-the-badge&logo=mongodb&logoColor=white" />
  <img src="https://img.shields.io/badge/Grok-xAI-000000.svg?style=for-the-badge&logo=x&logoColor=white" />
  <img src="https://img.shields.io/badge/Deploy-Render-46E3B7.svg?style=for-the-badge&logo=render&logoColor=white" />
</p>

Enterprise-grade asynchronous REST API powering the **Desi Jobs Portal & Recruitment Platform**. Built with FastAPI, Pydantic v2, Motor (MongoDB Async), Firebase Authentication, Grok Vision AI resume parsing, and ReportLab ATS PDF generation.

---

## 🏛️ Architectural Overview

```
                      +-----------------------------+
                      |   Client Web Applications   |
                      |  (Vercel: Frontend & Admin) |
                      +--------------+--------------+
                                     |
                                     | HTTPS / JSON
                                     v
                      +-----------------------------+
                      |   FastAPI REST Engine       |
                      |   (Render Web Service)      |
                      +--------------+--------------+
                                     |
         +---------------------------+---------------------------+
         |                           |                           |
         v                           v                           v
+-----------------+         +-----------------+         +-----------------+
|  MongoDB Atlas  |         |   Firebase SDK  |         |  xAI Grok API   |
| (Async Motor)   |         | (Token Verify)  |         | (Vision Parser) |
+-----------------+         +-----------------+         +-----------------+
```

---

## ⚡ Key Highlights & Systems

1. **Role-Based Access Control (RBAC)**:
   - `job_seeker`: Browse jobs, 1-click apply, AI photo resume extraction, track applications.
   - `employer`: Post jobs with custom salary periods (`$/Hour`, `$/Day`, `$/Month`, `$/Year`), vacancies count, review applicant pipeline, update status.
   - `admin`: Super admin dashboard with recruitment funnels, animated chart feeds, job moderation, user suspension, and password management.

2. **AI-Powered Photo Resume Extraction**:
   - Accepts photos of handwritten or printed paper resumes.
   - Processes image via xAI Grok Vision multimodal API.
   - Fallback OCR extraction engine for zero-downtime offline testing.
   - Compiles structured JSON data directly into ATS-compliant PDF resumes using ReportLab.

3. **Super Admin Security**:
   - Default credentials: `admin@desijobs.com`
   - Role-protected endpoints to update passwords, moderate listings, and inspect audit logs.

---

## 🛠️ API Reference Endpoints

All versioned endpoints are accessible under `/api/v1`:

### Authentication & Security (`/api/v1/auth`)
- `POST /auth/register` — Register seeker or employer account
- `POST /auth/login` — Email/password login with JWT token
- `POST /auth/verify` — Firebase ID token verification & auto-provisioning
- `GET /auth/me` — Current authenticated user profile
- `POST /auth/admin/login` — Super Admin login
- `POST /auth/admin/change-password` — Change Super Admin password

### Jobs Management (`/api/v1/jobs`)
- `GET /jobs` — Filtered & paginated job listings (keyword, category, country, city, work mode, salary period)
- `POST /jobs` — Create new job opening
- `GET /jobs/{job_id}` — Get job details
- `PATCH /jobs/{job_id}` — Update job opening
- `DELETE /jobs/{job_id}` — Delete job
- `GET /jobs/my/jobs` — Retrieve authenticated employer's posted jobs

### Job Applications (`/api/v1/applications`)
- `POST /applications` — Submit job application with attached resume snapshot
- `GET /applications/my-applications` — Candidate's application history
- `GET /applications/job/{job_id}` — Employer's candidate list for a specific job
- `PATCH /applications/{application_id}/status` — Update stage (`Shortlisted`, `Interview Scheduled`, `Selected`, `Rejected`)
- `POST /applications/{application_id}/withdraw` — Candidate withdraws application

### AI Resumes (`/api/v1/resumes`)
- `POST /resumes/process-image` — Upload photo of handwritten/paper resume to parse with Grok AI
- `POST /resumes` — Confirm and save structured resume
- `GET /resumes/my-resumes` — List candidate's saved resumes
- `PATCH /resumes/{resume_id}/default` — Set primary default resume
- `GET /resumes/{resume_id}/download-pdf` — Download ATS-compliant PDF

### Super Admin (`/api/v1/admin`)
- `GET /admin/dashboard` — Live recruitment funnel, KPI metrics, hiring sources, pipeline matrix
- `GET /admin/users` — User management and search
- `PATCH /admin/users/{user_id}/status` — Suspend or activate user
- `GET /admin/jobs` — Job moderation queue
- `PATCH /admin/jobs/{job_id}/moderation` — Approve or reject job post
- `GET /admin/audit-logs` — Administrative audit logs

---

## 🚀 Local Development Setup

```bash
# 1. Navigate to directory
cd Desi-Job-Backend

# 2. Run automated start script (creates venv and installs dependencies)
./start.sh
```

API Documentation will be live at:
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`
