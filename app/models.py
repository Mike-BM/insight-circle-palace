import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    country = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    education_level = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    role = Column(String, nullable=False, default="member")
    email_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    status = Column(String, nullable=False, default="active")

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="user", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="user", cascade="all, delete-orphan")
    event_bookings = relationship("EventBooking", back_populates="user", cascade="all, delete-orphan")
    analytics_events = relationship("AnalyticsEvent", back_populates="user", cascade="all, delete-orphan")
    
    season_attendances = relationship("Attendance", back_populates="user", cascade="all, delete-orphan")
    season_participations = relationship("Participation", back_populates="user", cascade="all, delete-orphan")
    season_certificates = relationship("SeasonCertificate", back_populates="user", cascade="all, delete-orphan")

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")

class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    q1_curiosity = Column(Text, nullable=True)
    q2_awareness = Column(Text, nullable=True)
    q3_mindset = Column(Text, nullable=True)
    q4_reflection = Column(Text, nullable=True)
    q5_focus = Column(Text, nullable=True)
    assigned_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, under_review, approved, rejected
    admin_notes = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="applications")

class Program(Base):
    __tablename__ = "programs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    path = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    modules = relationship("Module", back_populates="program", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="program", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="program", cascade="all, delete-orphan")

class Module(Base):
    __tablename__ = "modules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    program_id = Column(String(36), ForeignKey("programs.id"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    content_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    program = relationship("Program", back_populates="modules")
    completions = relationship("ModuleCompletion", back_populates="module", cascade="all, delete-orphan")

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    program_id = Column(String(36), ForeignKey("programs.id"), nullable=False)
    status = Column(String, nullable=False, default="in_progress")
    enrolled_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint('user_id', 'program_id', name='uix_user_program'),)

    user = relationship("User", back_populates="enrollments")
    program = relationship("Program", back_populates="enrollments")
    module_completions = relationship("ModuleCompletion", back_populates="enrollment", cascade="all, delete-orphan")
    certificate = relationship("Certificate", back_populates="enrollment", uselist=False, cascade="all, delete-orphan")

class ModuleCompletion(Base):
    __tablename__ = "module_completions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    enrollment_id = Column(String(36), ForeignKey("enrollments.id"), nullable=False)
    module_id = Column(String(36), ForeignKey("modules.id"), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (UniqueConstraint('enrollment_id', 'module_id', name='uix_enrollment_module'),)

    enrollment = relationship("Enrollment", back_populates="module_completions")
    module = relationship("Module", back_populates="completions")

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    enrollment_id = Column(String(36), ForeignKey("enrollments.id"), unique=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    program_id = Column(String(36), ForeignKey("programs.id"), nullable=False)
    certificate_number = Column(String, unique=True, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    pdf_url = Column(String, nullable=False)
    verification_code = Column(String, unique=True, nullable=False)

    enrollment = relationship("Enrollment", back_populates="certificate")
    user = relationship("User", back_populates="certificates")
    program = relationship("Program", back_populates="certificates")

class Event(Base):
    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    event_date = Column(DateTime(timezone=True), nullable=False)
    meeting_link = Column(String, nullable=True)
    registration_link = Column(String, nullable=True)
    recording_link = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    bookings = relationship("EventBooking", back_populates="event", cascade="all, delete-orphan")

class EventBooking(Base):
    __tablename__ = "event_bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    booked_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (UniqueConstraint('event_id', 'user_id', name='uix_event_user'),)

    event = relationship("Event", back_populates="bookings")
    user = relationship("User", back_populates="event_bookings")

class SessionRecording(Base):
    __tablename__ = "session_recordings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), nullable=False)
    events_json = Column(Text, nullable=False)  # Stored as JSON string
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False) # e.g. pageview, click
    path = Column(String, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json = Column(Text, nullable=True) # Optional JSON string

    user = relationship("User", back_populates="analytics_events")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    target_resource = Column(String, nullable=True)
    target_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    admin = relationship("User", foreign_keys=[admin_id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", foreign_keys=[user_id])

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

class Season(Base):
    __tablename__ = "seasons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    number_of_sessions = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="UPCOMING") # UPCOMING, ACTIVE, COMPLETED
    min_attendance_count = Column(Integer, nullable=True, default=8)
    min_participation_activities = Column(Integer, nullable=True, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    sessions = relationship("SeasonSession", back_populates="season", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="season", cascade="all, delete-orphan")
    participations = relationship("Participation", back_populates="season", cascade="all, delete-orphan")
    certificates = relationship("SeasonCertificate", back_populates="season", cascade="all, delete-orphan")

class SeasonSession(Base):
    __tablename__ = "season_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    season_id = Column(String(36), ForeignKey("seasons.id"), nullable=False)
    session_number = Column(Integer, nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    topic = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    speaker = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    season = relationship("Season", back_populates="sessions")
    attendances = relationship("Attendance", back_populates="session", cascade="all, delete-orphan")

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    season_id = Column(String(36), ForeignKey("seasons.id"), nullable=False)
    session_id = Column(String(36), ForeignKey("season_sessions.id"), nullable=False)
    attendance_status = Column(String, nullable=False, default="PRESENT") # PRESENT, ABSENT
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'session_id', name='uix_user_session_attendance'),)

    user = relationship("User", back_populates="season_attendances")
    season = relationship("Season", back_populates="attendances")
    session = relationship("SeasonSession", back_populates="attendances")

class Participation(Base):
    __tablename__ = "participations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    season_id = Column(String(36), ForeignKey("seasons.id"), nullable=False)
    activity_type = Column(String, nullable=False)
    activity_description = Column(Text, nullable=True)
    activity_date = Column(DateTime(timezone=True), nullable=False)
    recorded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="season_participations")
    season = relationship("Season", back_populates="participations")
    recorder = relationship("User", foreign_keys=[recorded_by])

class SeasonCertificate(Base):
    __tablename__ = "season_certificates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    certificate_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    season_id = Column(String(36), ForeignKey("seasons.id"), nullable=False)
    certificate_type = Column(String, nullable=False) # Completion, Participation
    issue_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, default="PENDING") # PENDING, APPROVED, REJECTED, ISSUED, REVOKED
    pdf_url = Column(String, nullable=True)
    verification_token = Column(String, unique=True, nullable=True, index=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('user_id', 'season_id', name='uix_user_season_certificate'),)

    user = relationship("User", foreign_keys=[user_id], back_populates="season_certificates")
    season = relationship("Season", back_populates="certificates")
    approver = relationship("User", foreign_keys=[approved_by])
