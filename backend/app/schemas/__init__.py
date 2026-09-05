import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


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
    juror_handles: list[str] = Field(..., min_length=2, max_length=5)


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
    is_falsifiable: bool
    reason: str
