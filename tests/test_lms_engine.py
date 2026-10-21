import asyncio
import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

from app.auth import get_password_hash
from app.database import AsyncSessionLocal, Base, engine
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
)
from main import app


def test_lms_complete_lifecycle():
    """
    Comprehensive LMS lifecycle test:
    1. Programs & Duplicate Enrollment Prevention
    2. Sequential Lesson Gating & Progress Persistence
    3. Quiz Fetch (Cheat-proof / Hidden Answers) & Grading
    4. Quiz Retry Policy Enforcement
    5. Final Assessment Prerequisite Validation
    6. Certificate Issuance & Public Verification
    7. Admin Authorization & Real Data Learner Roster
    """
    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # -------------------------------------------------------------
            # STEP 1: SETUP TEST PROGRAM, MODULES, LESSONS, & QUIZZES
            # -------------------------------------------------------------
            suffix = uuid.uuid4().hex[:6]
            prog_slug = f"lms-prog-{suffix}"
            
            async with AsyncSessionLocal() as session:
                program = Program(
                    slug=prog_slug,
                    title=f"LMS Masterclass {suffix}",
                    description="Advanced Architecture & Implementation",
                    path="engineering",
                    is_active=True,
                    published=True
                )
                session.add(program)
                await session.flush()

                # Module 1
                mod1 = Module(
                    program_id=program.id,
                    title="Module 1: Foundations",
                    description="Core basics",
                    order=1
                )
                session.add(mod1)
                await session.flush()

                lesson1 = Lesson(
                    module_id=mod1.id,
                    title="Lesson 1.1: Introduction",
                    order=1,
                    content_type="text",
                    content_body="Welcome to lesson 1",
                    duration_minutes=5,
                    is_optional=False
                )
                lesson2 = Lesson(
                    module_id=mod1.id,
                    title="Lesson 1.2: Architecture",
                    order=2,
                    content_type="text",
                    content_body="System design concepts",
                    duration_minutes=15,
                    is_optional=False
                )
                session.add_all([lesson1, lesson2])
                await session.flush()

                # Lesson Quiz for Lesson 2 (max 2 retries, passing 70%)
                quiz_lesson2 = Quiz(
                    program_id=program.id,
                    lesson_id=lesson2.id,
                    quiz_type="lesson_quiz",
                    title="Lesson 1.2 Knowledge Check",
                    description="Check your understanding of architecture",
                    passing_score=70,
                    max_retries=2
                )
                session.add(quiz_lesson2)
                await session.flush()

                q1 = QuizQuestion(
                    quiz_id=quiz_lesson2.id,
                    question_text="What pattern prevents duplicate enrollments?",
                    explanation="Database unique constraints prevent race condition duplicates.",
                    order=1
                )
                session.add(q1)
                await session.flush()

                opt1_1 = QuizOption(question_id=q1.id, option_text="Unique Constraint", is_correct=True)
                opt1_2 = QuizOption(question_id=q1.id, option_text="Client Cookies", is_correct=False)
                session.add_all([opt1_1, opt1_2])

                # Final Program Assessment
                final_quiz = Quiz(
                    program_id=program.id,
                    lesson_id=None,
                    quiz_type="final_assessment",
                    title="Final Certification Exam",
                    description="Comprehensive evaluation",
                    passing_score=80,
                    max_retries=3
                )
                session.add(final_quiz)
                await session.flush()

                fq1 = QuizQuestion(
                    quiz_id=final_quiz.id,
                    question_text="Where should scores be calculated?",
                    explanation="All evaluation must be server-side for integrity.",
                    order=1
                )
                session.add(fq1)
                await session.flush()

                fopt1 = QuizOption(question_id=fq1.id, option_text="Server-Side", is_correct=True)
                fopt2 = QuizOption(question_id=fq1.id, option_text="Client Browser", is_correct=False)
                session.add_all([fopt1, fopt2])

                # Create Learner User
                learner_email = f"learner_{suffix}@example.com"
                learner_pwd = "LearnerPass123!"
                learner_user = User(
                    email=learner_email,
                    password_hash=get_password_hash(learner_pwd),
                    full_name="Grace Hopper",
                    role="user",
                    email_verified=True,
                    status="active"
                )
                session.add(learner_user)

                # Create Admin User
                admin_email = f"admin_{suffix}@example.com"
                admin_pwd = "AdminPass123!"
                admin_user = User(
                    email=admin_email,
                    password_hash=get_password_hash(admin_pwd),
                    full_name="Dean Turing",
                    role="admin",
                    email_verified=True,
                    status="active"
                )
                session.add(admin_user)
                await session.commit()

                prog_id = program.id
                l1_id = lesson1.id
                l2_id = lesson2.id
                quiz2_id = quiz_lesson2.id
                q1_id = q1.id
                opt_correct = opt1_1.id
                opt_wrong = opt1_2.id

                fq_id = final_quiz.id
                fq1_id = fq1.id
                fopt_correct = fopt1.id
                fopt_wrong = fopt2.id

            # -------------------------------------------------------------
            # STEP 2: ENROLLMENT FLOW & DUPLICATE PREVENTION
            # -------------------------------------------------------------
            # Unauthenticated enrollment attempt -> 401
            anon_enr = await ac.post(f"/programs/{prog_slug}/enroll")
            assert anon_enr.status_code == 401

            # Login as learner
            login_res = await ac.post("/auth/login", json={"email": learner_email, "password": learner_pwd})
            assert login_res.status_code == 200

            # Enroll in program -> 200
            enr_res = await ac.post(f"/programs/{prog_slug}/enroll")
            assert enr_res.status_code == 200
            enr_data = enr_res.json()
            assert enr_data["status"] == "in_progress"

            # Attempt duplicate enrollment -> 400
            dup_res = await ac.post(f"/programs/{prog_slug}/enroll")
            assert dup_res.status_code == 400
            assert "already enrolled" in dup_res.json()["detail"].lower()

            # -------------------------------------------------------------
            # STEP 3: SEQUENTIAL GATING & RESUME
            # -------------------------------------------------------------
            # Fetch curriculum
            curric_res = await ac.get(f"/programs/{prog_slug}/curriculum")
            assert curric_res.status_code == 200
            curric = curric_res.json()
            assert curric["is_enrolled"] is True
            assert curric["completion_percentage"] == 0

            mod_lessons = curric["modules"][0]["lessons"]
            # Lesson 1 should be CURRENT (first lesson)
            assert mod_lessons[0]["status"] == "CURRENT"
            # Lesson 2 should be LOCKED
            assert mod_lessons[1]["status"] == "LOCKED"

            # Learner tries to complete Lesson 2 directly -> 400 prerequisite failure
            premature_res = await ac.post(f"/programs/{prog_slug}/lessons/{l2_id}/complete")
            assert premature_res.status_code == 400
            assert "prerequisite" in premature_res.json()["detail"].lower()

            # Complete Lesson 1 legitimately -> 200
            comp1_res = await ac.post(f"/programs/{prog_slug}/lessons/{l1_id}/complete")
            assert comp1_res.status_code == 200
            comp1_data = comp1_res.json()
            assert comp1_data["completion_percentage"] == 50
            assert comp1_data["next_lesson_id"] == l2_id

            # Resume endpoint returns current next lesson (Lesson 2)
            resume_res = await ac.get(f"/programs/{prog_slug}/resume")
            assert resume_res.status_code == 200
            assert resume_res.json()["current_lesson_id"] == l2_id

            # -------------------------------------------------------------
            # STEP 4: CHEAT-PROOF QUIZZES & RETRY POLICY
            # -------------------------------------------------------------
            # Fetch Quiz 2: Verify is_correct is NOT exposed to browser
            q_res = await ac.get(f"/quizzes/{quiz2_id}")
            assert q_res.status_code == 200
            q_data = q_res.json()
            for question in q_data["questions"]:
                for opt in question["options"]:
                    assert "is_correct" not in opt

            # Submit wrong answer -> Fails quiz (score 0)
            fail_sub = await ac.post(
                f"/quizzes/{quiz2_id}/submit",
                json={"answers": {str(q1_id): str(opt_wrong)}}
            )
            assert fail_sub.status_code == 200
            f_res = fail_sub.json()
            assert f_res["score"] == 0
            assert f_res["passed"] is False
            assert f_res["attempt_number"] == 1
            assert f_res["can_retry"] is True

            # Submit passing answer on attempt 2 -> Passes quiz
            pass_sub = await ac.post(
                f"/quizzes/{quiz2_id}/submit",
                json={"answers": {str(q1_id): str(opt_correct)}}
            )
            assert pass_sub.status_code == 200
            p_res = pass_sub.json()
            assert p_res["score"] == 100
            assert p_res["passed"] is True
            assert p_res["attempt_number"] == 2

            # Lesson 2 is now marked completed via passing its quiz!
            curric_after = await ac.get(f"/programs/{prog_slug}/curriculum")
            assert curric_after.json()["completion_percentage"] == 100

            # -------------------------------------------------------------
            # STEP 5: FINAL ASSESSMENT PREREQUISITE & CERTIFICATION
            # -------------------------------------------------------------
            # Check final assessment status
            fa_res = await ac.get(f"/programs/{prog_slug}/final-assessment")
            assert fa_res.status_code == 200
            fa_data = fa_res.json()
            assert fa_data["unlocked"] is True
            assert fa_data["certificate_earned"] is False

            # Submit final assessment passing answers
            final_sub = await ac.post(
                f"/quizzes/{fq_id}/submit",
                json={"answers": {str(fq1_id): str(fopt_correct)}}
            )
            assert final_sub.status_code == 200
            final_res = final_sub.json()
            assert final_res["passed"] is True
            assert final_res["certificate_issued"] is True
            cert_num = final_res["certificate_id"]
            assert cert_num.startswith("IC-")

            # Check /programs/{slug}/final-assessment again: Certificate recorded!
            fa_earned = await ac.get(f"/programs/{prog_slug}/final-assessment")
            assert fa_earned.json()["certificate_earned"] is True
            v_code = fa_earned.json()["verification_code"]
            assert v_code is not None

            # Verify Certificate via public verification route (by verification code)
            verify_res = await ac.get(f"/verify/{v_code}")
            assert verify_res.status_code == 200
            v_data = verify_res.json()
            assert v_data["status"] == "valid"
            assert v_data["holder_name"] == "Grace Hopper"
            assert v_data["certificate_number"] == cert_num

            # Verify Certificate via unique certificate ID (certificate_number)
            verify_by_id = await ac.get(f"/verify/{cert_num}")
            assert verify_by_id.status_code == 200
            assert verify_by_id.json()["status"] == "valid"
            assert verify_by_id.json()["certificate_number"] == cert_num

            # Verify learn workspace static endpoint responds
            learn_res = await ac.get("/learn")
            assert learn_res.status_code == 200

            # Learner's certificates endpoint
            my_certs = await ac.get("/me/certificates")
            assert my_certs.status_code == 200
            assert any(c["certificate_number"] == cert_num for c in my_certs.json())

            # -------------------------------------------------------------
            # STEP 6: ADMIN AUTHORIZATION & ROSTER OVERVIEW
            # -------------------------------------------------------------
            # Learner tries to access admin roster -> 403 Forbidden
            learner_roster = await ac.get(f"/admin/programs/{prog_id}/learners")
            assert learner_roster.status_code == 403

            # Logout learner and login as Admin
            await ac.post("/auth/logout")
            admin_login = await ac.post("/auth/login", json={"email": admin_email, "password": admin_pwd})
            assert admin_login.status_code == 200

            # Admin checks real data learner roster
            admin_roster = await ac.get(f"/admin/programs/{prog_id}/learners")
            assert admin_roster.status_code == 200
            roster_data = admin_roster.json()
            assert roster_data["total_enrolled"] == 1
            learner_entry = roster_data["learners"][0]
            assert learner_entry["email"] == learner_email
            assert learner_entry["completion_percentage"] == 100
            assert learner_entry["status"] == "completed"
            assert learner_entry["certificate"]["certificate_number"] == cert_num

    asyncio.run(_run())
