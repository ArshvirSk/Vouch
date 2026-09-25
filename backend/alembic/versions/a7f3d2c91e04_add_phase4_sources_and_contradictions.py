"""Add Phase 4 source documents, extracted commitments, contradiction flags

Revision ID: a7f3d2c91e04
Revises: c0d7ff440adc
Create Date: 2026-09-25 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a7f3d2c91e04"
down_revision: Union[str, None] = "c0d7ff440adc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("source_type", sa.Enum("news", "transcript", "speech", "social_media", "other", name="sourcetype"), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("pending", "extracted", "approved", "rejected", name="sourcestatus"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("extraction_cache", postgresql.JSONB(), nullable=True),
        sa.Column("submitted_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_documents_status", "source_documents", ["status"])
    op.create_index("ix_source_documents_created", "source_documents", ["created_at"])

    op.create_table(
        "extracted_commitments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("subject_name", sa.String(length=200), nullable=False),
        sa.Column("statement", sa.String(), nullable=False),
        sa.Column("reformulated_condition", sa.String(), nullable=False),
        sa.Column("suggested_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.Enum("pending", "approved", "rejected", name="extractionstatus"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("commitment_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["commitment_id"], ["commitments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("commitment_id"),
    )
    op.create_index("ix_extracted_commitments_source", "extracted_commitments", ["source_id"])
    op.create_index("ix_extracted_commitments_status", "extracted_commitments", ["status"])

    op.create_table(
        "contradiction_flags",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("extracted_commitment_id", sa.Uuid(), nullable=False),
        sa.Column("existing_commitment_id", sa.Uuid(), nullable=False),
        sa.Column("explanation", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.Enum("open", "confirmed", "dismissed", name="contradictionstatus"), server_default=sa.text("'open'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extracted_commitment_id"], ["extracted_commitments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["existing_commitment_id"], ["commitments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contradiction_flags_status", "contradiction_flags", ["status"])
    op.create_index("ix_contradiction_flags_source", "contradiction_flags", ["source_id"])

    # Moderator flag on users
    op.add_column("users", sa.Column("is_moderator", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("users", "is_moderator")
    op.drop_index("ix_contradiction_flags_source", table_name="contradiction_flags")
    op.drop_index("ix_contradiction_flags_status", table_name="contradiction_flags")
    op.drop_table("contradiction_flags")
    op.drop_index("ix_extracted_commitments_status", table_name="extracted_commitments")
    op.drop_index("ix_extracted_commitments_source", table_name="extracted_commitments")
    op.drop_table("extracted_commitments")
    op.drop_index("ix_source_documents_created", table_name="source_documents")
    op.drop_index("ix_source_documents_status", table_name="source_documents")
    op.drop_table("source_documents")
    op.execute("DROP TYPE IF EXISTS contradictionstatus")
    op.execute("DROP TYPE IF EXISTS extractionstatus")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS sourcestatus")
