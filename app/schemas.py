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


class AssignmentSubmissionOut(BaseModel):
    id: str
    assignment_id: str
    user_id: str
    submission_text: Optional[str] = None
    submission_link: Optional[str] = None
    submission_file_url: Optional[str] = None
    status: str  # 'submitted', 'graded', 'resubmitted'
    grade: Optional[int] = None
    feedback: Optional[str] = None
    submitted_at: datetime
    graded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentOut(BaseModel):
    id: str
    program_id: str
    program_slug: Optional[str] = None
    program_title: Optional[str] = None
    module_id: Optional[str] = None
    module_title: Optional[str] = None
    lesson_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    instructions: str
    rubric: Optional[str] = None
    submission_type: str = "text_or_file"
    max_points: int = 100
    due_days: Optional[int] = 14
    order: int = 1
    created_at: datetime
    status: str = "pending"  # 'pending', 'submitted', 'graded'
    submission: Optional[AssignmentSubmissionOut] = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentSubmitRequest(BaseModel):
    submission_text: Optional[str] = None
    submission_link: Optional[str] = None
    submission_file_url: Optional[str] = None


# --- Video Recordings Schemas ---
class RecordingCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    session_date: Optional[datetime] = None
    description: Optional[str] = None
    video_source_type: str = "google_drive"
    drive_url_or_id: Optional[str] = None
    drive_file_id: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    access_requirement: str = "members_only"
    published: bool = True


class RecordingUpdate(BaseModel):
    title: Optional[str] = None
    session_date: Optional[datetime] = None
    description: Optional[str] = None
    video_source_type: Optional[str] = None
    drive_url_or_id: Optional[str] = None
    drive_file_id: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    access_requirement: Optional[str] = None
    published: Optional[bool] = None


class RecordingPublicOut(BaseModel):
    id: str
    title: str
    session_date: Optional[datetime] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    access_requirement: str
    published: bool
    has_playback_access: bool = False

    model_config = ConfigDict(from_attributes=True)


class RecordingAdminOut(BaseModel):
    id: str
    title: str
    session_date: Optional[datetime] = None
    description: Optional[str] = None
    video_source_type: str
    drive_file_id: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    access_requirement: str
    published: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RecordingPlaybackOut(BaseModel):
    id: str
    title: str
    session_date: Optional[datetime] = None
    video_source_type: str
    drive_file_id: Optional[str] = None
    embed_url: str
    has_access: bool = True
    access_status: str


# --- Monday Sessions Registration Schemas ---
class MondayRegistrationCreate(BaseModel):
    session_date: str = Field(..., min_length=2, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


class MondayRegistrationOut(BaseModel):
    id: str
    session_date: str
    full_name: str
    email: str
    phone: Optional[str] = None
    notes: Optional[str] = None
    status: str
    registered_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Membership & Payment Schemas ---
class MembershipConfigUpdate(BaseModel):
    fee: float = Field(..., ge=0)
    currency: str = Field(..., min_length=2, max_length=10)
    duration_value: int = Field(..., gt=0)
    duration_unit: str = Field("days", pattern="^(days|months|years)$")
    is_configured: bool = True
    payment_instructions: Optional[str] = None
    paybill_number: Optional[str] = None
    account_reference: Optional[str] = None


class MembershipConfigOut(BaseModel):
    fee: float = 1500.0
    currency: str = "KES"
    duration_value: int = 30
    duration_unit: str = "days"
    is_configured: bool = True
    payment_instructions: Optional[str] = None
    paybill_number: Optional[str] = None
    account_reference: Optional[str] = None


class PaymentSubmissionCreate(BaseModel):
    transaction_reference: str = Field(..., min_length=4, max_length=60)
    payment_method: str = Field("mpesa", max_length=30)
    amount: float = Field(..., gt=0)
    currency: str = Field("KES", min_length=2, max_length=10)
    payer_name: Optional[str] = Field(None, max_length=100)
    payer_phone: Optional[str] = Field(None, max_length=50)


class PaymentSubmissionOut(BaseModel):
    id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    transaction_reference: str
    payment_method: str
    amount: float
    currency: str
    payer_name: Optional[str] = None
    payer_phone: Optional[str] = None
    status: str
    submitted_at: datetime
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    admin_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentVerificationAction(BaseModel):
    action: str = Field(..., pattern="^(approve|approved|reject|rejected)$")
    admin_notes: Optional[str] = None


class MembershipGrantAction(BaseModel):
    user_id: str
    duration_days: Optional[int] = None
    notes: Optional[str] = None


class MembershipStatusOut(BaseModel):
    user_id: str
    has_access: bool
    status: str
    is_admin: bool = False
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    days_remaining: Optional[int] = None
    membership_id: Optional[str] = None
    pending_submission: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class MemberOverviewOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    registered_at: datetime
    user_status: str
    user_role: str
    membership_id: Optional[str] = None
    membership_status: str  # "registered", "pending_verification", "paid", "expired", "suspended", "revoked"
    payment_id: Optional[str] = None
    payment_status: str  # "unpaid", "pending", "approved", "rejected"
    transaction_reference: Optional[str] = None
    payment_method: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    verified_by_name: Optional[str] = None
    verified_by_email: Optional[str] = None
    verified_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    monday_sessions_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ManualPaymentVerifyRequest(BaseModel):
    user_id: str
    payment_id: Optional[str] = None
    transaction_reference: str = Field(..., min_length=3, max_length=100)
    payment_method: str = Field(default="mpesa", max_length=50)
    amount: float = Field(default=1500.0, ge=0.0)
    currency: str = Field(default="KES", max_length=10)
    verification_date: Optional[datetime] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=3650)
    admin_notes: Optional[str] = Field(default=None, max_length=1000)
    payer_name: Optional[str] = Field(default=None, max_length=100)
    payer_phone: Optional[str] = Field(default=None, max_length=50)


class MembershipActionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|suspend|revoke|keep_pending|grant)$")
    admin_notes: Optional[str] = Field(default=None, max_length=1000)
    transaction_reference: Optional[str] = Field(default=None, max_length=100)
    duration_days: Optional[int] = Field(default=None, ge=1, le=3650)
    verification_date: Optional[datetime] = None


# --- Payment Access Request & LMS Entitlement Schemas ---

class PaymentRequestCreate(BaseModel):
    item_type: str = Field(default="program", description="program or subscription")
    program_slug: Optional[str] = Field(default=None, description="Slug of target program")
    subscription_plan: Optional[str] = Field(default=None, description="Subscription plan name")
    payment_method: str = Field(default="mpesa_manual", description="mpesa_manual, bank_transfer, cash, other")
    transaction_reference: str = Field(..., min_length=3, max_length=100, description="M-Pesa confirmation code or bank ref")
    amount: Optional[float] = Field(default=0.0, ge=0.0)
    currency: str = Field(default="KES", max_length=10)
    notes: Optional[str] = Field(default=None, max_length=1000)
    proof_image_url: Optional[str] = Field(default=None, max_length=500)


class PaymentRequestOut(BaseModel):
    id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    request_type: str
    program_id: Optional[str] = None
    program_slug: Optional[str] = None
    program_title: Optional[str] = None
    subscription_plan: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "KES"
    payment_method: str
    transaction_reference: str
    notes: Optional[str] = None
    proof_image_url: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentRequestApprove(BaseModel):
    admin_notes: Optional[str] = Field(default=None, max_length=1000)
    custom_expiry_days: Optional[int] = Field(default=None, ge=1, le=3650)


class PaymentRequestReject(BaseModel):
    admin_notes: str = Field(..., min_length=3, max_length=1000, description="Reason for rejection")


class ProgramEntitlementOut(BaseModel):
    id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    entitlement_type: str
    program_id: Optional[str] = None
    program_title: Optional[str] = None
    status: str
    start_date: datetime
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ManualEntitlementGrant(BaseModel):
    user_id: str = Field(..., min_length=1)
    entitlement_type: str = Field(default="program")
    program_id: Optional[str] = None
    expiry_days: Optional[int] = Field(default=None, ge=1, le=3650)


# --- Merchandise Schemas ---

class MerchandiseVariantOut(BaseModel):
    id: str
    name: str
    price: float


class MerchandiseItemOut(BaseModel):
    id: str
    name: str
    category: str
    price_min: float
    price_max: float
    price_display: str
    description: str
    image: str
    webp_image: Optional[str] = None
    variants: List[MerchandiseVariantOut] = []
    colors: List[str] = []
    sizes: Optional[List[str]] = None


class MerchandiseOrderCreate(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=100)
    variant_id: Optional[str] = Field(default=None, max_length=100)
    variant_name: Optional[str] = Field(default=None, max_length=150)
    size: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, max_length=50)
    quantity: int = Field(default=1, ge=1, le=100)
    customer_name: Optional[str] = Field(default=None, max_length=120)
    full_name: Optional[str] = Field(default=None, max_length=120)
    customer_phone: Optional[str] = Field(default=None, max_length=30)
    phone: Optional[str] = Field(default=None, max_length=30)
    customer_email: Optional[EmailStr] = None
    email: Optional[EmailStr] = None
    fulfillment_type: Optional[str] = Field(default="direct", max_length=50)
    delivery_address: Optional[str] = Field(default=None, max_length=300)
    delivery_location: Optional[str] = Field(default=None, max_length=300)
    notes: Optional[str] = Field(default=None, max_length=1000)


class MerchandiseOrderUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(pending|confirmed|processing|dispatched|completed|cancelled)$")
    payment_status: Optional[str] = Field(default=None, pattern="^(unpaid|paid|refunded)$")
    payment_reference: Optional[str] = Field(default=None, max_length=100)
    admin_notes: Optional[str] = Field(default=None, max_length=1000)


class MerchandiseOrderOut(BaseModel):
    id: str
    order_number: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    product_id: str
    product_name: str
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: int
    unit_price: float
    total_price: float
    currency: str = "KES"
    fulfillment_type: str
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    status: str
    payment_status: str
    payment_method: str
    payment_reference: Optional[str] = None
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
