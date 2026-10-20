"""Add contact enquiry, feedback, and missing schema columns

Revision ID: a1b2c3d4e5f6
Revises: f385b121093b
Create Date: 2026-10-20 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f385b121093b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create contact_enquiries table if not exists
    op.create_table(
        "contact_enquiries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), server_default="New", nullable=False),
        sa.Column("source", sa.String(), server_default="chat_widget", nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create feedback table
    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("rating", sa.Integer(), server_default="5", nullable=False),
        sa.Column("category", sa.String(), server_default="General", nullable=False),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("page_url", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="New", nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Add missing columns to applications
    with op.batch_alter_table("applications") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(), server_default="pending", nullable=False))
        batch_op.add_column(sa.Column("admin_notes", sa.Text(), nullable=True))

    # 4. Add missing columns to users
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(), server_default="active", nullable=False))
        batch_op.add_column(sa.Column("must_change_password", sa.Boolean(), server_default="false", nullable=False))

    # 5. Add missing columns to programs
    with op.batch_alter_table("programs") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
        batch_op.add_column(sa.Column("capacity", sa.Integer(), nullable=True))

    # 6. Add missing columns to events
    with op.batch_alter_table("events") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
        batch_op.add_column(sa.Column("cover_image_url", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("speaker_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("speaker_bio", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("speaker_image_url", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("price_display", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("events") as batch_op:
        batch_op.drop_column("price_display")
        batch_op.drop_column("speaker_image_url")
        batch_op.drop_column("speaker_bio")
        batch_op.drop_column("speaker_name")
        batch_op.drop_column("cover_image_url")
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("programs") as batch_op:
        batch_op.drop_column("capacity")
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("must_change_password")
        batch_op.drop_column("status")

    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_column("admin_notes")
        batch_op.drop_column("status")

    op.drop_table("feedback")
    op.drop_table("contact_enquiries")
