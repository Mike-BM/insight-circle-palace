from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApplicationSubmit(BaseModel):
    username: Optional[str] = None
    q1_curiosity: str
    q2_awareness: str
    q3_mindset: str
    q4_reflection: str
    q5_focus: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    phone: Optional[str] = None
    country: Optional[str] = None
    honeypot: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    photo_url: Optional[str] = None
    education_level: Optional[str] = None
    bio: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token (JWT)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    email_verified: bool
    photo_url: Optional[str] = None
    education_level: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    must_change_password: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    event_date: datetime
    meeting_link: Optional[str] = None
    registration_link: Optional[str] = None
    recording_link: Optional[str] = None
    speaker_name: Optional[str] = None
    speaker_bio: Optional[str] = None
    speaker_image_url: Optional[str] = None
    price_display: Optional[str] = None
    cover_image_url: Optional[str] = None


class EventOut(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    event_date: datetime
    meeting_link: Optional[str] = None
    registration_link: Optional[str] = None
    recording_link: Optional[str] = None
    speaker_name: Optional[str] = None
    speaker_bio: Optional[str] = None
    speaker_image_url: Optional[str] = None
    price_display: Optional[str] = None
    cover_image_url: Optional[str] = None
    created_at: datetime
    is_booked: Optional[bool] = False  # Populated dynamically for users

    model_config = ConfigDict(from_attributes=True)


class EventBookingOut(BaseModel):
    id: str
    event_id: str
    user_id: str
    booked_at: datetime
    event: EventOut

    model_config = ConfigDict(from_attributes=True)


# --- Season & Certification System Schemas ---


class SeasonCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    number_of_sessions: Optional[int] = None
    status: str = "UPCOMING"
    min_attendance_count: int = 8
    min_participation_activities: int = 1


class SeasonUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    number_of_sessions: Optional[int] = None
    status: Optional[str] = None
    min_attendance_count: Optional[int] = None
    min_participation_activities: Optional[int] = None


class SeasonOut(SeasonCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SeasonSessionCreate(BaseModel):
    session_number: int
    session_date: datetime
    topic: str
    description: Optional[str] = None
    speaker: Optional[str] = None


class SeasonSessionOut(SeasonSessionCreate):
    id: str
    season_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceCreate(BaseModel):
    user_id: str
    session_id: str
    attendance_status: str = "PRESENT"


class AttendanceOut(BaseModel):
    id: str
    user_id: str
    season_id: str
    session_id: str
    attendance_status: str
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParticipationCreate(BaseModel):
    user_id: str
    activity_type: str
    activity_description: Optional[str] = None
    activity_date: datetime


class ParticipationOut(ParticipationCreate):
    id: str
    season_id: str
    recorded_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SeasonCertificateOut(BaseModel):
    id: str
    certificate_id: str
    user_id: str
    season_id: str
    certificate_type: str
    issue_date: Optional[datetime] = None
    status: str
    pdf_url: Optional[str] = None
    verification_token: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Contact & Chat Enquiry Schemas ---


class EnquiryCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    message: str
    source: Optional[str] = "website_chat"
    session_id: Optional[str] = None


class EnquiryUpdate(BaseModel):
    status: Optional[str] = None  # New, Read, Responded, Closed
    admin_notes: Optional[str] = None


class EnquiryOut(BaseModel):
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    message: str
    status: str
    source: str
    session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- User Feedback & Suggestions Schemas ---


class FeedbackCreate(BaseModel):
    rating: int
    category: Optional[str] = "General"
    tags: Optional[List[str]] = Field(default_factory=list)
    message: str
    name: Optional[str] = None
    email: Optional[str] = None
    page_url: Optional[str] = None
    session_id: Optional[str] = None


class FeedbackUpdate(BaseModel):
    status: Optional[str] = None  # New, Reviewed, Archived
    admin_notes: Optional[str] = None


class FeedbackOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    rating: int
    category: str
    tags: Optional[str] = None
    message: str
    page_url: Optional[str] = None
    session_id: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackStatsOut(BaseModel):
    total: int
    average_rating: float
    new_count: int
    reviewed_count: int
    ratings_breakdown: Dict[str, int]


# ==================== LMS CORE SCHEMAS ====================

class LessonBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    order: int = Field(default=1, ge=1)
    content_type: str = Field(default="text")  # 'text', 'video', 'markdown'
    content_body: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: int = Field(default=10, ge=1)
    is_optional: bool = False


class LessonCreate(LessonBase):
    pass


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    order: Optional[int] = None
    content_type: Optional[str] = None
    content_body: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_optional: Optional[bool] = None


class LessonOut(LessonBase):
    id: str
    module_id: str
    has_quiz: bool = False
    quiz_id: Optional[str] = None
    status: Optional[str] = "LOCKED"  # 'COMPLETED', 'CURRENT', 'AVAILABLE', 'LOCKED'
    completed_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ModuleOut(BaseModel):
    id: str
    program_id: str
    title: str
    order: int
    description: Optional[str] = None
    lessons: List[LessonOut] = []

    model_config = ConfigDict(from_attributes=True)


class CurriculumOut(BaseModel):
    program_id: str
    program_title: str
    program_slug: str
    is_enrolled: bool
    enrollment_id: Optional[str] = None
    completion_percentage: int = 0
    current_lesson_id: Optional[str] = None
    modules: List[ModuleOut] = []
    has_final_assessment: bool = False
    final_assessment_id: Optional[str] = None
    final_assessment_unlocked: bool = False
    final_assessment_passed: bool = False
    certificate_id: Optional[str] = None
    certificate_number: Optional[str] = None


class QuizOptionCreate(BaseModel):
    option_text: str = Field(..., min_length=1)
    is_correct: bool = False


class QuizOptionOut(BaseModel):
    id: str
    option_text: str

    model_config = ConfigDict(from_attributes=True)


class QuizOptionAdminOut(BaseModel):
    id: str
    option_text: str
    is_correct: bool

    model_config = ConfigDict(from_attributes=True)


class QuizQuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    explanation: Optional[str] = None
    order: int = Field(default=1, ge=1)
    options: List[QuizOptionCreate] = []


class QuizQuestionOut(BaseModel):
    id: str
    question_text: str
    order: int
    options: List[QuizOptionOut] = []

    model_config = ConfigDict(from_attributes=True)


class QuizQuestionAdminOut(BaseModel):
    id: str
    question_text: str
    explanation: Optional[str] = None
    order: int
    options: List[QuizOptionAdminOut] = []

    model_config = ConfigDict(from_attributes=True)


class QuizCreate(BaseModel):
    program_id: str
    lesson_id: Optional[str] = None
    quiz_type: str = "lesson_quiz"  # 'lesson_quiz', 'final_assessment'
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    passing_score: int = Field(default=80, ge=1, le=100)
    max_retries: int = Field(default=3, ge=0)
    time_limit_minutes: Optional[int] = None


class QuizOut(BaseModel):
    id: str
    program_id: str
    lesson_id: Optional[str] = None
    quiz_type: str
    title: str
    description: Optional[str] = None
    passing_score: int
    max_retries: int
    retries_left: int = 3
    can_retry: bool = True
    time_limit_minutes: Optional[int] = None
    questions: List[QuizQuestionOut] = []
    previous_attempt: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class QuizAdminOut(BaseModel):
    id: str
    program_id: str
    lesson_id: Optional[str] = None
    quiz_type: str
    title: str
    description: Optional[str] = None
    passing_score: int
    max_retries: int
    time_limit_minutes: Optional[int] = None
    questions: List[QuizQuestionAdminOut] = []

    model_config = ConfigDict(from_attributes=True)


class QuizSubmission(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)  # question_id -> option_id


class QuizFeedbackItem(BaseModel):
    question_id: str
    question_text: str
    user_option_id: Optional[str]
    is_correct: bool
    explanation: Optional[str] = None


class QuizResult(BaseModel):
    quiz_id: str
    score: int
    passed: bool
    passing_score: int
    correct_count: int
    total_questions: int
    attempt_number: int
    max_retries: int = 3
    retries_left: int = 0
    can_retry: bool = True
    lesson_unlocked: bool = False
    certificate_issued: bool = False
    certificate_awarded: bool = False
    certificate_id: Optional[str] = None
    certificate_url: Optional[str] = None
    feedback: List[QuizFeedbackItem] = []


class ProgramDetailOut(BaseModel):
    id: str
    slug: str
    title: str
    description: Optional[str] = None
    path: Optional[str] = None
    module_count: int = 0
    lesson_count: int = 0
    total_duration_minutes: int = 0
    learning_outcomes: List[str] = []
    is_enrolled: bool = False
    enrollment_id: Optional[str] = None
    completion_percentage: int = 0

    model_config = ConfigDict(from_attributes=True)


class LearnerProgressItem(BaseModel):
    enrollment_id: str
    user_id: str
    full_name: str
    email: str
    status: str
    enrolled_at: str
    completed_at: Optional[str] = None
    completed_lessons_count: int = 0
    total_lessons_count: int = 0
    completion_percentage: int = 0
    current_lesson_title: Optional[str] = None
    quizzes_passed_count: int = 0
    certificate_number: Optional[str] = None
