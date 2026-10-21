import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.models import (Certificate, Enrollment, Lesson, LessonCompletion,
                        Module, ModuleCompletion, Program, Quiz, QuizAttempt,
                        User)
from app.schemas import (CurriculumOut, LearnerProgressItem, LessonCreate,
                         LessonOut, LessonUpdate, ModuleOut, ProgramDetailOut)

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("/")
async def list_programs(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_optional_user(request, db)

    # Fetch published active programs (admins see all, learners see published)
    is_admin = bool(current_user and current_user.role in ["admin", "super_admin", "program_manager"])
    stmt = select(Program).where(Program.is_active == True)
    if not is_admin:
        stmt = stmt.where(Program.published == True)
    stmt = stmt.order_by(Program.created_at.desc())
    result = await db.execute(stmt)
    programs = result.scalars().all()

    # Pre-fetch user enrollments if logged in
    user_enrollments = {}
    if current_user:
        enr_res = await db.execute(
            select(Enrollment).where(Enrollment.user_id == current_user.id)
        )
        for enr in enr_res.scalars().all():
            user_enrollments[enr.program_id] = enr

    response = []
    for p in programs:
        # Count modules and lessons
        mod_res = await db.execute(select(Module).where(Module.program_id == p.id))
        mods = mod_res.scalars().all()
        mod_count = len(mods)

        mod_ids = [m.id for m in mods]
        lesson_count = 0
        total_duration = 0
        if mod_ids:
            less_res = await db.execute(
                select(Lesson).where(Lesson.module_id.in_(mod_ids))
            )
            lessons = less_res.scalars().all()
            lesson_count = len(lessons)
            total_duration = sum(l.duration_minutes for l in lessons)

        enr = user_enrollments.get(p.id)
        is_enrolled = enr is not None
        enr_id = str(enr.id) if enr else None
        completion_pct = 0

        if enr:
            if enr.status == "completed":
                completion_pct = 100
            elif lesson_count > 0:
                comp_res = await db.execute(
                    select(LessonCompletion).where(LessonCompletion.enrollment_id == enr.id)
                )
                completed_count = len(comp_res.scalars().all())
                completion_pct = min(100, int((completed_count / lesson_count) * 100))

        response.append({
            "id": p.id,
            "slug": p.slug,
            "title": p.title,
            "description": p.description,
            "path": p.path,
            "module_count": mod_count,
            "lesson_count": lesson_count,
            "total_duration_minutes": total_duration,
            "is_enrolled": is_enrolled,
            "enrollment_id": enr_id,
            "completion_percentage": completion_pct,
        })
    return response


@router.post("/{slug}/enroll")
async def enroll_program(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Program).where(Program.slug == slug))
    program = result.scalars().first()

    if not program or not program.is_active:
        raise HTTPException(status_code=404, detail="Program not found")

    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.user_id == current_user.id)
        .where(Enrollment.program_id == program.id)
    )
    existing_enr = result.scalars().first()
    if existing_enr:
        raise HTTPException(
            status_code=400,
            detail="Already enrolled in this program"
        )

    # Find the very first lesson if any to initialize last_accessed_lesson_id
    first_lesson_id = None
    first_mod_res = await db.execute(
        select(Module).where(Module.program_id == program.id).order_by(Module.order)
    )
    first_mod = first_mod_res.scalars().first()
    if first_mod:
        first_less_res = await db.execute(
            select(Lesson).where(Lesson.module_id == first_mod.id).order_by(Lesson.order)
        )
        first_less = first_less_res.scalars().first()
        if first_less:
            first_lesson_id = first_less.id

    enrollment = Enrollment(
        user_id=current_user.id,
        program_id=program.id,
        status="in_progress",
        last_accessed_lesson_id=first_lesson_id,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)

    return {
        "message": "Enrolled successfully",
        "status": enrollment.status,
        "enrollment_id": str(enrollment.id),
        "learn_url": f"/static/learn.html?program={slug}",
        "first_lesson_id": first_lesson_id
    }


