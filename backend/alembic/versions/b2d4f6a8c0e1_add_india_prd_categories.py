"""Add India PRD categories: commitment category + civic metadata, user ward

Revision ID: b2d4f6a8c0e1
Revises: e9b0c7d4f2a3
Create Date: 2026-09-25 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2d4f6a8c0e1"
down_revision: Union[str, None] = "e9b0c7d4f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type explicitly — inline sa.Enum in add_column does not
    # auto-emit CREATE TYPE on Postgres.
    commitment_category = sa.Enum("personal", "civic", "vendor", name="commitmentcategory")
    commitment_category.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "commitments",
        sa.Column(
            "category",
            commitment_category,
            server_default=sa.text("'personal'"),
            nullable=False,
        ),
    )
    op.add_column("commitments", sa.Column("official_name", sa.String(length=200), nullable=True))
    op.add_column("commitments", sa.Column("official_role", sa.String(length=200), nullable=True))
    op.add_column("commitments", sa.Column("ward", sa.String(length=200), nullable=True))
    op.add_column("commitments", sa.Column("source_type", sa.String(length=50), nullable=True))
    op.add_column("commitments", sa.Column("source_citation", sa.String(), nullable=True))
    op.create_index("ix_commitments_category", "commitments", ["category"])
    op.create_index("ix_commitments_ward", "commitments", ["ward"])

    # Self-declared ward for civic vote eligibility (PRD §5)
    op.add_column("users", sa.Column("ward", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ward")
    op.drop_index("ix_commitments_ward", table_name="commitments")
    op.drop_index("ix_commitments_category", table_name="commitments")
    op.drop_column("commitments", "source_citation")
    op.drop_column("commitments", "source_type")
    op.drop_column("commitments", "ward")
    op.drop_column("commitments", "official_role")
    op.drop_column("commitments", "official_name")
    op.drop_column("commitments", "category")
    sa.Enum(name="commitmentcategory").drop(op.get_bind(), checkfirst=True)
