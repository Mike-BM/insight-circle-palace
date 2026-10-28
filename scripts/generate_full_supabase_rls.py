import os
import sys
sys.path.insert(0, ".")
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from app.database import Base
from app import models

OUTPUT_PATH = os.path.join("migrations", "supabase_security_rls.sql")

sql_parts = []

sql_parts.append("""-- ==============================================================================
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
""")

for table in Base.metadata.sorted_tables:
    stmt = CreateTable(table, if_not_exists=True).compile(dialect=postgresql.dialect())
    sql_parts.append(str(stmt).strip() + ";\n")

sql_parts.append("""
-- ==============================================================================
-- PART 2: ENABLE ROW LEVEL SECURITY (RLS) ON ALL TABLES
-- ==============================================================================
""")

for table in Base.metadata.sorted_tables:
    sql_parts.append(f"ALTER TABLE IF EXISTS {table.name} ENABLE ROW LEVEL SECURITY;")

sql_parts.append("""

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
""")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_parts))

print(f"Generated complete migration file at: {OUTPUT_PATH}")