@router.get("/{slug}/curriculum")
async def get_program_curriculum(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_optional_user(request, db)

    # Fetch Program
    prog_res = await db.execute(select(Program).where(Program.slug == slug))
    program = prog_res.scalars().first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Fetch Modules ordered
    mod_res = await db.execute(
        select(Module).where(Module.program_id == program.id).order_by(Module.order)
    )
    modules = mod_res.scalars().all()

    # Check enrollment
    enrollment = None
    if current_user:
        enr_res = await db.execute(
            select(Enrollment)
            .where(Enrollment.user_id == current_user.id)
            .where(Enrollment.program_id == program.id)
        )
        enrollment = enr_res.scalars().first()

    # Fetch completions and attempts if enrolled
    completed_lesson_ids = set()
    quiz_attempt_map = {}
    if enrollment:
        comp_res = await db.execute(
            select(LessonCompletion).where(LessonCompletion.enrollment_id == enrollment.id)
        )
        completed_lesson_ids = {c.lesson_id for c in comp_res.scalars().all()}

        att_res = await db.execute(
            select(QuizAttempt).where(QuizAttempt.enrollment_id == enrollment.id)
        )
        for att in att_res.scalars().all():
            if att.quiz_id not in quiz_attempt_map or att.attempt_number > quiz_attempt_map[att.quiz_id].attempt_number:
                quiz_attempt_map[att.quiz_id] = att

    # Check final assessment
    final_quiz_res = await db.execute(
        select(Quiz)
        .where(Quiz.program_id == program.id)
        .where(Quiz.quiz_type == "final_assessment")
    )
    final_quiz = final_quiz_res.scalars().first()

    final_assessment_passed = False
    if final_quiz and final_quiz.id in quiz_attempt_map:
        final_assessment_passed = quiz_attempt_map[final_quiz.id].passed

    # Certificate
    certificate_id = None
    certificate_number = None
    if enrollment:
        cert_res = await db.execute(
            select(Certificate).where(Certificate.enrollment_id == enrollment.id)
        )
        cert = cert_res.scalars().first()
        if cert:
            certificate_id = cert.id
            certificate_number = cert.certificate_number

    # Process modules & lessons with sequential state calculation
    all_program_lessons = []
    modules_output = []
    found_current = False

    for m in modules:
        less_res = await db.execute(
            select(Lesson).where(Lesson.module_id == m.id).order_by(Lesson.order)
        )
        lessons = less_res.scalars().all()

        lessons_out = []
        for l in lessons:
            all_program_lessons.append(l)

            # Check if lesson has a quiz
            quiz_res = await db.execute(
                select(Quiz).where(Quiz.lesson_id == l.id)
            )
            l_quiz = quiz_res.scalars().first()
            has_quiz = l_quiz is not None
            quiz_id = l_quiz.id if l_quiz else None

            # Calculate status
            if not enrollment:
                status = "LOCKED"
                content_body = None
                video_url = None
            else:
                if l.id in completed_lesson_ids:
                    status = "COMPLETED"
                elif not found_current:
                    # First non-completed lesson is CURRENT and AVAILABLE
                    status = "CURRENT"
                    found_current = True
                else:
                    status = "LOCKED"

                # If available/current/completed, show content; if locked, hide
                if status in ["COMPLETED", "CURRENT"]:
                    content_body = l.content_body
                    video_url = l.video_url
                else:
                    content_body = None
                    video_url = None

            lessons_out.append({
                "id": l.id,
                "module_id": l.module_id,
                "title": l.title,
                "order": l.order,
                "content_type": l.content_type,
                "content_body": content_body,
                "video_url": video_url,
                "duration_minutes": l.duration_minutes,
                "is_optional": l.is_optional,
                "has_quiz": has_quiz,
                "quiz_id": quiz_id,
                "status": status,
            })

        modules_output.append({
            "id": m.id,
            "program_id": m.program_id,
            "title": m.title,
            "order": m.order,
            "description": m.description,
            "lessons": lessons_out,
        })

    # Total completion percentage
    total_required = len([l for l in all_program_lessons if not l.is_optional])
    completed_required = len([l for l in all_program_lessons if l.id in completed_lesson_ids and not l.is_optional])
    completion_percentage = 0
    if total_required > 0:
        completion_percentage = min(100, int((completed_required / total_required) * 100))

    final_assessment_unlocked = (total_required > 0 and completed_required >= total_required)

    return {
        "program_id": program.id,
        "program_title": program.title,
        "program_slug": program.slug,
        "is_enrolled": enrollment is not None,
        "enrollment_id": str(enrollment.id) if enrollment else None,
        "completion_percentage": completion_percentage,
        "current_lesson_id": enrollment.last_accessed_lesson_id if enrollment else None,
        "modules": modules_output,
        "has_final_assessment": final_quiz is not None,
        "final_assessment_id": final_quiz.id if final_quiz else None,
        "final_assessment_unlocked": final_assessment_unlocked,
        "final_assessment_passed": final_assessment_passed,
        "certificate_id": certificate_id,
        "certificate_number": certificate_number,
    }


@router.post("/{slug}/lessons/{lesson_id}/complete")
async def complete_lesson(
    slug: str,
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Fetch Program
    prog_res = await db.execute(select(Program).where(Program.slug == slug))
    program = prog_res.scalars().first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Fetch Enrollment
    enr_res = await db.execute(
        select(Enrollment)
        .where(Enrollment.user_id == current_user.id)
        .where(Enrollment.program_id == program.id)
    )
    enrollment = enr_res.scalars().first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="You are not enrolled in this program")

    # Fetch Target Lesson
    less_res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    target_lesson = less_res.scalars().first()
    if not target_lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify lesson belongs to this program
    mod_res = await db.execute(select(Module).where(Module.id == target_lesson.module_id))
    target_module = mod_res.scalars().first()
    if not target_module or target_module.program_id != program.id:
        raise HTTPException(status_code=400, detail="Lesson does not belong to this program")

    # Verify all ordered prior lessons in the program are complete (Sequential Gating)
    mod_list_res = await db.execute(
        select(Module).where(Module.program_id == program.id).order_by(Module.order)
    )
    all_modules = mod_list_res.scalars().all()

    ordered_lessons = []
    for m in all_modules:
        m_less_res = await db.execute(
            select(Lesson).where(Lesson.module_id == m.id).order_by(Lesson.order)
        )
        ordered_lessons.extend(m_less_res.scalars().all())

    # Get completed IDs
    comp_res = await db.execute(
        select(LessonCompletion).where(LessonCompletion.enrollment_id == enrollment.id)
    )
    completed_ids = {c.lesson_id for c in comp_res.scalars().all()}

    # Check prerequisites: all non-optional lessons appearing before target_lesson must be completed
    for l in ordered_lessons:
        if l.id == target_lesson.id:
            break
        if not l.is_optional and l.id not in completed_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Prerequisite incomplete: You must complete '{l.title}' first."
            )

    # Check lesson quiz requirement: if lesson has a quiz, it MUST be passed!
    quiz_res = await db.execute(select(Quiz).where(Quiz.lesson_id == target_lesson.id))
    lesson_quiz = quiz_res.scalars().first()
    if lesson_quiz:
        att_res = await db.execute(
            select(QuizAttempt)
            .where(QuizAttempt.enrollment_id == enrollment.id)
            .where(QuizAttempt.quiz_id == lesson_quiz.id)
            .where(QuizAttempt.passed == True)
        )
        if not att_res.scalars().first():
            raise HTTPException(
                status_code=400,
                detail=f"Quiz required: You must pass the quiz for '{target_lesson.title}' before completing this lesson."
            )

    # Mark lesson complete if not already marked
    if target_lesson.id not in completed_ids:
        completion = LessonCompletion(
            enrollment_id=enrollment.id,
            lesson_id=target_lesson.id,
        )
        db.add(completion)
        completed_ids.add(target_lesson.id)

    # Find next lesson
    next_lesson_id = None
    found_target = False
    for l in ordered_lessons:
        if found_target:
            next_lesson_id = l.id
            break
        if l.id == target_lesson.id:
            found_target = True

    # Update enrollment pointer
    if next_lesson_id:
        enrollment.last_accessed_lesson_id = next_lesson_id
    else:
        enrollment.last_accessed_lesson_id = target_lesson.id

    await db.commit()

    total_non_optional = sum(1 for l in ordered_lessons if not l.is_optional)
    completed_non_optional = sum(1 for l in ordered_lessons if not l.is_optional and l.id in completed_ids)
    pct = round((completed_non_optional / total_non_optional) * 100) if total_non_optional > 0 else 100

    return {
        "message": "Lesson completed successfully",
        "lesson_id": target_lesson.id,
        "next_lesson_id": next_lesson_id,
        "completion_percentage": pct,
        "completed_count": completed_non_optional,
        "total_count": total_non_optional,
        "is_program_complete": next_lesson_id is None and len(completed_ids) == len(ordered_lessons)
    }


