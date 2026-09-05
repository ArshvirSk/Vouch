# Technical Requirements Document — Vouch

Companion to the Vouch PRD. Scope here is MVP (Phase 1: personal peer accountability skin), with notes on what Phase 3's on-chain layer will require so early schema choices don't box it out.

## 1. System Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Next.js Web │────▶│   FastAPI     │────▶│  PostgreSQL │
│  React Native│     │   (REST API)  │     │  (Supabase) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                            │
                     ┌──────┴───────┐
                     │    Redis      │  (vote-window timers,
                     │  (jobs/queue) │   notification queue)
                     └──────┬───────┘
                            │
                     ┌──────┴───────┐
                     │  LLM service  │  (falsifiability check,
                     │ (OpenAI/Anthropic) │ evidence summarization)
                     └──────────────┘
```

Phase 1 is fully off-chain. Reputation and stakes live in Postgres. The data model below is designed so a later on-chain mirror (Phase 3, Polygon or Aptos) can be bolted on without a schema rewrite — commitment/evidence/vote hashes are computed from day one even though nothing is written to a chain yet.

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Web frontend | Next.js 14+ (App Router) | Server components for public profile/commitment pages (SEO matters if this is ever public-facing) |
| Mobile | React Native / Expo | Push notifications for deadlines, vote windows |
| API | FastAPI (Python 3.11+) | Async, Pydantic models double as request/response schema + validation |
| DB | PostgreSQL via Supabase | Row-level security scoped by user_id from day one |
| Cache/Queue | Redis | Vote-window countdowns, notification dispatch, rate limiting |
| Auth | Supabase Auth (or Clerk) | Email + OAuth; single identity used across web/mobile |
| LLM | Anthropic/OpenAI API | Falsifiability check at commitment creation, evidence summarization for jurors |
| File storage | Supabase Storage | Evidence images/screenshots |
| Hosting | Vercel (web) + Railway/Fly.io (FastAPI) | Keep API stateless for easy horizontal scaling |
| Future (Phase 3) | Polygon or Aptos (Move) | On-chain reputation ledger + staking contract |

## 3. Data Model (Postgres DDL-level detail)

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  handle TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  reputation_score NUMERIC(5,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TYPE commitment_status AS ENUM (
  'open', 'evidence_submitted', 'in_verification', 'met', 'broken', 'disputed', 'expired'
);

CREATE TABLE commitments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id UUID REFERENCES users(id) NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  measurable_condition TEXT NOT NULL,   -- validated non-empty + passes LLM falsifiability check
  deadline TIMESTAMPTZ NOT NULL,
  status commitment_status DEFAULT 'open',
  content_hash TEXT NOT NULL,           -- sha256(title+description+condition+deadline), for future on-chain anchoring
  created_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

CREATE TABLE commitment_jurors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  commitment_id UUID REFERENCES commitments(id) NOT NULL,
  juror_id UUID REFERENCES users(id) NOT NULL,
  invited_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(commitment_id, juror_id)
);

CREATE TYPE evidence_type AS ENUM ('link', 'image', 'text', 'onchain_tx');

CREATE TABLE evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  commitment_id UUID REFERENCES commitments(id) NOT NULL,
  submitter_id UUID REFERENCES users(id) NOT NULL,
  type evidence_type NOT NULL,
  content TEXT NOT NULL,               -- URL, storage path, or raw text
  content_hash TEXT NOT NULL,
  submitted_at TIMESTAMPTZ DEFAULT now()
);

CREATE TYPE vote_choice AS ENUM ('met', 'broken', 'abstain');

CREATE TABLE votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  commitment_id UUID REFERENCES commitments(id) NOT NULL,
  juror_id UUID REFERENCES users(id) NOT NULL,
  vote vote_choice NOT NULL,
  reason TEXT,
  voted_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(commitment_id, juror_id)
);

CREATE TYPE reputation_reason AS ENUM (
  'commitment_kept', 'commitment_broken', 'jury_accurate', 'jury_inaccurate'
);

CREATE TABLE reputation_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) NOT NULL,
  delta NUMERIC(5,2) NOT NULL,
  reason reputation_reason NOT NULL,
  commitment_id UUID REFERENCES commitments(id),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

Indexes: `commitments(author_id, status)`, `commitments(deadline)` for the deadline-sweep job, `votes(commitment_id)`, `reputation_events(user_id, created_at)` for score recomputation windows.

## 4. Core Workflows

### 4.1 Create Commitment
1. Client sends `POST /commitments` with title, description, measurable_condition, deadline, juror handles (2–5).
2. API calls LLM falsifiability check on `measurable_condition`; rejects with 422 if it's not a concrete, checkable claim (e.g. rejects "get better at coding," accepts "solve 90 LeetCode problems by Oct 1").
3. On pass: compute `content_hash`, insert commitment row (status=`open`), insert `commitment_jurors` rows, enqueue deadline-reminder jobs in Redis.
4. Notify invited jurors (push/email).

### 4.2 Submit Evidence
1. `POST /commitments/{id}/evidence` — allowed any time before deadline, or during a short grace window after.
2. Store file in Supabase Storage if image; compute `content_hash`.
3. On first evidence submission, transition status `open` → `evidence_submitted`.
4. At deadline (Redis-scheduled job), transition to `in_verification` and open the vote window (default 72h), notify jurors.

### 4.3 Jury Voting
1. Each invited juror calls `POST /commitments/{id}/vote` once (`UNIQUE(commitment_id, juror_id)` enforces single vote).
2. When all jurors have voted, or the vote window expires, a resolution job runs:
   - Majority vote (ties → `disputed`, escalate to author + all jurors for discussion, manual re-vote allowed once).
   - Status set to `met` / `broken` / `disputed`.
3. Resolution triggers reputation recalculation (§4.4).

### 4.4 Reputation Update
Runs as an async job on commitment resolution:
```
commitment_met:    reputation_events += (+delta for author, based on streak/decay)
commitment_broken: reputation_events += (-delta for author)
jury_accurate:     +delta for each juror whose vote matched majority
jury_inaccurate:   -delta for each juror whose vote didn't match majority
```
`users.reputation_score` is a materialized rollup, recomputed from `reputation_events` on a decay-weighted window (recent events weighted higher) — recompute via scheduled job every 15 min rather than on every event, to keep writes cheap.

### 4.5 Falsifiability & Evidence Summarization (LLM)
- **Falsifiability check** (creation time): single LLM call, structured JSON output `{is_falsifiable: bool, reason: string}`. Cache nothing — this is cheap and infrequent.
- **Evidence summarization** (before vote window opens): summarize all submitted evidence into a short digest jurors see alongside raw evidence, to reduce vote-time friction. Not a verdict — just a neutral recap.

## 5. API Surface (MVP)

```
POST   /auth/signup | /auth/login
GET    /users/{handle}                  -- public profile + reputation history
POST   /commitments                     -- create
GET    /commitments/{id}
GET    /commitments?author=&status=     -- list/filter
POST   /commitments/{id}/evidence
POST   /commitments/{id}/vote
GET    /commitments/{id}/votes          -- visible only after resolution
GET    /users/{handle}/reputation-history
```

All endpoints authenticated except public profile/commitment reads (public-by-default is a product decision — confirm before build whether commitments are public or jury-only visible).

## 6. Non-Functional Requirements

- **Auditability:** every state transition (evidence added, vote cast, resolution) is append-only (reputation_events, votes, evidence are never updated/deleted, only inserted) — this is what makes the record trustworthy even before anything is on-chain.
- **Abuse resistance (MVP-level):** rate-limit commitment creation per user (Redis token bucket), cap jury size at 5, require jurors to accept invite before they can vote (prevents unwilling/inactive jurors silently defaulting).
- **Notifications:** deadline T-24h reminder, vote-window-open notice, resolution notice. Redis-backed delayed jobs (or a lightweight scheduler like APScheduler/Celery beat).
- **Latency:** all endpoints target <300ms p95; LLM calls (falsifiability check, summarization) run async/non-blocking where possible so they don't sit in the request path for commitment creation.
- **Data integrity for future on-chain migration:** `content_hash` fields on commitments/evidence exist from day one specifically so Phase 3 can anchor hashes on-chain retroactively without needing to re-derive historical data.

## 7. Phase 3 On-Chain Notes (forward-looking, not MVP-build)

- Reputation ledger and jury stakes move to a smart contract (Polygon: Solidity; Aptos: Move — pick based on which DAO ecosystems you're targeting for the governance skin).
- Postgres remains source of truth for UI/query performance; chain is the tamper-proof audit trail. Sync via an event-indexer service, not real-time writes.
- `content_hash` values already computed in Phase 1 become the leaves anchored on-chain (e.g., batched into a Merkle root per day) — no data migration needed, just start anchoring.

## 8. Open Technical Decisions (need answers before build)

1. Are commitments public by default, or visible only to author + invited jurors?
2. Vote window length — fixed 72h, or configurable per commitment?
3. What happens if a juror never votes — auto-abstain, or does it block resolution?
4. Is reputation score global (one number) or split by domain (personal vs. governance vs. public) from the start, to avoid conflating contexts later?