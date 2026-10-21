import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Certificate,
    Enrollment,
    Lesson,
    LessonCompletion,
    Module,
    Program,
    Quiz,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    User,
    utcnow,
)
from app.schemas import (
    QuizFeedbackItem,
    QuizOptionOut,
    QuizOut,
    QuizQuestionOut,
    QuizResult,
    QuizSubmission,
)
from app.services.certificates import generate_certificate_for_enrollment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["quizzes"])


@router.get("/quizzes/{quiz_id}", response_model=QuizOut)
async def get_quiz_for_learner(
    quiz_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch a quiz for a learner. Answers ('is_correct') are strictly stripped.
    Enforces program enrollment and lesson sequential prerequisite checks.
    """
    # Fetch quiz with questions and options
    result = await db.execute(
        select(Quiz)
        .options(
            selectinload(Quiz.questions).selectinload(QuizQuestion.options)
        )
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalars().first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    # Check program enrollment unless user is admin
    enrollment = None
    if current_user.role != "admin":
        enr_res = await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == current_user.id,
                Enrollment.program_id == quiz.program_id
            )
        )
        enrollment = enr_res.scalars().first()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in this program to access this assessment."
            )

        # If this is a final assessment, verify all required lessons are completed
        if quiz.quiz_type == "final_assessment" or quiz.lesson_id is None:
            # Get all non-optional lessons
            all_lessons_res = await db.execute(
                select(Lesson.id)
                .join(Module, Lesson.module_id == Module.id)
                .where(
                    Module.program_id == quiz.program_id,
                    Lesson.is_optional == False  # noqa: E712
                )
            )
            req_lesson_ids = set(all_lessons_res.scalars().all())

            comp_res = await db.execute(
                select(LessonCompletion.lesson_id).where(
                    LessonCompletion.enrollment_id == enrollment.id
                )
            )
            completed_ids = set(comp_res.scalars().all())

            if not req_lesson_ids.issubset(completed_ids):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Final assessment is locked. You have completed {len(completed_ids & req_lesson_ids)} of {len(req_lesson_ids)} required lessons."
                )

    # Calculate prior attempts
    attempts_count = 0
    already_passed = False
    if enrollment:
        att_res = await db.execute(
            select(QuizAttempt)
            .where(
                QuizAttempt.enrollment_id == enrollment.id,
                QuizAttempt.quiz_id == quiz.id
            )
            .order_by(QuizAttempt.attempt_number.asc())
        )
        attempts = att_res.scalars().all()
        attempts_count = len(attempts)
        already_passed = any(a.passed for a in attempts)

    can_attempt = True
    if already_passed:
        can_attempt = False
    elif quiz.max_retries > 0 and attempts_count >= quiz.max_retries:
        can_attempt = False

    # Format questions and options without is_correct
    sorted_questions = sorted(quiz.questions, key=lambda q: q.order)
    questions_out = []
    for q in sorted_questions:
        options_out = [
            QuizOptionOut(id=opt.id, option_text=opt.option_text)
            for opt in q.options
        ]
        questions_out.append(
            QuizQuestionOut(
                id=q.id,
                question_text=q.question_text,
                order=q.order,
                options=options_out
            )
        )

    return QuizOut(
        id=quiz.id,
        program_id=quiz.program_id,
        lesson_id=quiz.lesson_id,
        quiz_type=quiz.quiz_type,
        title=quiz.title,
        description=quiz.description,
        passing_score=quiz.passing_score,
        max_retries=quiz.max_retries,
        time_limit_minutes=quiz.time_limit_minutes,
        questions=questions_out,
        attempts_count=attempts_count,
        already_passed=already_passed,
        can_attempt=can_attempt
    )


@router.post("/quizzes/{quiz_id}/submit", response_model=QuizResult)
async def submit_quiz(
    quiz_id: str,
    submission: QuizSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submits and grades a quiz or final assessment on the server.
    - Prevents tampering: Answers and scores are never trusted from client.
    - Enforces retry limits and prerequisite lesson completions.
    - If passed and is final assessment, automatically validates all lessons and issues Certificate.
    """
    # Fetch quiz with questions and options including correctness
    result = await db.execute(
        select(Quiz)
        .options(
            selectinload(Quiz.questions).selectinload(QuizQuestion.options)
        )
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalars().first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )

    # Fetch user's enrollment
    enr_res = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.program_id == quiz.program_id
        )
    )
    enrollment = enr_res.scalars().first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled to submit this assessment."
        )

    # If this is final assessment, strictly verify that every required lesson is completed
    is_final = (quiz.quiz_type == "final_assessment" or quiz.lesson_id is None)
    if is_final:
        all_lessons_res = await db.execute(
            select(Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Module.program_id == quiz.program_id,
                Lesson.is_optional == False  # noqa: E712
            )
        )
        req_lesson_ids = set(all_lessons_res.scalars().all())

        comp_res = await db.execute(
            select(LessonCompletion.lesson_id).where(
                LessonCompletion.enrollment_id == enrollment.id
            )
        )
        completed_ids = set(comp_res.scalars().all())

        if not req_lesson_ids.issubset(completed_ids):
            missing_count = len(req_lesson_ids - completed_ids)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit final assessment. You still have {missing_count} uncompleted required lesson(s)."
            )

    # Check attempt limits
    att_res = await db.execute(
        select(QuizAttempt)
        .where(
            QuizAttempt.enrollment_id == enrollment.id,
            QuizAttempt.quiz_id == quiz.id
        )
        .order_by(QuizAttempt.attempt_number.asc())
    )
    prior_attempts = att_res.scalars().all()
    already_passed = any(a.passed for a in prior_attempts)
    attempts_count = len(prior_attempts)

    if already_passed:
        # Learner has already mastered this quiz
        pass
    elif quiz.max_retries > 0 and attempts_count >= quiz.max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum attempts ({quiz.max_retries}) reached for this assessment."
        )

    # Server-Side Grading
    feedback_items: List[QuizFeedbackItem] = []
    correct_count = 0
    total_questions = len(quiz.questions)

    for question in sorted(quiz.questions, key=lambda q: q.order):
        user_choice_id = submission.answers.get(str(question.id))
        correct_option = next((opt for opt in question.options if opt.is_correct), None)
        
        is_correct = False
        if correct_option and user_choice_id and str(correct_option.id) == str(user_choice_id):
            is_correct = True
            correct_count += 1

        feedback_items.append(
            QuizFeedbackItem(
                question_id=str(question.id),
                question_text=question.question_text,
                user_option_id=user_choice_id,
                is_correct=is_correct,
                explanation=question.explanation
            )
        )

    score = int(round((correct_count / total_questions) * 100)) if total_questions > 0 else 100
    passed = score >= quiz.passing_score
    attempt_number = attempts_count + 1

    # Persist attempt
    attempt = QuizAttempt(
        enrollment_id=enrollment.id,
        quiz_id=quiz.id,
        score=score,
        passed=passed,
        answers=json.dumps(submission.answers),
        attempt_number=attempt_number,
        attempted_at=utcnow()
    )
    db.add(attempt)

    certificate_issued = False
    certificate_id = None
    certificate_url = None

    # Actions upon passing
    if passed:
        # If this is a lesson quiz, mark the lesson as completed!
        if quiz.lesson_id:
            existing_comp = await db.execute(
                select(LessonCompletion).where(
                    LessonCompletion.enrollment_id == enrollment.id,
                    LessonCompletion.lesson_id == quiz.lesson_id
                )
            )
            if not existing_comp.scalars().first():
                db.add(LessonCompletion(
                    enrollment_id=enrollment.id,
                    lesson_id=quiz.lesson_id,
                    completed_at=utcnow()
                ))
            enrollment.last_accessed_lesson_id = quiz.lesson_id

        # If this is the final assessment, verify and issue Certificate
        if is_final:
            enrollment.status = "completed"
            await db.commit()  # commit status and attempt first

            cert = await generate_certificate_for_enrollment(enrollment, db)
            certificate_issued = True
            certificate_id = cert.certificate_number
            certificate_url = cert.pdf_url
        else:
            await db.commit()
    else:
        await db.commit()

    can_retry = (not passed and (quiz.max_retries <= 0 or attempt_number < quiz.max_retries))
    retries_left = max(0, quiz.max_retries - attempt_number) if quiz.max_retries > 0 else 999

    return QuizResult(
        quiz_id=quiz.id,
        score=score,
        passed=passed,
        passing_score=quiz.passing_score,
        correct_count=correct_count,
        total_questions=total_questions,
        attempt_number=attempt_number,
        max_retries=quiz.max_retries,
        retries_left=retries_left,
        can_retry=can_retry,
        lesson_unlocked=passed,
        certificate_issued=certificate_issued,
        certificate_awarded=certificate_issued,
        certificate_id=certificate_id,
        certificate_url=certificate_url,
        feedback=feedback_items
    )


