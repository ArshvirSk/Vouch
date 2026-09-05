"""001 - Initial schema matching TRD section 3

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-09-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    commitment_status = sa.Enum(
        "open", "evidence_submitted", "in_verification",
        "met", "broken", "disputed", "expired",
        name="commitmentstatus",
    )
    evidence_type = sa.Enum("link", "image", "text", "onchain_tx", name="evidencetype")
    vote_choice = sa.Enum("met", "broken", "abstain", name="votechoice")
    reputation_reason = sa.Enum(
        "commitment_kept", "commitment_broken",
        "jury_accurate", "jury_inaccurate",
        name="reputationreason",
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("handle", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("reputation_score", sa.Numeric(5, 2), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Commitments
    op.create_table(
        "commitments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("measurable_condition", sa.String(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", commitment_status, server_default=sa.text("'open'")),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_commitments_author_status", "commitments", ["author_id", "status"])
    op.create_index("ix_commitments_deadline", "commitments", ["deadline"])

    # Commitment jurors
    op.create_table(
        "commitment_jurors",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("commitment_id", sa.Uuid(), sa.ForeignKey("commitments.id"), nullable=False),
        sa.Column("juror_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_commitment_jurors_unique", "commitment_jurors",
        ["commitment_id", "juror_id"], unique=True,
    )

    # Evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("commitment_id", sa.Uuid(), sa.ForeignKey("commitments.id"), nullable=False),
        sa.Column("submitter_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", evidence_type, nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Votes
    op.create_table(
        "votes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("commitment_id", sa.Uuid(), sa.ForeignKey("commitments.id"), nullable=False),
        sa.Column("juror_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("vote", vote_choice, nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("voted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_votes_commitment_juror", "votes", ["commitment_id", "juror_id"], unique=True)
    op.create_index("ix_votes_commitment_id", "votes", ["commitment_id"])

    # Reputation events
    op.create_table(
        "reputation_events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("delta", sa.Numeric(5, 2), nullable=False),
        sa.Column("reason", reputation_reason, nullable=False),
        sa.Column("commitment_id", sa.Uuid(), sa.ForeignKey("commitments.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_reputation_events_user_created", "reputation_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("reputation_events")
    op.drop_table("votes")
    op.drop_table("evidence")
    op.drop_table("commitment_jurors")
    op.drop_table("commitments")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS reputationreason")
    op.execute("DROP TYPE IF EXISTS votechoice")
    op.execute("DROP TYPE IF EXISTS evidencetype")
    op.execute("DROP TYPE IF EXISTS commitmentstatus")
