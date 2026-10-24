"""Add recordings, monday_registrations, memberships, and payment_submissions tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-24 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = ("a1b2c3d4e5f6", "9a8b7c6d5e4f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create recordings table
    op.create_table(
        "recordings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("session_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "video_source_type",
            sa.String(),
            server_default="google_drive",
            nullable=False,
        ),
        sa.Column("drive_file_id", sa.String(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column(
            "access_requirement",
            sa.String(),
            server_default="members_only",
            nullable=False,
        ),
        sa.Column(
            "published", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create monday_registrations table
    op.create_table(
        "monday_registrations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_date", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(), server_default="confirmed", nullable=False
        ),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "email", "session_date", name="uix_monday_email_session"
        ),
    )

    # 3. Create memberships table
    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status", sa.String(), server_default="pending", nullable=False
        ),
        sa.Column("fee_paid", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(), server_default="KES", nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Create payment_submissions table
    op.create_table(
        "payment_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("membership_id", sa.String(length=36), nullable=True),
        sa.Column("transaction_reference", sa.String(), nullable=False),
        sa.Column(
            "payment_method", sa.String(), server_default="mpesa", nullable=False
        ),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), server_default="KES", nullable=False),
        sa.Column("payer_name", sa.String(), nullable=True),
        sa.Column("payer_phone", sa.String(), nullable=True),
        sa.Column(
            "status", sa.String(), server_default="pending", nullable=False
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(length=36), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"]),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transaction_reference", name="uix_payment_transaction_ref"
        ),
    )


def downgrade() -> None:
    op.drop_table("payment_submissions")
    op.drop_table("memberships")
    op.drop_table("monday_registrations")
    op.drop_table("recordings")
