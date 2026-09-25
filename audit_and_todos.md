# Vouch Platform Audit & Remaining Tasks

## 1. Remaining Platform Features (Roadmap)
Based on the Product Requirements Document (PRD), the platform is currently at Phase 2 (Personal MVP). The following major phases and features are remaining to complete the full platform vision:

### Phase 3: Governance Accountability Skin
- [x] **Jury Mechanics:** Token/stake-weighted jury selection from open pools is implemented (`JuryPool` model, `POST /commitments/{id}/jury-pool`, stake-weighted selection in `backend/app/tasks/jury_selection.py`, scheduled + manually triggerable via `POST /admin/run-phase5-jobs`).
- [x] **On-chain Data Ingestion:** DAO proposals import idempotently via `POST /dao/proposals` (unique per `(dao_name, external_id)`), and moderators push them into the Phase 4 pipeline with `POST /dao/proposals/{id}/to-source` — so DAO promises get the same Gemini extraction → review → publication → contradiction-check flow (`backend/app/routers/dao.py`, `dao_proposals` table).
- [ ] **Milestone Tracking:** Link commitments to specific roadmap items with ongoing milestone checks.
- [x] **On-chain Reputation:** Reputation scores are published natively on Polygon Amoy via the new `VouchReputation.sol` contract — the backend signs `keccak256(abi.encode(user, score, observedAt))` (EIP-191) and `attestReputation` stores the score + signature; anyone can verify the attestation on-chain (`verifyAttestation`). Users need a linked wallet; the job recomputes scores then attests changed ones hourly and via `POST /admin/run-phase3-jobs` (`backend/app/tasks/anchor_reputation.py`). Commitment-hash batch anchoring (with on-chain Merkle inclusion proofs via `verifyInclusion`) is supported in the same contract. *Staking itself remains off-chain for now.*

