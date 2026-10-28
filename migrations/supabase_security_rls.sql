-- ==============================================================================
-- INSIGHT CIRCLE PALACE - COMPLETE SUPABASE POSTGRESQL SCHEMA & RLS MIGRATION
-- ==============================================================================
-- Safe, idempotent migration script for Supabase SQL Editor.
-- 1. Creates all missing tables (CREATE TABLE IF NOT EXISTS) so no 42P01 errors occur.
-- 2. Preserves all existing tables and data.
-- 3. Enables Row Level Security (RLS) on all application tables.
-- 4. Establishes fine-grained policies protecting user privacy and gating paid content.
-- ==============================================================================

-- ==============================================================================
-- PART 1: ENSURE ALL APPLICATION TABLES EXIST (Idempotent)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS contact_enquiries (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR, 
	email VARCHAR, 
	phone VARCHAR, 
	message TEXT NOT NULL, 
	status VARCHAR NOT NULL, 
	source VARCHAR NOT NULL, 
	session_id VARCHAR, 
	admin_notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS events (
	id VARCHAR(36) NOT NULL, 
	title VARCHAR NOT NULL, 
	subtitle VARCHAR, 
	description TEXT, 
	event_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	meeting_link VARCHAR, 
	registration_link VARCHAR, 
	recording_link VARCHAR, 
	capacity INTEGER, 
	speaker_name VARCHAR, 
	speaker_bio TEXT, 
	speaker_image_url VARCHAR, 
	price_display VARCHAR, 
	cover_image_url VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS merchandise_orders (
	id VARCHAR(36) NOT NULL, 
	order_number VARCHAR(50) NOT NULL, 
	full_name VARCHAR NOT NULL, 
	phone VARCHAR NOT NULL, 
	email VARCHAR, 
	product_id VARCHAR NOT NULL, 
	product_name VARCHAR NOT NULL, 
	variant_id VARCHAR, 
	variant_name VARCHAR, 
	size VARCHAR, 
	color VARCHAR, 
	quantity INTEGER NOT NULL, 
	unit_price FLOAT NOT NULL, 
	total_price FLOAT NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	fulfillment_type VARCHAR(20) NOT NULL, 
	delivery_location TEXT, 
	notes TEXT, 
	status VARCHAR(20) NOT NULL, 
	payment_status VARCHAR(20) NOT NULL, 
	payment_method VARCHAR(30) NOT NULL, 
	payment_reference VARCHAR(100), 
	admin_notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS monday_registrations (
	id VARCHAR(36) NOT NULL, 
	session_date VARCHAR NOT NULL, 
	full_name VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	phone VARCHAR, 
	notes TEXT, 
	status VARCHAR NOT NULL, 
	registered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_monday_email_session UNIQUE (email, session_date)
);

CREATE TABLE IF NOT EXISTS programs (
	id VARCHAR(36) NOT NULL, 
	slug VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	description TEXT, 
	path VARCHAR, 
	is_active BOOLEAN NOT NULL, 
	start_date TIMESTAMP WITH TIME ZONE, 
	end_date TIMESTAMP WITH TIME ZONE, 
	capacity INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	published BOOLEAN NOT NULL, 
	price_kes FLOAT NOT NULL, 
	price_usd FLOAT NOT NULL, 
	is_paid BOOLEAN NOT NULL, 
	payment_instructions TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS recordings (
	id VARCHAR(36) NOT NULL, 
	title VARCHAR NOT NULL, 
	session_date TIMESTAMP WITH TIME ZONE, 
	description TEXT, 
	video_source_type VARCHAR NOT NULL, 
	drive_file_id VARCHAR, 
	video_url VARCHAR, 
	thumbnail_url VARCHAR, 
	access_requirement VARCHAR NOT NULL, 
	published BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS seasons (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	start_date TIMESTAMP WITH TIME ZONE, 
	end_date TIMESTAMP WITH TIME ZONE, 
	number_of_sessions INTEGER, 
	status VARCHAR NOT NULL, 
	min_attendance_count INTEGER, 
	min_participation_activities INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS session_recordings (
	id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	events_json TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS system_settings (
	id VARCHAR(36) NOT NULL, 
	key VARCHAR NOT NULL, 
	value TEXT NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	full_name VARCHAR NOT NULL, 
	phone VARCHAR, 
	country VARCHAR, 
	photo_url VARCHAR, 
	education_level VARCHAR, 
	bio TEXT, 
	role VARCHAR NOT NULL, 
	email_verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR NOT NULL, 
	must_change_password BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS analytics_events (
	id VARCHAR(36) NOT NULL, 
	event_type VARCHAR NOT NULL, 
	path VARCHAR NOT NULL, 
	user_id VARCHAR(36), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	metadata_json TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS applications (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	q1_curiosity TEXT, 
	q2_awareness TEXT, 
	q3_mindset TEXT, 
	q4_reflection TEXT, 
	q5_focus TEXT, 
	assigned_path VARCHAR, 
	status VARCHAR NOT NULL, 
	admin_notes TEXT, 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
	id VARCHAR(36) NOT NULL, 
	admin_id VARCHAR(36) NOT NULL, 
	action VARCHAR NOT NULL, 
	target_resource VARCHAR, 
	target_id VARCHAR, 
	details TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(admin_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS email_verification_tokens (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS enrollments (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	program_id VARCHAR(36) NOT NULL, 
	status VARCHAR NOT NULL, 
	enrolled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	last_accessed_lesson_id VARCHAR(36), 
	PRIMARY KEY (id), 
	CONSTRAINT uix_user_program UNIQUE (user_id, program_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(program_id) REFERENCES programs (id)
);

CREATE TABLE IF NOT EXISTS event_bookings (
	id VARCHAR(36) NOT NULL, 
	event_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	booked_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_event_user UNIQUE (event_id, user_id), 
	FOREIGN KEY(event_id) REFERENCES events (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS feedback (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	name VARCHAR, 
	email VARCHAR, 
	rating INTEGER NOT NULL, 
	category VARCHAR NOT NULL, 
	tags TEXT, 
	message TEXT NOT NULL, 
	page_url VARCHAR, 
	session_id VARCHAR, 
	status VARCHAR NOT NULL, 
	admin_notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS memberships (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	status VARCHAR NOT NULL, 
	fee_paid FLOAT, 
	currency VARCHAR NOT NULL, 
	activated_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	granted_by VARCHAR(36), 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(granted_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS modules (
	id VARCHAR(36) NOT NULL, 
	program_id VARCHAR(36) NOT NULL, 
	title VARCHAR NOT NULL, 
	"order" INTEGER NOT NULL, 
	content_url VARCHAR, 
	description TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(program_id) REFERENCES programs (id)
);

CREATE TABLE IF NOT EXISTS notifications (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	title VARCHAR NOT NULL, 
	message TEXT NOT NULL, 
	is_read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS participations (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	season_id VARCHAR(36) NOT NULL, 
	activity_type VARCHAR NOT NULL, 
	activity_description TEXT, 
	activity_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	recorded_by VARCHAR(36), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(season_id) REFERENCES seasons (id), 
	FOREIGN KEY(recorded_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS payment_access_requests (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	request_type VARCHAR(20) NOT NULL, 
	program_id VARCHAR(36), 
	subscription_plan VARCHAR(50), 
	amount FLOAT, 
	currency VARCHAR(10) NOT NULL, 
	payment_method VARCHAR(30) NOT NULL, 
	transaction_reference VARCHAR(100) NOT NULL, 
	notes TEXT, 
	proof_image_url VARCHAR(500), 
	status VARCHAR(20) NOT NULL, 
	admin_notes TEXT, 
	approved_by VARCHAR(36), 
	approved_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(program_id) REFERENCES programs (id), 
	FOREIGN KEY(approved_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS season_certificates (
	id VARCHAR(36) NOT NULL, 
	certificate_id VARCHAR NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	season_id VARCHAR(36) NOT NULL, 
	certificate_type VARCHAR NOT NULL, 
	issue_date TIMESTAMP WITH TIME ZONE, 
	status VARCHAR NOT NULL, 
	pdf_url VARCHAR, 
	verification_token VARCHAR, 
	approved_by VARCHAR(36), 
	approved_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_user_season_certificate UNIQUE (user_id, season_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(season_id) REFERENCES seasons (id), 
	FOREIGN KEY(approved_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS season_sessions (
	id VARCHAR(36) NOT NULL, 
	season_id VARCHAR(36) NOT NULL, 
	session_number INTEGER NOT NULL, 
	session_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	topic VARCHAR NOT NULL, 
	description TEXT, 
	speaker VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(season_id) REFERENCES seasons (id)
);

CREATE TABLE IF NOT EXISTS sessions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ip_address VARCHAR, 
	user_agent VARCHAR, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS attendances (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	season_id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	attendance_status VARCHAR NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_user_session_attendance UNIQUE (user_id, session_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(season_id) REFERENCES seasons (id), 
	FOREIGN KEY(session_id) REFERENCES season_sessions (id)
);

CREATE TABLE IF NOT EXISTS certificates (
	id VARCHAR(36) NOT NULL, 
	enrollment_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	program_id VARCHAR(36) NOT NULL, 
	certificate_number VARCHAR NOT NULL, 
	issued_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	pdf_url VARCHAR NOT NULL, 
	verification_code VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (enrollment_id), 
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(program_id) REFERENCES programs (id), 
	UNIQUE (certificate_number), 
	UNIQUE (verification_code)
);

CREATE TABLE IF NOT EXISTS lessons (
	id VARCHAR(36) NOT NULL, 
	module_id VARCHAR(36) NOT NULL, 
	title VARCHAR NOT NULL, 
	"order" INTEGER NOT NULL, 
	content_type VARCHAR NOT NULL, 
	content_body TEXT, 
	video_url VARCHAR, 
	duration_minutes INTEGER NOT NULL, 
	is_optional BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(module_id) REFERENCES modules (id)
);

CREATE TABLE IF NOT EXISTS module_completions (
	id VARCHAR(36) NOT NULL, 
	enrollment_id VARCHAR(36) NOT NULL, 
	module_id VARCHAR(36) NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_enrollment_module UNIQUE (enrollment_id, module_id), 
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id), 
	FOREIGN KEY(module_id) REFERENCES modules (id)
);

CREATE TABLE IF NOT EXISTS payment_submissions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	membership_id VARCHAR(36), 
	transaction_reference VARCHAR NOT NULL, 
	payment_method VARCHAR NOT NULL, 
	amount FLOAT NOT NULL, 
	currency VARCHAR NOT NULL, 
	payer_name VARCHAR, 
	payer_phone VARCHAR, 
	status VARCHAR NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	verified_by VARCHAR(36), 
	admin_notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(membership_id) REFERENCES memberships (id), 
	FOREIGN KEY(verified_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS program_entitlements (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	entitlement_type VARCHAR(20) NOT NULL, 
	program_id VARCHAR(36), 
	payment_request_id VARCHAR(36), 
	status VARCHAR(20) NOT NULL, 
	start_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	granted_by VARCHAR(36), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(program_id) REFERENCES programs (id), 
	FOREIGN KEY(payment_request_id) REFERENCES payment_access_requests (id), 
	FOREIGN KEY(granted_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS assignments (
	id VARCHAR(36) NOT NULL, 
	program_id VARCHAR(36) NOT NULL, 
	module_id VARCHAR(36), 
	lesson_id VARCHAR(36), 
	title VARCHAR NOT NULL, 
	description TEXT, 
	instructions TEXT NOT NULL, 
	rubric TEXT, 
	submission_type VARCHAR NOT NULL, 
	max_points INTEGER NOT NULL, 
	due_days INTEGER, 
	"order" INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(program_id) REFERENCES programs (id), 
	FOREIGN KEY(module_id) REFERENCES modules (id), 
	FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE IF NOT EXISTS lesson_completions (
	id VARCHAR(36) NOT NULL, 
	enrollment_id VARCHAR(36) NOT NULL, 
	lesson_id VARCHAR(36) NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_enrollment_lesson UNIQUE (enrollment_id, lesson_id), 
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id), 
	FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE IF NOT EXISTS quizzes (
	id VARCHAR(36) NOT NULL, 
	program_id VARCHAR(36) NOT NULL, 
	lesson_id VARCHAR(36), 
	quiz_type VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	description TEXT, 
	passing_score INTEGER NOT NULL, 
	max_retries INTEGER NOT NULL, 
	time_limit_minutes INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(program_id) REFERENCES programs (id), 
	FOREIGN KEY(lesson_id) REFERENCES lessons (id)
);

CREATE TABLE IF NOT EXISTS assignment_submissions (
	id VARCHAR(36) NOT NULL, 
	assignment_id VARCHAR(36) NOT NULL, 
	enrollment_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	submission_text TEXT, 
	submission_link VARCHAR, 
	submission_file_url VARCHAR, 
	status VARCHAR NOT NULL, 
	grade INTEGER, 
	feedback TEXT, 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	graded_at TIMESTAMP WITH TIME ZONE, 
	graded_by VARCHAR(36), 
	PRIMARY KEY (id), 
	FOREIGN KEY(assignment_id) REFERENCES assignments (id), 
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(graded_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
	id VARCHAR(36) NOT NULL, 
	enrollment_id VARCHAR(36) NOT NULL, 
	quiz_id VARCHAR(36) NOT NULL, 
	score INTEGER NOT NULL, 
	passed BOOLEAN NOT NULL, 
	answers TEXT, 
	attempt_number INTEGER NOT NULL, 
	attempted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id), 
	FOREIGN KEY(quiz_id) REFERENCES quizzes (id)
);

CREATE TABLE IF NOT EXISTS quiz_questions (
	id VARCHAR(36) NOT NULL, 
	quiz_id VARCHAR(36) NOT NULL, 
	question_text TEXT NOT NULL, 
	explanation TEXT, 
	"order" INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(quiz_id) REFERENCES quizzes (id)
);

CREATE TABLE IF NOT EXISTS quiz_options (
	id VARCHAR(36) NOT NULL, 
	question_id VARCHAR(36) NOT NULL, 
	option_text VARCHAR NOT NULL, 
	is_correct BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(question_id) REFERENCES quiz_questions (id)
);


-- ==============================================================================
-- PART 2: ENABLE ROW LEVEL SECURITY (RLS) ON ALL TABLES
-- ==============================================================================

ALTER TABLE IF EXISTS contact_enquiries ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS events ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS merchandise_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS monday_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS recordings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS seasons ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS session_recordings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS email_verification_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS event_bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS participations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS payment_access_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS season_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS season_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS attendances ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS lessons ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS module_completions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS payment_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS program_entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS lesson_completions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS assignment_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS quiz_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS quiz_options ENABLE ROW LEVEL SECURITY;


-- ==============================================================================
-- PART 3: HELPER FUNCTION TO VERIFY ADMINISTRATOR PRIVILEGES
-- ==============================================================================
CREATE OR REPLACE FUNCTION is_admin_user()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM users
    WHERE id = auth.uid()::text
      AND role IN ('super_admin', 'admin', 'editor', 'program_manager', 'event_manager', 'certificate_manager')
      AND status = 'active'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ==============================================================================
-- PART 4: POLICIES FOR USER PROFILES & ACCOUNTS
-- ==============================================================================
DROP POLICY IF EXISTS "Users can read own profile" ON users;
CREATE POLICY "Users can read own profile"
  ON users FOR SELECT
  USING (auth.uid()::text = id OR is_admin_user());

DROP POLICY IF EXISTS "Users can update own profile fields" ON users;
CREATE POLICY "Users can update own profile fields"
  ON users FOR UPDATE
  USING (auth.uid()::text = id)
  WITH CHECK (
    auth.uid()::text = id
    -- Prevent users from elevating their role or status through direct update
    AND role = (SELECT role FROM users WHERE id = auth.uid()::text)
    AND status = (SELECT status FROM users WHERE id = auth.uid()::text)
  );

DROP POLICY IF EXISTS "Admins have full access to users" ON users;
CREATE POLICY "Admins have full access to users"
  ON users FOR ALL
  USING (is_admin_user());

-- ==============================================================================
-- PART 5: POLICIES FOR MEMBERSHIPS & PAYMENT VERIFICATION
-- ==============================================================================
DROP POLICY IF EXISTS "Users can view own memberships" ON memberships;
CREATE POLICY "Users can view own memberships"
  ON memberships FOR SELECT
  USING (auth.uid()::text = user_id OR is_admin_user());

DROP POLICY IF EXISTS "Admins manage memberships" ON memberships;
CREATE POLICY "Admins manage memberships"
  ON memberships FOR ALL
  USING (is_admin_user());

DROP POLICY IF EXISTS "Users can view own payment submissions" ON payment_submissions;
CREATE POLICY "Users can view own payment submissions"
  ON payment_submissions FOR SELECT
  USING (auth.uid()::text = user_id OR is_admin_user());

DROP POLICY IF EXISTS "Users can insert payment submission for verification" ON payment_submissions;
CREATE POLICY "Users can insert payment submission for verification"
  ON payment_submissions FOR INSERT
  WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Only admins can verify or update payment submissions" ON payment_submissions;
CREATE POLICY "Only admins can verify or update payment submissions"
  ON payment_submissions FOR UPDATE
  USING (is_admin_user());

-- ==============================================================================
-- PART 6: POLICIES FOR RECORDINGS (Gated Content)
-- ==============================================================================
DROP POLICY IF EXISTS "Anyone can view published recordings catalogue" ON recordings;
CREATE POLICY "Anyone can view published recordings catalogue"
  ON recordings FOR SELECT
  USING (published = true OR is_admin_user());

DROP POLICY IF EXISTS "Only admins can manage recordings" ON recordings;
CREATE POLICY "Only admins can manage recordings"
  ON recordings FOR ALL
  USING (is_admin_user());

-- ==============================================================================
-- PART 7: POLICIES FOR PROGRAMS & EVENTS
-- ==============================================================================
DROP POLICY IF EXISTS "Public can view active programs" ON programs;
CREATE POLICY "Public can view active programs"
  ON programs FOR SELECT
  USING (is_active = true OR is_admin_user());

DROP POLICY IF EXISTS "Admins can manage programs" ON programs;
CREATE POLICY "Admins can manage programs"
  ON programs FOR ALL
  USING (is_admin_user());

DROP POLICY IF EXISTS "Public can view events" ON events;
CREATE POLICY "Public can view events"
  ON events FOR SELECT
  USING (true);

DROP POLICY IF EXISTS "Admins can manage events" ON events;
CREATE POLICY "Admins can manage events"
  ON events FOR ALL
  USING (is_admin_user());

-- ==============================================================================
-- PART 8: POLICIES FOR APPLICATIONS, ENROLLMENTS & CERTIFICATES
-- ==============================================================================
DROP POLICY IF EXISTS "Users can view own applications" ON applications;
CREATE POLICY "Users can view own applications"
  ON applications FOR SELECT
  USING (auth.uid()::text = user_id OR is_admin_user());

DROP POLICY IF EXISTS "Users can insert own applications" ON applications;
CREATE POLICY "Users can insert own applications"
  ON applications FOR INSERT
  WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can view own enrollments" ON enrollments;
CREATE POLICY "Users can view own enrollments"
  ON enrollments FOR SELECT
  USING (auth.uid()::text = user_id OR is_admin_user());

DROP POLICY IF EXISTS "Users can view own certificates" ON certificates;
CREATE POLICY "Users can view own certificates"
  ON certificates FOR SELECT
  USING (auth.uid()::text = user_id OR is_admin_user());

-- ==============================================================================
-- PART 9: POLICIES FOR AUDIT LOGS & SYSTEM SETTINGS
-- ==============================================================================
DROP POLICY IF EXISTS "Only admins can view audit logs" ON audit_logs;
CREATE POLICY "Only admins can view audit logs"
  ON audit_logs FOR SELECT
  USING (is_admin_user());

DROP POLICY IF EXISTS "Public can read public system settings" ON system_settings;
CREATE POLICY "Public can read public system settings"
  ON system_settings FOR SELECT
  USING (key IN ('membership_config', 'site_maintenance', 'public_notice'));

DROP POLICY IF EXISTS "Admins manage system settings" ON system_settings;
CREATE POLICY "Admins manage system settings"
  ON system_settings FOR ALL
  USING (is_admin_user());

-- ==============================================================================
-- PART 10: POLICIES FOR CONTACT ENQUIRIES, FEEDBACK & MONDAY SESSIONS
-- ==============================================================================
DROP POLICY IF EXISTS "Public can submit contact enquiries" ON contact_enquiries;
CREATE POLICY "Public can submit contact enquiries"
  ON contact_enquiries FOR INSERT
  WITH CHECK (true);

DROP POLICY IF EXISTS "Only admins can view contact enquiries" ON contact_enquiries;
CREATE POLICY "Only admins can view contact enquiries"
  ON contact_enquiries FOR SELECT
  USING (is_admin_user());

DROP POLICY IF EXISTS "Anyone can submit feedback" ON feedback;
CREATE POLICY "Anyone can submit feedback"
  ON feedback FOR INSERT
  WITH CHECK (true);

DROP POLICY IF EXISTS "Only admins can view detailed feedback" ON feedback;
CREATE POLICY "Only admins can view detailed feedback"
  ON feedback FOR SELECT
  USING (is_admin_user());

DROP POLICY IF EXISTS "Public can register for Monday sessions" ON monday_registrations;
CREATE POLICY "Public can register for Monday sessions"
  ON monday_registrations FOR INSERT
  WITH CHECK (true);

DROP POLICY IF EXISTS "Only admins can view Monday registrations list" ON monday_registrations;
CREATE POLICY "Only admins can view Monday registrations list"
  ON monday_registrations FOR SELECT
  USING (is_admin_user());

-- ==============================================================================
-- PART 11: POLICIES FOR LMS ASSIGNMENTS & QUIZZES
-- ==============================================================================
DROP POLICY IF EXISTS "Users can view own event bookings" ON event_bookings;
CREATE POLICY "Users can view own event bookings"
  ON event_bookings FOR SELECT
  USING (auth.uid()::text = user_id OR is_admin_user());

DROP POLICY IF EXISTS "Users can insert own event bookings" ON event_bookings;
CREATE POLICY "Users can insert own event bookings"
  ON event_bookings FOR INSERT
  WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Anyone can view assignments catalogue" ON assignments;
CREATE POLICY "Anyone can view assignments catalogue"
  ON assignments FOR SELECT
  USING (true);

DROP POLICY IF EXISTS "Admins manage assignments" ON assignments;
CREATE POLICY "Admins manage assignments"
  ON assignments FOR ALL
  USING (is_admin_user());

DROP POLICY IF EXISTS "Users can view own assignment submissions" ON assignment_submissions;
CREATE POLICY "Users can view own assignment submissions"
  ON assignment_submissions FOR SELECT
  USING (auth.uid()::text = user_id OR is_admin_user());

DROP POLICY IF EXISTS "Users can submit own assignments" ON assignment_submissions;
CREATE POLICY "Users can submit own assignments"
  ON assignment_submissions FOR INSERT
  WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Admins can grade and manage assignment submissions" ON assignment_submissions;
CREATE POLICY "Admins can grade and manage assignment submissions"
  ON assignment_submissions FOR ALL
  USING (is_admin_user());

DROP POLICY IF EXISTS "Anyone can view quizzes and questions" ON quizzes;
CREATE POLICY "Anyone can view quizzes and questions"
  ON quizzes FOR SELECT
  USING (true);

DROP POLICY IF EXISTS "Admins manage quizzes" ON quizzes;
CREATE POLICY "Admins manage quizzes"
  ON quizzes FOR ALL
  USING (is_admin_user());

DROP POLICY IF EXISTS "Anyone can view quiz questions" ON quiz_questions;
CREATE POLICY "Anyone can view quiz questions"
  ON quiz_questions FOR SELECT
  USING (true);

DROP POLICY IF EXISTS "Admins manage quiz questions" ON quiz_questions;
CREATE POLICY "Admins manage quiz questions"
  ON quiz_questions FOR ALL
  USING (is_admin_user());

DROP POLICY IF EXISTS "Anyone can view quiz options" ON quiz_options;
CREATE POLICY "Anyone can view quiz options"
  ON quiz_options FOR SELECT
  USING (true);

DROP POLICY IF EXISTS "Admins manage quiz options" ON quiz_options;
CREATE POLICY "Admins manage quiz options"
  ON quiz_options FOR ALL
  USING (is_admin_user());

DROP POLICY IF EXISTS "Users can view own quiz attempts" ON quiz_attempts;
CREATE POLICY "Users can view own quiz attempts"
  ON quiz_attempts FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM enrollments
      WHERE enrollments.id = quiz_attempts.enrollment_id
        AND enrollments.user_id = auth.uid()::text
    )
    OR is_admin_user()
  );

DROP POLICY IF EXISTS "Users can submit own quiz attempts" ON quiz_attempts;
CREATE POLICY "Users can submit own quiz attempts"
  ON quiz_attempts FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM enrollments
      WHERE enrollments.id = quiz_attempts.enrollment_id
        AND enrollments.user_id = auth.uid()::text
    )
  );

DROP POLICY IF EXISTS "Admins manage quiz attempts" ON quiz_attempts;
CREATE POLICY "Admins manage quiz attempts"
  ON quiz_attempts FOR ALL
  USING (is_admin_user());

-- ==============================================================================
-- PART 12: POLICIES FOR MERCHANDISE ORDERS
-- ==============================================================================
DROP POLICY IF EXISTS "Anyone can submit merchandise order" ON merchandise_orders;
CREATE POLICY "Anyone can submit merchandise order"
  ON merchandise_orders FOR INSERT
  WITH CHECK (true);

DROP POLICY IF EXISTS "Users can view own merchandise orders" ON merchandise_orders;
CREATE POLICY "Users can view own merchandise orders"
  ON merchandise_orders FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = auth.uid()::text
        AND LOWER(users.email) = LOWER(merchandise_orders.email)
    )
    OR is_admin_user()
  );

DROP POLICY IF EXISTS "Admins manage merchandise orders" ON merchandise_orders;
CREATE POLICY "Admins manage merchandise orders"
  ON merchandise_orders FOR ALL
  USING (is_admin_user());