@router.get("/{slug}/resume")
async def resume_program(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prog_res = await db.execute(select(Program).where(Program.slug == slug))
    program = prog_res.scalars().first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    enr_res = await db.execute(
        select(Enrollment)
        .where(Enrollment.user_id == current_user.id)
        .where(Enrollment.program_id == program.id)
    )
    enrollment = enr_res.scalars().first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this program")

    return {
        "program_slug": slug,
        "enrollment_id": str(enrollment.id),
        "current_lesson_id": enrollment.last_accessed_lesson_id,
        "last_accessed_lesson_id": enrollment.last_accessed_lesson_id,
        "learn_url": f"/static/learn.html?program={slug}" + (
            f"&lesson={enrollment.last_accessed_lesson_id}" if enrollment.last_accessed_lesson_id else ""
        )
    }


@router.get("/me/enrollments")
async def get_my_enrollments(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Enrollment, Program)
        .join(Program, Enrollment.program_id == Program.id)
        .where(Enrollment.user_id == current_user.id)
        .order_by(Enrollment.enrolled_at.desc())
    )
    enrollments_data = result.all()

    response = []
    for enr, prog in enrollments_data:
        # Calculate real completion %
        mod_res = await db.execute(select(Module).where(Module.program_id == prog.id))
        mods = mod_res.scalars().all()
        mod_ids = [m.id for m in mods]

        total_lessons = 0
        if mod_ids:
            less_res = await db.execute(select(Lesson).where(Lesson.module_id.in_(mod_ids)))
            total_lessons = len(less_res.scalars().all())

        comp_res = await db.execute(
            select(LessonCompletion).where(LessonCompletion.enrollment_id == enr.id)
        )
        completed_lessons = len(comp_res.scalars().all())

        completion_pct = 0
        if enr.status == "completed":
            completion_pct = 100
        elif total_lessons > 0:
            completion_pct = min(100, int((completed_lessons / total_lessons) * 100))

        # Current lesson title
        current_lesson_title = None
        if enr.last_accessed_lesson_id:
            curr_l_res = await db.execute(select(Lesson).where(Lesson.id == enr.last_accessed_lesson_id))
            curr_l = curr_l_res.scalars().first()
            if curr_l:
                current_lesson_title = curr_l.title

        response.append(
            {
                "enrollment_id": str(enr.id),
                "program": prog.title,
                "program_slug": prog.slug,
                "status": enr.status,
                "enrolled_at": enr.enrolled_at.isoformat() if enr.enrolled_at else None,
                "completed_at": enr.completed_at.isoformat() if enr.completed_at else None,
                "completion_percentage": completion_pct,
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "current_lesson_id": enr.last_accessed_lesson_id,
                "current_lesson_title": current_lesson_title,
                "learn_url": f"/static/learn.html?program={prog.slug}" + (
                    f"&lesson={enr.last_accessed_lesson_id}" if enr.last_accessed_lesson_id else ""
                )
            }
        )
    return response
