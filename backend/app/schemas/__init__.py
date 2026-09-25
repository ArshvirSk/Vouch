import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator


# ──────────────────────────────────────────────
# Auth schemas
# ──────────────────────────────────────────────

class SignupRequest(BaseModel):
    handle: str = Field(..., min_length=3, max_length=30)
    email: str = Field(...)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: uuid.UUID
    handle: str
    reputation_score: float
    current_streak: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Commitment schemas
# ──────────────────────────────────────────────

class CommitmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    measurable_condition: str = Field(..., min_length=1)
    deadline: datetime
    juror_handles: list[str] = Field(default_factory=list)
    is_public: bool = False
    jury_pool_size: int | None = Field(None, ge=3, description="Minimum 3 for public pools")

    @model_validator(mode="after")
    def validate_juror_handles(self) -> "CommitmentCreate":
        """Enforce juror requirements by commitment visibility.

        Private commitments need exactly 2-5 named jurors; public commitments
        draw from an open pool and must declare a pool size instead.
        """
        if self.is_public:
            if self.jury_pool_size is None:
                raise ValueError("Public commitments must specify jury_pool_size (minimum 3)")
        elif not (2 <= len(self.juror_handles) <= 5):
            raise ValueError("Private commitments must name 2-5 jurors")
        return self


class CommitmentResponse(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    title: str
    description: str | None
    measurable_condition: str
    deadline: datetime
    status: str
    content_hash: str
    created_at: datetime
    resolved_at: datetime | None
    is_public: bool = False
    jury_pool_size: int | None = None
    author: UserPublic | None = None
    juror_count: int = 0
    evidence_count: int = 0

    model_config = {"from_attributes": True}


class CommitmentListResponse(BaseModel):
    commitments: list[CommitmentResponse]
    total: int


# ──────────────────────────────────────────────
# Evidence schemas
# ──────────────────────────────────────────────

class EvidenceCreate(BaseModel):
    type: str = Field(..., pattern="^(link|image|text|onchain_tx)$")
    content: str = Field(..., min_length=1)


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    commitment_id: uuid.UUID
    submitter_id: uuid.UUID
    type: str
    content: str
    content_hash: str
    submitted_at: datetime
    submitter: UserPublic | None = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Vote schemas
# ──────────────────────────────────────────────

class VoteCreate(BaseModel):
    vote: str = Field(..., pattern="^(met|broken|abstain)$")
    reason: str | None = None


class VoteResponse(BaseModel):
    id: uuid.UUID
    commitment_id: uuid.UUID
    juror_id: uuid.UUID
    vote: str
    reason: str | None
    voted_at: datetime
    juror: UserPublic | None = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Reputation schemas
# ──────────────────────────────────────────────

class ReputationEventResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    delta: float
    reason: str
    commitment_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReputationHistoryResponse(BaseModel):
    events: list[ReputationEventResponse]
    current_score: float


# ──────────────────────────────────────────────
# Falsifiability check
# ──────────────────────────────────────────────

class FalsifiabilityResult(BaseModel):
    """Result of an LLM falsifiability check (also used as the Gemini
    structured-output schema, hence the strict extra="forbid")."""

    model_config = ConfigDict(extra="forbid")

    is_falsifiable: bool
    reason: str
    suggested_rewrite: str | None = None


# ──────────────────────────────────────────────
# Phase 4: source documents, extractions, contradictions
# ──────────────────────────────────────────────

class SourceDocumentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    source_type: str = Field(..., pattern="^(news|transcript|speech|social_media|other)$")
    source_url: str | None = None
    content: str = Field(..., min_length=20)
    published_at: datetime | None = None


class ExtractedCommitmentResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    subject_name: str
    statement: str
    reformulated_condition: str
    suggested_deadline: datetime | None
    confidence: float
    status: str
    commitment_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class SourceDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    source_type: str
    source_url: str | None
    content: str
    published_at: datetime | None
    status: str
    created_at: datetime
    reviewed_at: datetime | None
    extractions: list[ExtractedCommitmentResponse] = []

    model_config = {"from_attributes": True}


class SourceDocumentListResponse(BaseModel):
    sources: list[SourceDocumentResponse]
    total: int


class ExtractionReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")


class SourceReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")


class ContradictionFlagResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    extracted_commitment_id: uuid.UUID
    existing_commitment_id: uuid.UUID
    explanation: str
    confidence: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ContradictionReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(confirmed|dismissed)$")
