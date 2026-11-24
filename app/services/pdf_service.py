import os
import uuid
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.core.config import settings

def generate_resume_pdf(resume_data: Dict[str, Any], resume_id: str = None) -> str:
    """
    Generates a clean, ATS-compliant PDF resume from structured resume data.
    Returns relative file path of generated PDF.
    """
    if not resume_id:
        resume_id = str(uuid.uuid4())
        
    resumes_dir = os.path.join(settings.UPLOAD_DIR, "resumes")
    os.makedirs(resumes_dir, exist_ok=True)
    
    file_path = os.path.join(resumes_dir, f"{resume_id}.pdf")
    
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )
    
    brand_primary = HexColor(settings.BRAND_COLOR)  # #17324D
    text_dark = HexColor("#1F2937")
    text_muted = HexColor("#4B5563")
    
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle(
        'ResumeName',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=brand_primary,
        alignment=0,
        spaceAfter=4
    )
    
    contact_style = ParagraphStyle(
        'ResumeContact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=text_muted,
        alignment=0,
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'ResumeSectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=brand_primary,
        spaceBefore=10,
        spaceAfter=4,
        textTransform='uppercase'
    )
    
    body_bold = ParagraphStyle(
        'ResumeBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=text_dark
    )
    
    body_style = ParagraphStyle(
        'ResumeBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark
    )
    
    bullet_style = ParagraphStyle(
        'ResumeBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark,
        leftIndent=15,
        spaceAfter=2
    )
    
    story = []
    
    # 1. Header (Name & Contact)
    full_name = resume_data.get("full_name", "Applicant Name")
    story.append(Paragraph(full_name, name_style))
    
    contact_parts = []
    if resume_data.get("email"):
        contact_parts.append(resume_data["email"])
    if resume_data.get("phone"):
        contact_parts.append(resume_data["phone"])
    if resume_data.get("location"):
        contact_parts.append(resume_data["location"])
    
    story.append(Paragraph(" | ".join(contact_parts), contact_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_primary, spaceBefore=2, spaceAfter=8))

    # Candidate Bio Info
    bio_parts = []
    if resume_data.get("age"):
        bio_parts.append(f"<b>Age:</b> {resume_data['age']}")
    if resume_data.get("current_job"):
        bio_parts.append(f"<b>Job Status:</b> {resume_data['current_job']}")
    if resume_data.get("total_experience"):
        bio_parts.append(f"<b>Total Experience:</b> {resume_data['total_experience']}")

    if bio_parts:
        story.append(Paragraph(" &bull; ".join(bio_parts), body_style))
        story.append(Spacer(1, 6))
    
    # 2. Professional Summary
    summary = resume_data.get("professional_summary")
    if summary:
        story.append(Paragraph("Professional Summary", heading_style))
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 6))
    
    # 3. Work Experience
    experience = resume_data.get("experience", [])
    if experience:
        story.append(Paragraph("Experience", heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=6))
        for exp in experience:
            company = exp.get("company", "")
            title = exp.get("title", "")
            dates = f"{exp.get('start_date', '')} – {exp.get('end_date', 'Present')}"
            
            exp_header = f"<b>{title}</b> — {company} <font color='#6B7280' size='8'>({dates})</font>"
            story.append(Paragraph(exp_header, body_bold))
            
            for resp in exp.get("responsibilities", []):
                story.append(Paragraph(f"• {resp}", bullet_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 4))
    
    # 4. Education
    education = resume_data.get("education", [])
    if education:
        story.append(Paragraph("Education", heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=6))
        for edu in education:
            inst = edu.get("institution", "")
            deg = edu.get("degree", "")
            dept = f", {edu.get('department')}" if edu.get("department") else ""
            year = f" | Class of {edu.get('graduation_year')}" if edu.get("graduation_year") else ""
            grade = f" | {edu.get('grade_or_cgpa')}" if edu.get("grade_or_cgpa") else ""
            
            edu_text = f"<b>{deg}{dept}</b> — {inst} <font color='#6B7280' size='8'>({year}{grade})</font>"
            story.append(Paragraph(edu_text, body_style))
            story.append(Spacer(1, 2))
        story.append(Spacer(1, 6))
    
    # 5. Skills
    skills = resume_data.get("skills", [])
    soft_skills = resume_data.get("soft_skills", [])
    if skills or soft_skills:
        story.append(Paragraph("Skills & Competencies", heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=6))
        if skills:
            story.append(Paragraph(f"<b>Technical Skills:</b> {', '.join(skills)}", body_style))
        if soft_skills:
            story.append(Paragraph(f"<b>Core Competencies:</b> {', '.join(soft_skills)}", body_style))
        story.append(Spacer(1, 6))
        
    # 6. Certifications
    certs = resume_data.get("certifications", [])
    if certs:
        story.append(Paragraph("Certifications", heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#CBD5E1"), spaceBefore=1, spaceAfter=6))
        for cert in certs:
            story.append(Paragraph(f"• {cert}", bullet_style))
        story.append(Spacer(1, 4))
    
    doc.build(story)
    return f"/uploads/resumes/{resume_id}.pdf"
