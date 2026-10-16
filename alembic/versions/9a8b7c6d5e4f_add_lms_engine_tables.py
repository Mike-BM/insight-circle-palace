"""Add LMS engine tables and columns

Revision ID: 9a8b7c6d5e4f
Revises: f385b121093b
Create Date: 2026-10-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, None] = 'f385b121093b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to programs and enrollments if not present
    conn = op.get_bind()
    
    # Tables creation
    op.create_table(
        'lessons',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('module_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('content_type', sa.String(), nullable=False, server_default='text'),
        sa.Column('content_body', sa.Text(), nullable=True),
        sa.Column('video_url', sa.String(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('is_optional', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['module_id'], ['modules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lessons_module_id'), 'lessons', ['module_id'], unique=False)

    op.create_table(
        'lesson_completions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('enrollment_id', sa.String(length=36), nullable=False),
        sa.Column('lesson_id', sa.String(length=36), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enrollment_id'], ['enrollments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('enrollment_id', 'lesson_id', name='uix_enrollment_lesson')
    )
    op.create_index(op.f('ix_lesson_completions_enrollment_id'), 'lesson_completions', ['enrollment_id'], unique=False)
    op.create_index(op.f('ix_lesson_completions_lesson_id'), 'lesson_completions', ['lesson_id'], unique=False)

    op.create_table(
        'quizzes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('program_id', sa.String(length=36), nullable=False),
        sa.Column('lesson_id', sa.String(length=36), nullable=True),
        sa.Column('quiz_type', sa.String(), nullable=False, server_default='lesson_quiz'),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('passing_score', sa.Integer(), nullable=False, server_default='80'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quizzes_program_id'), 'quizzes', ['program_id'], unique=False)
    op.create_index(op.f('ix_quizzes_lesson_id'), 'quizzes', ['lesson_id'], unique=False)

    op.create_table(
        'quiz_questions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('quiz_id', sa.String(length=36), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_questions_quiz_id'), 'quiz_questions', ['quiz_id'], unique=False)

    op.create_table(
        'quiz_options',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('question_id', sa.String(length=36), nullable=False),
        sa.Column('option_text', sa.String(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_options_question_id'), 'quiz_options', ['question_id'], unique=False)

    op.create_table(
        'quiz_attempts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('enrollment_id', sa.String(length=36), nullable=False),
        sa.Column('quiz_id', sa.String(length=36), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('answers', sa.Text(), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enrollment_id'], ['enrollments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['quiz_id'], ['quizzes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quiz_attempts_enrollment_id'), 'quiz_attempts', ['enrollment_id'], unique=False)
    op.create_index(op.f('ix_quiz_attempts_quiz_id'), 'quiz_attempts', ['quiz_id'], unique=False)


def downgrade() -> None:
    op.drop_table('quiz_attempts')
    op.drop_table('quiz_options')
    op.drop_table('quiz_questions')
    op.drop_table('quizzes')
    op.drop_table('lesson_completions')
    op.drop_table('lessons')
