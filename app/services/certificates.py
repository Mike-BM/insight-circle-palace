import os
import uuid
import random
import string
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

from app.models import Certificate, Enrollment, User, Program

async def generate_certificate_for_enrollment(enrollment: Enrollment, db: AsyncSession):
    # Fetch user and program
    result = await db.execute(select(User).where(User.id == enrollment.user_id))
    user = result.scalars().first()
    
    result = await db.execute(select(Program).where(Program.id == enrollment.program_id))
    program = result.scalars().first()
    
    # Generate unique codes
    cert_number = f"IC-{datetime.now(timezone.utc).year}-" + "".join(random.choices(string.digits, k=6))
    verification_code = secrets_token_urlsafe(16)
    
    # Generate PDF locally for now
    pdf_filename = f"certificate_{cert_number}.pdf"
    pdf_path = os.path.join("static", "assets", pdf_filename)
    
    c = canvas.Canvas(pdf_path, pagesize=(1280, 904))

    # Draw the background image template
    template_path = os.path.join("static", "assets", "ICP_cert.jpeg")
    c.drawImage(template_path, 0, 0, width=1280, height=904)

    # Draw a box to cover [ Recipient Name ]
    c.setFillColor(HexColor("#FDF9EE")) # approximate background color
    c.setStrokeColor(HexColor("#FDF9EE"))
    c.rect(200, 370, 880, 100, fill=1, stroke=1) # Cover name area

    # Write the name
    c.setFillColorRGB(0.1, 0.1, 0.3) # Dark blue to match template
    c.setFont("Helvetica-Bold", 60)
    c.drawCentredString(640, 400, f"{user.full_name}")

    # Cover Certificate ID
    c.setFillColor(HexColor("#FDF9EE"))
    c.rect(300, 180, 680, 40, fill=1, stroke=1)
    
    # Write Certificate ID
    c.setFillColor(HexColor("#808080")) # Grayish
    c.setFont("Helvetica", 20)
    c.drawCentredString(640, 190, f"Certificate ID: {cert_number}  •  Verify at: insightcirclepalace.com/verify")

    # Cover Date
    c.setFillColor(HexColor("#FDF9EE"))
    c.rect(900, 100, 300, 40, fill=1, stroke=1)
    
    # Write Date
    c.setFillColor(HexColor("#808080"))
    c.setFont("Helvetica", 20)
    issue_date = datetime.now(timezone.utc).strftime('%d / %m / %Y')
    c.drawString(910, 110, f"Date: {issue_date}")
    
    c.save()
    
    # Dummy object storage upload (just served from /static/assets/ for now)
    pdf_url = f"/static/assets/{pdf_filename}"
    
    cert = Certificate(
        enrollment_id=enrollment.id,
        user_id=user.id,
        program_id=program.id,
        certificate_number=cert_number,
        pdf_url=pdf_url,
        verification_code=verification_code
    )
    db.add(cert)
    await db.commit()
    
    # Send email
    print(f"Sending certificate email to {user.email} with link {pdf_url}")
    
    from app.services.email import send_email
    send_email(
        to_email=user.email,
        subject=f"Your Certificate for {program.title}",
        html_content=f"<p>Congratulations {user.full_name},</p><p>You have successfully completed <strong>{program.title}</strong>.</p><p>You can view and download your certificate here: <a href='http://localhost:8000{pdf_url}'>Certificate Link</a></p><p>Your Verification Code: {verification_code}</p>"
    )

def secrets_token_urlsafe(nbytes=None):
    import secrets
    return secrets.token_urlsafe(nbytes)
