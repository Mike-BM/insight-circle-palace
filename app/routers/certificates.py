from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import Certificate, User, Program
from app.auth import get_current_user

router = APIRouter(prefix="", tags=["certificates"])

@router.get("/verify/{verification_code}")
async def verify_certificate(verification_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Certificate, User, Program)
        .join(User, Certificate.user_id == User.id)
        .join(Program, Certificate.program_id == Program.id)
        .where(Certificate.verification_code == verification_code)
    )
    data = result.first()
    if not data:
        raise HTTPException(status_code=404, detail="Certificate not found")
        
    cert, user, program = data
    return {
        "status": "valid",
        "holder_name": user.full_name,
        "program": program.title,
        "issue_date": cert.issued_at,
        "certificate_number": cert.certificate_number,
        "pdf_url": cert.pdf_url
    }

@router.get("/me/certificates")
async def my_certificates(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Certificate, Program)
        .join(Program, Certificate.program_id == Program.id)
        .where(Certificate.user_id == current_user.id)
    )
    certs = result.all()
    
    return [
        {
            "program": prog.title,
            "certificate_number": cert.certificate_number,
            "issue_date": cert.issued_at,
            "pdf_url": cert.pdf_url,
            "verification_code": cert.verification_code
        }
        for cert, prog in certs
    ]
