import logging
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Assignment,
    AssignmentSubmission,
    Enrollment,
    Module,
    Program,
    User,
    utcnow,
)
from app.schemas import (
    AssignmentOut,
    AssignmentSubmissionOut,
    AssignmentSubmitRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("")
@router.get("/")
async def assignments_root(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        return FileResponse("static/assignments.html", media_type="text/html")
    return await get_my_assignments(None, None, current_user, db)


@router.get("/me")
async def get_my_assignments(
    program_slug: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all assignments relevant to the authenticated user, including their submission status and stats.
    """
    # Find user enrollments
    enrollment_stmt = (
        select(Enrollment)
        .options(selectinload(Enrollment.program))
        .where(Enrollment.user_id == current_user.id)
    )
    if program_slug:
        enrollment_stmt = enrollment_stmt.join(Program).where(Program.slug == program_slug)

    res_enrollments = await db.execute(enrollment_stmt)
    enrollments = res_enrollments.scalars().all()
    enrolled_program_ids = [e.program_id for e in enrollments]

    # Query assignments for enrolled programs, or all active programs if user has no enrollments yet
    query = (
        select(Assignment)
        .options(
            selectinload(Assignment.program),
            selectinload(Assignment.module),
            selectinload(Assignment.submissions),
        )
        .join(Program)
        .where(Program.is_active == True, Program.published == True)
        .order_by(Assignment.program_id, Assignment.order)
    )

    if enrolled_program_ids:
        # Prioritize assignments from programs the user is enrolled in
        query = query.where(Assignment.program_id.in_(enrolled_program_ids))
    elif program_slug:
        query = query.where(Program.slug == program_slug)

    res_assignments = await db.execute(query)
    assignments = res_assignments.scalars().all()

    # If no assignments found for enrolled programs, fallback to all active programs
    if not assignments and not program_slug:
        fallback_query = (
            select(Assignment)
            .options(
                selectinload(Assignment.program),
                selectinload(Assignment.module),
                selectinload(Assignment.submissions),
            )
            .join(Program)
            .where(Program.is_active == True, Program.published == True)
            .order_by(Assignment.order)
        )
        res_fb = await db.execute(fallback_query)
        assignments = res_fb.scalars().all()

    # Build response list with user-specific submission status
    items = []
    total = len(assignments)
    pending_count = 0
    submitted_count = 0
    graded_count = 0

    for a in assignments:
        # Check user submission
        user_sub = None
        for s in a.submissions:
            if s.user_id == current_user.id:
                user_sub = s
                break

        if user_sub:
            if user_sub.status == "graded" or user_sub.grade is not None:
                item_status = "graded"
                graded_count += 1
            else:
                item_status = "submitted"
                submitted_count += 1
        else:
            item_status = "pending"
            pending_count += 1

        if status_filter and status_filter.lower() != "all" and item_status != status_filter.lower():
            continue

        sub_out = None
        if user_sub:
            sub_out = AssignmentSubmissionOut(
                id=user_sub.id,
                assignment_id=user_sub.assignment_id,
                user_id=user_sub.user_id,
                submission_text=user_sub.submission_text,
                submission_link=user_sub.submission_link,
                submission_file_url=user_sub.submission_file_url,
                status=user_sub.status,
                grade=user_sub.grade,
                feedback=user_sub.feedback,
                submitted_at=user_sub.submitted_at,
                graded_at=user_sub.graded_at,
            )

        items.append(
            AssignmentOut(
                id=a.id,
                program_id=a.program_id,
                program_slug=a.program.slug if a.program else None,
                program_title=a.program.title if a.program else None,
                module_id=a.module_id,
                module_title=a.module.title if a.module else None,
                lesson_id=a.lesson_id,
                title=a.title,
                description=a.description,
                instructions=a.instructions,
                rubric=a.rubric,
                submission_type=a.submission_type,
                max_points=a.max_points,
                due_days=a.due_days,
                order=a.order,
                created_at=a.created_at,
                status=item_status,
                submission=sub_out,
            )
        )

    return {
        "stats": {
            "total": total,
            "pending": pending_count,
            "submitted": submitted_count,
            "graded": graded_count,
        },
        "assignments": items,
    }


@router.get("/{assignment_id}")
async def get_assignment_detail(
    assignment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed assignment info, instructions, rubric, and user submission.
    """
    stmt = (
        select(Assignment)
        .options(
            selectinload(Assignment.program),
            selectinload(Assignment.module),
            selectinload(Assignment.lesson),
            selectinload(Assignment.submissions),
        )
        .where(Assignment.id == assignment_id)
    )
    res = await db.execute(stmt)
    assignment = res.scalar_one_or_none()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    # Check user submission
    user_sub = None
    for s in assignment.submissions:
        if s.user_id == current_user.id:
            user_sub = s
            break

    if user_sub:
        item_status = "graded" if (user_sub.status == "graded" or user_sub.grade is not None) else "submitted"
    else:
        item_status = "pending"

    sub_out = None
    if user_sub:
        sub_out = AssignmentSubmissionOut(
            id=user_sub.id,
            assignment_id=user_sub.assignment_id,
            user_id=user_sub.user_id,
            submission_text=user_sub.submission_text,
            submission_link=user_sub.submission_link,
            submission_file_url=user_sub.submission_file_url,
            status=user_sub.status,
            grade=user_sub.grade,
            feedback=user_sub.feedback,
            submitted_at=user_sub.submitted_at,
            graded_at=user_sub.graded_at,
        )

    return {
        "assignment": AssignmentOut(
            id=assignment.id,
            program_id=assignment.program_id,
            program_slug=assignment.program.slug if assignment.program else None,
            program_title=assignment.program.title if assignment.program else None,
            module_id=assignment.module_id,
            module_title=assignment.module.title if assignment.module else None,
            lesson_id=assignment.lesson_id,
            title=assignment.title,
            description=assignment.description,
            instructions=assignment.instructions,
            rubric=assignment.rubric,
            submission_type=assignment.submission_type,
            max_points=assignment.max_points,
            due_days=assignment.due_days,
            order=assignment.order,
            created_at=assignment.created_at,
            status=item_status,
            submission=sub_out,
        )
    }


@router.post("/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: str,
    payload: AssignmentSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit an assignment response (text, link, or uploaded file).
    """
    text_content = (payload.submission_text or "").strip()
    link_content = (payload.submission_link or "").strip()
    file_content = (payload.submission_file_url or "").strip()

    if not text_content and not link_content and not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission must include at least one of: written text response, external resource link, or uploaded document.",
        )

    if text_content and len(text_content) < 10 and not link_content and not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Written submission must be at least 10 characters long.",
        )

    # Fetch assignment
    res_a = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = res_a.scalar_one_or_none()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )

    # Verify or create enrollment
    res_enr = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.program_id == assignment.program_id,
        )
    )
    enrollment = res_enr.scalar_one_or_none()
    if not enrollment:
        enrollment = Enrollment(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            program_id=assignment.program_id,
            status="in_progress",
        )
        db.add(enrollment)
        await db.flush()

    # Check for existing submission
    res_sub = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.user_id == current_user.id,
        )
    )
    existing_sub = res_sub.scalar_one_or_none()

    now = utcnow()
    if existing_sub:
        existing_sub.submission_text = text_content or existing_sub.submission_text
        existing_sub.submission_link = link_content or existing_sub.submission_link
        existing_sub.submission_file_url = file_content or existing_sub.submission_file_url
        existing_sub.status = "resubmitted" if existing_sub.status == "graded" else "submitted"
        existing_sub.submitted_at = now
        submission = existing_sub
    else:
        submission = AssignmentSubmission(
            id=str(uuid.uuid4()),
            assignment_id=assignment_id,
            enrollment_id=enrollment.id,
            user_id=current_user.id,
            submission_text=text_content or None,
            submission_link=link_content or None,
            submission_file_url=file_content or None,
            status="submitted",
            submitted_at=now,
        )
        db.add(submission)

    await db.commit()
    await db.refresh(submission)

    return {
        "success": True,
        "message": "Assignment submitted successfully!",
        "submission": AssignmentSubmissionOut(
            id=submission.id,
            assignment_id=submission.assignment_id,
            user_id=submission.user_id,
            submission_text=submission.submission_text,
            submission_link=submission.submission_link,
            submission_file_url=submission.submission_file_url,
            status=submission.status,
            grade=submission.grade,
            feedback=submission.feedback,
            submitted_at=submission.submitted_at,
            graded_at=submission.graded_at,
        ),
    }


@router.post("/upload")
async def upload_assignment_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an assignment attachment (PDF, DOCX, ZIP, PNG, JPG).
    """
    allowed_exts = {".pdf", ".docx", ".doc", ".txt", ".zip", ".png", ".jpg", ".jpeg"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{ext}'. Allowed types: PDF, DOCX, DOC, TXT, ZIP, PNG, JPG.",
        )

    # 15MB limit check
    contents = await file.read()
    if len(contents) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 15MB limit.",
        )

    upload_dir = os.path.join("static", "uploads", "assignments")
    os.makedirs(upload_dir, exist_ok=True)

    safe_filename = f"{uuid.uuid4().hex[:12]}_{os.path.basename(file.filename or 'file')}"
    file_path = os.path.join(upload_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/assignments/{safe_filename}"
    return {
        "success": True,
        "file_url": file_url,
        "filename": file.filename,
    }


@router.post("/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: str,
    grade: int = Query(..., ge=0, le=100),
    feedback: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Instructor/admin grading endpoint.
    """
    valid_roles = ["admin", "super_admin", "editor", "moderator"]
    if current_user.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and instructors can grade submissions.",
        )

    res_sub = await db.execute(
        select(AssignmentSubmission).where(AssignmentSubmission.id == submission_id)
    )
    sub = res_sub.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    sub.grade = grade
    sub.feedback = feedback
    sub.status = "graded"
    sub.graded_at = utcnow()
    sub.graded_by = current_user.id

    await db.commit()
    await db.refresh(sub)

    return {
        "success": True,
        "message": f"Submission graded successfully ({grade}/100)",
        "submission": AssignmentSubmissionOut(
            id=sub.id,
            assignment_id=sub.assignment_id,
            user_id=sub.user_id,
            submission_text=sub.submission_text,
            submission_link=sub.submission_link,
            submission_file_url=sub.submission_file_url,
            status=sub.status,
            grade=sub.grade,
            feedback=sub.feedback,
            submitted_at=sub.submitted_at,
            graded_at=sub.graded_at,
        ),
    }
