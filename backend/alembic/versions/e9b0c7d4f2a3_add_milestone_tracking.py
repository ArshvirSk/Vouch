"""Add milestone tracking

Revision ID: e9b0c7d4f2a3
Revises: c4d8e5f2a9b1
Create Date: 2026-09-25 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e9b0c7d4f2a3"
down_revision: Union[str, None] = "c4d8e5f2a9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "milestones",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("commitment_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("progress_weight", sa.Float(), nullable=False),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("pending", "submitted", "verified", "missed", name="milestonestatus"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("verified_by_id", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["commitment_id"], ["commitments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_milestones_commitment", "milestones", ["commitment_id"])
    op.create_index("ix_milestones_target_date", "milestones", ["target_date"])

    # Extend notificationtype with MILESTONE_DUE (Postgres enum ALTER)
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'MILESTONE_DUE'")


def downgrade() -> None:
    op.drop_index("ix_milestones_target_date", table_name="milestones")
    op.drop_index("ix_milestones_commitment", table_name="milestones")
    op.drop_table("milestones")
    op.execute("DROP TYPE IF EXISTS milestonestatus")
