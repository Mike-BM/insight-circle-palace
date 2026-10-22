import os
import random
import string
import uuid
import secrets
from datetime import datetime, timezone

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Certificate, Enrollment, Program, User


def secrets_token_urlsafe(nbytes=None):
    return secrets.token_urlsafe(nbytes)


async def generate_certificate_for_enrollment(enrollment: Enrollment, db: AsyncSession) -> Certificate:
    """
    Generates a unique PDF certificate for a completed program enrollment.
    Verifies and prevents duplicate certificate records for the same enrollment.
    Returns the created Certificate record.
    """
    # Check if certificate already exists for this enrollment
    existing = await db.execute(select(Certificate).where(Certificate.enrollment_id == enrollment.id))
    existing_cert = existing.scalars().first()
    if existing_cert:
        return existing_cert

    # Fetch user and program
    result = await db.execute(select(User).where(User.id == enrollment.user_id))
    user = result.scalars().first()
    if not user:
        raise ValueError(f"User {enrollment.user_id} not found")

    result = await db.execute(
        select(Program).where(Program.id == enrollment.program_id)
    )
    program = result.scalars().first()
    if not program:
        raise ValueError(f"Program {enrollment.program_id} not found")

    # Generate unique codes
    cert_number = f"IC-{datetime.now(timezone.utc).year}-" + "".join(
        random.choices(string.digits, k=6)
    )
    verification_code = secrets_token_urlsafe(16)

    # Ensure output directory exists
    assets_dir = os.path.join("static", "assets")
    os.makedirs(assets_dir, exist_ok=True)

    pdf_filename = f"certificate_{cert_number}.pdf"
    pdf_path = os.path.join(assets_dir, pdf_filename)

    c = canvas.Canvas(pdf_path, pagesize=(1280, 904))
    template_path = os.path.join(assets_dir, "ICP_cert.jpeg")

    if os.path.exists(template_path):
        try:
            # Draw the background image template
            c.drawImage(template_path, 0, 0, width=1280, height=904)

            # Draw a box to cover [ Recipient Name ]
            c.setFillColor(HexColor("#FDF9EE"))
            c.setStrokeColor(HexColor("#FDF9EE"))
            c.rect(200, 370, 880, 100, fill=1, stroke=1)

            # Write the recipient name
            c.setFillColorRGB(0.1, 0.1, 0.3)
            c.setFont("Helvetica-Bold", 54)
            c.drawCentredString(640, 400, f"{user.full_name}")

            # Cover and write Certificate ID & Verification link
            c.setFillColor(HexColor("#FDF9EE"))
            c.rect(300, 180, 680, 40, fill=1, stroke=1)
            c.setFillColor(HexColor("#666666"))
            c.setFont("Helvetica", 18)
            c.drawCentredString(
                640,
                192,
                f"Certificate ID: {cert_number}  |  Verification Code: {verification_code}",
            )

            # Cover and write Date
            c.setFillColor(HexColor("#FDF9EE"))
            c.rect(880, 95, 340, 45, fill=1, stroke=1)
            c.setFillColor(HexColor("#666666"))
            c.setFont("Helvetica", 18)
            issue_date = datetime.now(timezone.utc).strftime("%d %B %Y")
            c.drawString(900, 110, f"Date: {issue_date}")

        except Exception as e:
            print(f"Warning: Failed to render image template on canvas: {e}. Falling back to programmatic layout.")
            _render_fallback_certificate(c, user.full_name, program.title, cert_number, verification_code)
    else:
        _render_fallback_certificate(c, user.full_name, program.title, cert_number, verification_code)

    c.save()

    pdf_url = f"/static/assets/{pdf_filename}"

    cert = Certificate(
        enrollment_id=enrollment.id,
        user_id=user.id,
        program_id=program.id,
        certificate_number=cert_number,
        pdf_url=pdf_url,
        verification_code=verification_code,
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)

    # Send confirmation email if service configured
    try:
        from app.services.email import send_email

        base_url = os.environ.get("BASE_URL", "https://insightcirclepalace.com").rstrip("/")
        full_pdf_url = f"{base_url}{pdf_url}"
        send_email(
            to_email=user.email,
            subject=f"Your Certificate of Completion: {program.title}",
            html_content=(
                f"<div style='font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;'>"
                f"<h2 style='color: #0b132b;'>Congratulations {user.full_name}!</h2>"
                f"<p>You have successfully fulfilled all academic curriculum requirements and passed the comprehensive assessment for <strong>{program.title}</strong>.</p>"
                f"<p><strong>Certificate ID:</strong> {cert_number}<br><strong>Verification Code:</strong> {verification_code}</p>"
                f"<p style='margin-top: 24px;'><a href='{full_pdf_url}' style='background-color: #f7a072; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;'>Download Official Certificate (PDF)</a></p>"
                f"<p style='color: #777; font-size: 12px; margin-top: 30px;'>Insight Circle Palace LMS • Official Credential</p>"
                f"</div>"
            ),
        )
    except Exception as e:
        print(f"Notice: Email notification could not be sent: {e}")

    return cert


def _render_fallback_certificate(c: canvas.Canvas, full_name: str, program_title: str, cert_number: str, verification_code: str):
    """Draws a premium styled vector certificate if the background template image is missing."""
    width, height = 1280, 904

    # Navy gradient/dark border
    c.setFillColor(HexColor("#0A1128"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Cream inner parchment
    c.setFillColor(HexColor("#FDFBF7"))
    c.rect(40, 40, width - 80, height - 80, fill=1, stroke=0)

    # Gold double border
    c.setStrokeColor(HexColor("#D4AF37"))
    c.setLineWidth(4)
    c.rect(56, 56, width - 112, height - 112, fill=0, stroke=1)
    c.setLineWidth(1)
    c.rect(64, 64, width - 128, height - 128, fill=0, stroke=1)

    # Header
    c.setFillColor(HexColor("#0A1128"))
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 150, "INSIGHT CIRCLE PALACE")

    c.setFont("Helvetica", 14)
    c.setFillColor(HexColor("#D4AF37"))
    c.drawCentredString(width / 2, height - 180, "CERTIFICATE OF ACHIEVEMENT & COMPLETION")

    c.setFont("Helvetica", 16)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 250, "This is proudly presented to")

    # Learner Name
    c.setFont("Helvetica-Bold", 46)
    c.setFillColor(HexColor("#0A1128"))
    c.drawCentredString(width / 2, height - 330, full_name)

    # Program Title
    c.setFont("Helvetica", 16)
    c.setFillColor(HexColor("#555555"))
    c.drawCentredString(width / 2, height - 400, "for successfully demonstrating mastery and completing all requirements for")

    c.setFont("Helvetica-Bold", 30)
    c.setFillColor(HexColor("#D4AF37"))
    c.drawCentredString(width / 2, height - 460, program_title)

    # Footer Metadata
    issue_date = datetime.now(timezone.utc).strftime("%d %B %Y")
    c.setFont("Helvetica", 14)
    c.setFillColor(HexColor("#666666"))
    c.drawString(100, 140, f"Issued Date: {issue_date}")
    c.drawString(100, 115, f"Certificate ID: {cert_number}")
    c.drawString(100, 90, f"Verification Code: {verification_code}")

    c.drawRightString(width - 100, 140, "Insight Circle Palace Academic Council")
    c.setStrokeColor(HexColor("#999999"))
    c.setLineWidth(1)
    c.line(width - 380, 160, width - 100, 160)
    c.drawRightString(width - 100, 115, "Authorized Signature")
