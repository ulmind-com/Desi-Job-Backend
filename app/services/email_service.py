import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(
    to: Union[str, List[str]],
    subject: str,
    html: str,
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a simple transactional email via Resend using noreply@hireadesi.com."""
    api_key = (settings.RESEND_API_KEY or "").strip()
    if not api_key:
        logger.warning("Resend API key is not configured; skipping email to %s", to)
        return {"sent": False, "reason": "RESEND_API_KEY missing"}

    recipients = [to] if isinstance(to, str) else [r for r in to if r]
    if not recipients:
        return {"sent": False, "reason": "No recipients provided"}

    payload: Dict[str, Any] = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            data = resp.json() if resp.content else {}
            if resp.status_code in (200, 201):
                logger.info("Resend email sent to %s (id=%s)", recipients, data.get("id"))
                return {"sent": True, "id": data.get("id"), "status_code": resp.status_code}
            logger.warning("Resend API error (%s): %s", resp.status_code, resp.text)
            return {"sent": False, "status_code": resp.status_code, "error": data or resp.text}
    except Exception as exc:
        logger.warning("Failed sending email via Resend: %s", exc)
        return {"sent": False, "error": str(exc)}


def trigger_email_background(
    to: Union[str, List[str]],
    subject: str,
    html: str,
    reply_to: Optional[str] = None,
) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_email(to=to, subject=subject, html=html, reply_to=reply_to))
    except RuntimeError:
        pass


def _simple_html(body_html: str) -> str:
    return (
        '<div style="font-family: Arial, sans-serif; color: #1f2937; font-size: 14px; line-height: 1.6;">'
        f"{body_html}"
        '<p style="margin-top: 20px; color: #6b7280; font-size: 12px;">— Desi Jobs (hireadesi.com)</p>'
        "</div>"
    )


def send_welcome_email(email: str, name: str, role: str) -> None:
    role_label = "Employer" if role == "employer" else "Job Seeker"
    html = _simple_html(
        f"""
        <p>Hi {name or 'there'},</p>
        <p>Welcome to <strong>Desi Jobs</strong>. Your {role_label} account has been created successfully.</p>
        <p>You can now sign in anytime to apply for jobs, build your resume, or manage listings.</p>
        """
    )
    trigger_email_background(email, "Welcome to Desi Jobs", html)


async def send_application_emails(
    applicant_email: str,
    applicant_name: str,
    job_title: str,
    company_name: str,
    job_location: str,
    employer_email: Optional[str] = None,
) -> None:
    tasks = []
    if applicant_email:
        candidate_html = _simple_html(
            f"""
            <p>Hi {applicant_name},</p>
            <p>Your application for <strong>{job_title}</strong> at <strong>{company_name}</strong> ({job_location}) has been received.</p>
            <p>We will notify you by email when there is an update from the hiring team.</p>
            """
        )
        tasks.append(
            send_email(
                to=applicant_email,
                subject=f"Application Received: {job_title} at {company_name}",
                html=candidate_html,
            )
        )

    if employer_email:
        employer_html = _simple_html(
            f"""
            <p>Hello,</p>
            <p><strong>{applicant_name}</strong> ({applicant_email}) applied for your job posting <strong>{job_title}</strong> ({job_location}).</p>
            <p>Sign in to Desi Jobs to view their details and resume.</p>
            """
        )
        tasks.append(
            send_email(
                to=employer_email,
                subject=f"New Application: {applicant_name} for {job_title}",
                html=employer_html,
                reply_to=applicant_email or None,
            )
        )

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def send_status_update_email(
    applicant_email: str,
    applicant_name: str,
    job_title: str,
    new_status: str,
) -> None:
    if not applicant_email:
        return
    html = _simple_html(
        f"""
        <p>Hi {applicant_name},</p>
        <p>Your application for <strong>{job_title}</strong> has been updated to: <strong>{new_status}</strong>.</p>
        <p>Check your Desi Jobs dashboard for more details.</p>
        """
    )
    await send_email(
        to=applicant_email,
        subject=f"Application Status Update: {job_title} ({new_status})",
        html=html,
    )
