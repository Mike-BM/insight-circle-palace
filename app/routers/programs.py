from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_db
from app.models import User, Program, Enrollment, Module, ModuleCompletion
from app.auth import get_current_user

router = APIRouter(prefix="/programs", tags=["programs"])

@router.get("/")
async def list_programs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Program).where(Program.is_active == True))
    programs = result.scalars().all()
    return [{"id": p.id, "slug": p.slug, "title": p.title, "description": p.description} for p in programs]

@router.post("/{slug}/enroll")
async def enroll_program(slug: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Program).where(Program.slug == slug))
    program = result.scalars().first()
    
    if not program or not program.is_active:
        raise HTTPException(status_code=404, detail="Program not found")
        
    result = await db.execute(
        select(Enrollment).where(Enrollment.user_id == current_user.id).where(Enrollment.program_id == program.id)
    )
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Already enrolled in this program")
        
    enrollment = Enrollment(
        user_id=current_user.id,
        program_id=program.id
    )
    db.add(enrollment)
    await db.commit()
    return {"message": "Enrolled successfully"}

@router.post("/enrollments/{enrollment_id}/modules/{module_id}/complete")
async def complete_module(
    enrollment_id: str, 
    module_id: str, 
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id).where(Enrollment.user_id == current_user.id)
    )
    enrollment = result.scalars().first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
        
    result = await db.execute(select(Module).where(Module.id == module_id).where(Module.program_id == enrollment.program_id))
    module = result.scalars().first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found in this program")
        
    result = await db.execute(
        select(ModuleCompletion).where(ModuleCompletion.enrollment_id == enrollment.id).where(ModuleCompletion.module_id == module.id)
    )
    if result.scalars().first():
        return {"message": "Module already completed"}
        
    completion = ModuleCompletion(
        enrollment_id=enrollment.id,
        module_id=module.id
    )
    db.add(completion)
    await db.commit()
    
    # Check if all modules are completed
    result = await db.execute(select(Module).where(Module.program_id == enrollment.program_id))
    all_modules = result.scalars().all()
    
    result = await db.execute(select(ModuleCompletion).where(ModuleCompletion.enrollment_id == enrollment.id))
    completed_modules = result.scalars().all()
    
    if len(all_modules) > 0 and len(completed_modules) >= len(all_modules):
        enrollment.status = "completed"
        from datetime import datetime, timezone
        enrollment.completed_at = datetime.now(timezone.utc)
        await db.commit()
        # Trigger certificate generation logic here or via background task
        from app.services.certificates import generate_certificate_for_enrollment
        await generate_certificate_for_enrollment(enrollment, db)
        
    return {"message": "Module completed successfully"}

@router.get("/me/enrollments")
async def get_my_enrollments(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Enrollment, Program)
        .join(Program, Enrollment.program_id == Program.id)
        .where(Enrollment.user_id == current_user.id)
    )
    enrollments_data = result.all()
    
    response = []
    for enr, prog in enrollments_data:
        response.append({
            "enrollment_id": enr.id,
            "program": prog.title,
            "program_slug": prog.slug,
            "status": enr.status,
            "enrolled_at": enr.enrolled_at
        })
    return response