@router.get("/programs/{slug}/final-assessment")
async def get_program_final_assessment(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the final assessment status and data for a given program.
    Checks prerequisite lesson completions.
    """
    # Fetch program
    prog_res = await db.execute(select(Program).where(Program.slug == slug))
    program = prog_res.scalars().first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Fetch enrollment
    enr_res = await db.execute(
        select(Enrollment).where(
            Enrollment.user_id == current_user.id,
            Enrollment.program_id == program.id
        )
    )
    enrollment = enr_res.scalars().first()
    if not enrollment:
        raise HTTPException(
            status_code=403,
            detail="You must be enrolled to access this program's final assessment."
        )

    # Check lesson completions
    all_lessons_res = await db.execute(
        select(Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .where(
            Module.program_id == program.id,
            Lesson.is_optional == False  # noqa: E712
        )
    )
    required_ids = set(all_lessons_res.scalars().all())

    comp_res = await db.execute(
        select(LessonCompletion.lesson_id).where(
            LessonCompletion.enrollment_id == enrollment.id
        )
    )
    completed_ids = set(comp_res.scalars().all())

    is_unlocked = required_ids.issubset(completed_ids) if required_ids else True
    total_required = len(required_ids)
    completed_count = len(completed_ids & required_ids)

    # Check for Certificate
    cert_res = await db.execute(
        select(Certificate).where(Certificate.enrollment_id == enrollment.id)
    )
    cert = cert_res.scalars().first()

    # Find the final quiz for this program
    quiz_res = await db.execute(
        select(Quiz)
        .options(
            selectinload(Quiz.questions).selectinload(QuizQuestion.options)
        )
        .where(
            Quiz.program_id == program.id,
            Quiz.quiz_type == "final_assessment"
        )
    )
    quiz = quiz_res.scalars().first()

    # If no designated final_assessment quiz, check for any quiz with lesson_id is None
    if not quiz:
        quiz_res = await db.execute(
            select(Quiz)
            .options(
                selectinload(Quiz.questions).selectinload(QuizQuestion.options)
            )
            .where(
                Quiz.program_id == program.id,
                Quiz.lesson_id.is_(None)
            )
        )
        quiz = quiz_res.scalars().first()

    # Format quiz details if unlocked
    quiz_out = None
    if quiz and is_unlocked:
        # Count prior attempts
        att_res = await db.execute(
            select(QuizAttempt)
            .where(
                QuizAttempt.enrollment_id == enrollment.id,
                QuizAttempt.quiz_id == quiz.id
            )
            .order_by(QuizAttempt.attempt_number.asc())
        )
        attempts = att_res.scalars().all()
        attempts_count = len(attempts)
        already_passed = any(a.passed for a in attempts)
        can_attempt = not already_passed and (quiz.max_retries <= 0 or attempts_count < quiz.max_retries)

        sorted_questions = sorted(quiz.questions, key=lambda q: q.order)
        questions_out = [
            QuizQuestionOut(
                id=q.id,
                question_text=q.question_text,
                order=q.order,
                options=[QuizOptionOut(id=opt.id, option_text=opt.option_text) for opt in q.options]
            )
            for q in sorted_questions
        ]

        quiz_out = QuizOut(
            id=quiz.id,
            program_id=quiz.program_id,
            lesson_id=quiz.lesson_id,
            quiz_type=quiz.quiz_type,
            title=quiz.title,
            description=quiz.description,
            passing_score=quiz.passing_score,
            max_retries=quiz.max_retries,
            time_limit_minutes=quiz.time_limit_minutes,
            questions=questions_out,
            attempts_count=attempts_count,
            already_passed=already_passed,
            can_attempt=can_attempt
        )

    return {
        "program_id": program.id,
        "program_title": program.title,
        "unlocked": is_unlocked,
        "total_required_lessons": total_required,
        "completed_required_lessons": completed_count,
        "quiz": quiz_out,
        "has_quiz": quiz is not None,
        "certificate_earned": cert is not None,
        "certificate_url": cert.pdf_url if cert else None,
        "certificate_number": cert.certificate_number if cert else None,
        "verification_code": cert.verification_code if cert else None,
    }