### Phase 4: Public-Figure Accountability Skin
- [x] **Commitment Sourcing:** Manual submission queues and moderation tooling for statements from news/media — `POST /sources` submits, `GET /sources` is the public queue, `POST /sources/{id}/extract` + review endpoints are the moderator tooling (`backend/app/routers/sources.py`). Moderators are bootstrapped via the `VOUCH_MODERATOR_HANDLES` env list and the `is_moderator` user flag.
- [x] **NLP Extraction:** Automated LLM-assisted extraction of commitments from public transcripts — `LLMEngine.extract_commitments` (Gemini structured output) pulls concrete promises with a falsifiable reformulation, suggested deadline, and confidence score; approved extractions publish as public commitments with an open jury pool.
- [x] **Contradiction Detection:** AI-assisted flagging — `LLMEngine.find_contradictions` compares a new statement against the subject's recent public commitments; runs automatically when an extraction is published, flags land in `contradiction_flags` with `open` status for community/moderator review (`GET /contradictions`, `POST /contradictions/{id}/review`).
- [x] **Open Juries:** Reputation-weighted jury pools — selection weights each pool member by `stake + sqrt(reputation)` (squashed so whales can't fully dominate, floored so everyone keeps a chance), with a pool-quorum gate (60% of target size, min 3) before a jury is seated. Accurate past jurors are drawn preferentially, raising the cost of brigading with fresh accounts (`backend/app/services/jury_weighting.py`, `backend/app/tasks/jury_selection.py`).

### Missing Tech Stack Components
- [ ] **Mobile App:** The PRD mentions React Native for mobile check-ins and notifications, which is currently unbuilt (only Next.js web exists).

---

## 2. Codebase Cracks and Openings (Audit / To-Do) — Status: RESOLVED 2026-09-25

### AI & LLM Services — FIXED
- **`backend/app/services/falsifiability.py`**: No longer a stub. It now runs a deterministic heuristic pre-check (rejects conditions without measurable numbers / minimum length) and delegates to the shared `LLMEngine` (`backend/app/services/llm.py`) when `VOUCH_ENABLE_LLM_CHECK=true` and `VOUCH_GEMINI_API_KEY` are set. The misleading `"Mocked — real LLM falsifiability check not wired."` reason is gone; the LLM-disabled path returns `"Heuristic check passed (LLM check disabled)."`. The commitments router uses this unified entrypoint.
- **`backend/app/services/llm.py`**: Unified with the rest of the app. It now returns the shared `app.schemas.FalsifiabilityResult` (with `is_falsifiable` / `reason` / optional `suggested_rewrite`), uses it directly as the Gemini structured-output schema, and is configurable via `VOUCH_LLM_MODEL` (default `gemini-2.5-flash`). The only "mock" remaining is the intentional fail-open when LLM checks are disabled by configuration, and the fail-open on Gemini outage (by design, so users aren't blocked).
- Verified by `backend/tests/test_audit_fixes.py` (heuristic rejects vague conditions; no mock strings) and an in-process API smoke test (vague condition → 422 with actionable reason).

### Blockchain & Web3 — FIXED
- **Merkle Tree Anchoring (`backend/app/tasks/anchor.py`)**: The naive "hash all hashes together" approach was replaced with a real binary Merkle tree (sha256 pairing, last-leaf padding for odd levels). The batch's leaves are now persisted to `backend/scratch/anchor_log.json` together with the root and tx hash, so Merkle inclusion proofs can be reconstructed later. Root construction is unit-tested (`_build_merkle_root`), including padding, ordering, and single-leaf cases. Anchoring is wired into the APScheduler (hourly) and `POST /admin/run-phase5-jobs`.
- **EAS Integration (`frontend/src/lib/eas.ts`)**: The schema UID is no longer hardcoded. `VOUCH_SCHEMA_UID` is read from `NEXT_PUBLIC_VOUCH_SCHEMA_UID` (zero-UID dev fallback). `frontend/scripts/registerSchema.js` is now a complete, working script that registers the `"uint256 reputationScore, string handle"` schema on Base Sepolia via the EAS SDK and prints/saves the UID (previously it was a stub full of unanswered comments). The profile page refuses to attest with a clear error while the schema is unregistered (`isSchemaRegistered` guard).
  - To go live: fund a Base Sepolia wallet → `cd frontend && DEPLOYER_PRIVATE_KEY=0x... node scripts/registerSchema.js` → copy the printed UID into `frontend/.env.local`.

### Data Validation — FIXED
- **Jury Size Validation (`backend/app/schemas/__init__.py`)**: The TODO is implemented. `CommitmentCreate` now has a `model_validator` that enforces private commitments to name exactly 2–5 jurors and public commitments to declare `jury_pool_size` (≥ 3). Covered by unit tests and verified end-to-end through the API (422 with clear messages).

### Additional Issues Found & Fixed During This Pass
- **Broken imports**: `backend/app/tasks/anchor.py` and `jury_selection.py` imported `app.db.session` (nonexistent module) — both tasks crashed on import. They now use the app's real `AsyncSessionLocal` from `app.database`.
- **Background jobs never scheduled**: the anchoring and public-jury-selection jobs were dead code. They now run on the APScheduler (`jury_selection` every 15 min, `anchor_batch` hourly) and can be triggered manually via `POST /admin/run-phase5-jobs`.
- **Jury selection gating**: selection now only picks pools for public commitments past their deadline in `open`/`evidence_submitted` state (previously every public commitment, even unexpired ones, was processed on every tick), and duplicate juror assignment is prevented by the existing unique constraint.
- **Dependency drift**: `backend/requirements.txt` was missing `web3`, `google-genai`, `APScheduler`, and `PyJWT` (all imported by the code). All dependencies are now pinned (matching the verified local venv versions), and `pytest`/`pytest-asyncio` are included for the new test suite.
- **Frontend build broken**: fixed five pre-existing TypeScript errors that failed `next build` — wrong Privy provider call (`getEthereumProvider` + `BrowserProvider` instead of removed `getEthersProvider`), wrong Privy embedded-wallets config shape, attesting against `stats.reputation_score` (field lives on `user`), BigInt literal below ES2020 target, and a missing `User` interface in `lib/api.ts`.

### Verification Performed
- `python -m pytest tests/test_audit_fixes.py` → 16/16 passed (Merkle tree, schema validator, falsifiability heuristic).
- Full app import check → 21 routes registered, all schedulers wired.
- In-process API smoke test via FastAPI `TestClient` → jury-size and falsifiability validation return proper 422s; `/health` OK.
- `next build` → compiles cleanly, all 8 routes build, TypeScript passes.
- Phase 4 additions: `pytest tests/` → 32 passed (incl. extraction/contradiction schemas, disabled-LLM fail-closed, moderator guard); live Gemini end-to-end check confirmed extraction pulls only concrete promises (ignored fluff sentences) and contradiction detection flags only the genuinely reversed commitment; `alembic heads` → single head `a7f3d2c91e04` with 6 new `/sources` + `/contradictions` routes registered.
- Phase 3 additions: `npx hardhat test` → 14/14 passed (attestation sign/verify/tamper-reject, non-owner rejection, batch anchoring, fixed-order Merkle inclusion proofs — matching the backend builder exactly); `pytest tests/` → 43 passed (attestation digest/signature roundtrip vs the contract encoding, jury weighting math incl. sqrt squashing and no-replacement draws); app imports with 30 routes; `alembic heads` → single head `c4d8e5f2a9b1`; `next build` still clean. Note: hardhat config converted to `.cjs` (ESM package.json), solc bumped to 0.8.28 with `cancun` EVM target for OZ v5.6 (`mcopy`), `@openzeppelin/contracts` added as a dev dependency.
