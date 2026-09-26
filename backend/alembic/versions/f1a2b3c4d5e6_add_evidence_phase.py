"""Add evidence.phase ('before' | 'after') for the civic before/after slider

Revision ID: f1a2b3c4d5e6
Revises: b2d4f6a8c0e1
Create Date: 2026-09-26 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "b2d4f6a8c0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("phase", sa.String(length=20), nullable=True))
    op.create_index("ix_evidence_commitment_phase", "evidence", ["commitment_id", "phase"])


def downgrade() -> None:
    op.drop_index("ix_evidence_commitment_phase", table_name="evidence")
    op.drop_column("evidence", "phase")
