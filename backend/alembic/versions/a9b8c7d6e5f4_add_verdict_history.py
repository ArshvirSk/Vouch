"""Add verdict_history append-only tally snapshots (Stage 2)

Revision ID: a9b8c7d6e5f4
Revises: f1a2b3c4d5e6
Create Date: 2026-09-26 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "verdict_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("commitment_id", UUID(as_uuid=True), sa.ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("met_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("broken_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("abstain_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("juror_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("event_label", sa.String(length=300), nullable=True),
        sa.Column("event_type", sa.String(length=30), nullable=False, server_default="'status'"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_verdict_history_commitment_time", "verdict_history", ["commitment_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_verdict_history_commitment_time", table_name="verdict_history")
    op.drop_table("verdict_history")
