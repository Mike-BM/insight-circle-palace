import os
import uuid
import random
import string
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

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
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(letter[0]/2, letter[1]/2 + 2*inch, "Certificate of Completion")
    
    c.setFont("Helvetica", 20)
    c.drawCentredString(letter[0]/2, letter[1]/2 + 1*inch, f"This is to certify that")
    
    c.setFont("Helvetica-Bold", 25)
    c.drawCentredString(letter[0]/2, letter[1]/2, f"{user.full_name}")
    
    c.setFont("Helvetica", 20)
    c.drawCentredString(letter[0]/2, letter[1]/2 - 1*inch, f"has successfully completed the program")
    
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(letter[0]/2, letter[1]/2 - 1.5*inch, f"{program.title}")
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(letter[0]/2, letter[1]/2 - 3*inch, f"Certificate Number: {cert_number}")
    c.drawCentredString(letter[0]/2, letter[1]/2 - 3.5*inch, f"Verification Code: {verification_code}")
    
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
    
    import os
    resend_key = os.environ.get("RESEND_API_KEY")
    if resend_key:
        import resend
        resend.api_key = resend_key
        try:
            resend.Emails.send({
                "from": "Insight Circle <onboarding@resend.dev>",
                "to": user.email,
                "subject": f"Your Certificate for {program.title}",
                "html": f"<p>Congratulations {user.full_name},</p><p>You have successfully completed <strong>{program.title}</strong>.</p><p>You can view and download your certificate here: <a href='http://localhost:8000{pdf_url}'>Certificate Link</a></p><p>Your Verification Code: {verification_code}</p>"
            })
            print(f"Certificate email sent to {user.email}")
        except Exception as e:
            print(f"Failed to send certificate email: {e}")

def secrets_token_urlsafe(nbytes=None):
    import secrets
    return secrets.token_urlsafe(nbytes)
