"""Add Phase 3 DAO proposals and on-chain reputation attestation fields

Revision ID: c4d8e5f2a9b1
Revises: a7f3d2c91e04
Create Date: 2026-09-25 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c4d8e5f2a9b1"
down_revision: Union[str, None] = "a7f3d2c91e04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dao_proposals",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("dao_name", sa.String(length=200), nullable=False),
        sa.Column("external_id", sa.String(length=300), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("proposer", sa.String(length=200), nullable=True),
        sa.Column("status", sa.Enum("pending", "imported", "rejected", name="daoproposalstatus"), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_document_id"], ["source_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dao_name", "external_id"),
    )
    op.create_index("ix_dao_proposals_status", "dao_proposals", ["status"])

    # On-chain reputation attestation state per user
    op.add_column("users", sa.Column("onchain_score", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("onchain_tx_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("onchain_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "onchain_synced_at")
    op.drop_column("users", "onchain_tx_hash")
    op.drop_column("users", "onchain_score")
    op.drop_index("ix_dao_proposals_status", table_name="dao_proposals")
    op.drop_table("dao_proposals")
    op.execute("DROP TYPE IF EXISTS daoproposalstatus")
