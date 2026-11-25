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
    """Send a transactional email via the Resend HTTP API using noreply@hireadesi.com."""
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
    """Schedule email delivery in the background so user API responses stay fast."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_email(to=to, subject=subject, html=html, reply_to=reply_to))
    except RuntimeError:
        pass


def _wrap_brand_html(title: str, body_html: str) -> str:
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f8fafc; padding:24px;">
      <div style="max-width:560px; margin:0 auto; background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; overflow:hidden;">
        <div style="background:#17324D; padding:20px 24px; color:#ffffff;">
          <h1 style="margin:0; font-size:18px; font-weight:800; letter-spacing:-0.2px;">Desi Jobs</h1>
          <p style="margin:4px 0 0; font-size:12px; color:#cbd5e1;">{title}</p>
        </div>
        <div style="padding:24px; color:#334155; font-size:14px; line-height:1.6;">
          {body_html}
        </div>
        <div style="padding:14px 24px; background:#f8fafc; border-top:1px solid #e2e8f0; font-size:11px; color:#64748b;">
          Sent via Desi Jobs • noreply@hireadesi.com
        </div>
      </div>
    </div>
    """


def send_welcome_email(email: str, name: str, role: str) -> None:
    role_label = "Employer" if role == "employer" else "Job Seeker"
    html = _wrap_brand_html(
        "Welcome to Desi Jobs",
        f"""
        <p>Hi <strong>{name or 'there'}</strong>,</p>
        <p>Your <strong>{role_label}</strong> account on Desi Jobs is now active.</p>
        <p>You can sign in anytime to manage your profile, build or scan an AI resume, or apply and hire across the USA.</p>
        """,
    )
    trigger_email_background(email, "Welcome to Desi Jobs!", html)


def send_application_emails(
    applicant_email: str,
    applicant_name: str,
    job_title: str,
    company_name: str,
    job_location: str,
    employer_email: Optional[str] = None,
) -> None:
    if applicant_email:
        candidate_html = _wrap_brand_html(
            "Application Received",
            f"""
            <p>Hi <strong>{applicant_name}</strong>,</p>
            <p>Your application for <strong>{job_title}</strong> at <strong>{company_name}</strong> ({job_location}) has been submitted.</p>
            <p>We will notify you by email when the hiring team updates your application status.</p>
            """,
        )
        trigger_email_background(
            applicant_email,
            f"Application Submitted: {job_title} at {company_name}",
            candidate_html,
        )

    if employer_email:
        employer_html = _wrap_brand_html(
            "New Candidate Application",
            f"""
            <p>Hello,</p>
            <p><strong>{applicant_name}</strong> ({applicant_email}) just applied for your opening <strong>{job_title}</strong> in {job_location}.</p>
            <p>Log in to Desi Jobs to inspect their AI resume and update their hiring stage.</p>
            """,
        )
        trigger_email_background(
            employer_email,
            f"New Applicant: {applicant_name} for {job_title}",
            employer_html,
            reply_to=applicant_email or None,
        )


def send_status_update_email(
    applicant_email: str,
    applicant_name: str,
    job_title: str,
    new_status: str,
) -> None:
    if not applicant_email:
        return
    html = _wrap_brand_html(
        "Application Status Updated",
        f"""
        <p>Hi <strong>{applicant_name}</strong>,</p>
        <p>Your application status for <strong>{job_title}</strong> has been updated to: <strong>{new_status}</strong>.</p>
        <p>Visit your Desi Jobs dashboard for full details.</p>
        """,
    )
    trigger_email_background(
        applicant_email,
        f"Status Update ({new_status}): {job_title}",
        html,
    )
