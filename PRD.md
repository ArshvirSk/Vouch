# Product Requirements Document

## Naming

"Hold Me Accountable" works as a tagline, but as a product name it's long and a bit self-help-app-flavored rather than platform-flavored. A few sharper alternatives, all short, ownable, and equally credible for a personal habit tracker or a public-figure watchdog:

| Name | Why it works |
|---|---|
| **Vouch** | Punchy, verb-and-noun, implies staking your word. (Check for existing trademark collisions before committing.) |

This PRD uses **Vouch** as the working title. Swap freely — the product shape doesn't depend on the name.

## 1. Problem

Accountability today is either:
- **Centralized and gameable** — a single company, platform, or newsroom decides what counts as broken promises, and that judgment can be biased, slow, or captured.
- **Informal and forgettable** — personal commitments (to friends, to a team, to yourself) live in chat threads or memory and quietly disappear once inconvenient.
- **Siloed by domain** — political fact-checkers, DAO governance tools, and habit-tracking apps all solve a version of "did X do what they said," but none share infrastructure, so trust never compounds across contexts.

There's no general-purpose, tamper-resistant record of *who promised what, whether they delivered, and who has a track record of following through* — verified by a community rather than a single authority.

## 2. Vision

A single core primitive — **commitment → evidence → community verification → reputation** — that can power three different products on shared infrastructure:

1. **Public accountability** — tracking claims and promises made by public figures, brands, or institutions.
2. **Governance accountability** — tracking whether DAOs/teams deliver on roadmap commitments, tied to on-chain proposals and voting.
3. **Personal accountability** — small-group habit and goal tracking, where your circle of friends is the "jury."

Reputation is portable across all three: a track record built in one context (e.g., reliably delivering on personal goals) is visible wherever else the same identity shows up.

## 3. Core Mechanic

```
COMMITMENT  →  EVIDENCE  →  VERIFICATION  →  REPUTATION
(claim +       (proof         (staked jury      (score
 deadline)      submitted)     decides)          updates)
```

1. **Commitment logged** — an entity (person, DAO, org) states a specific, falsifiable claim with a deadline or measurable condition. Vague claims are rejected at submission (a lightweight NLP check can flag non-falsifiable wording).
2. **Evidence submitted** — anyone can attach proof: links, screenshots, on-chain transactions, check-ins, news articles.
3. **Community verifies** — instead of a platform moderator, a jury of stakers votes on whether the commitment was met. Jurors stake reputation/tokens on their vote; incorrect votes (relative to final consensus) cost stake, correct ones earn it. This is the "held by people, made by people" part — no single admin can unilaterally rule.
4. **Reputation compounds** — every entity has a public, portable trust score reflecting their history of commitments kept vs. broken, and every juror has a track record of voting accuracy.

## 4. MVP Scope — Which Skin First

Recommendation: **start with personal peer accountability.** It's the cheapest to build, the easiest to test on real users (your own friend group), has no legal/moderation risk, and proves the core loop (commitment → evidence → jury → reputation) before you generalize to adversarial public-figure tracking, which needs much heavier moderation and legal review.

The public-figure and DAO-governance skins become v2/v3 once the core engine is validated — same data model, different commitment sources and jury composition rules.

## 5. User Personas (MVP)

- **The Committer** — states a personal goal ("I will finish the LeetCode grind, 3 problems/day, for 30 days") with a deadline.
- **The Juror** — a friend or small trusted group who verifies evidence and votes. Has their own accuracy score.
- **The Observer** — anyone who can view public commitments and reputation history, even without staking.

## 6. Feature Set

### MVP (personal accountability skin)
- Create a commitment: title, description, measurable condition, deadline, chosen jury (2–5 people).
- Submit evidence at any point before deadline (text, image, link).
- Jury voting window after deadline: each juror votes met/broken, with an optional reason.
- Reputation score per user: simple weighted history (e.g., % commitments kept, streaks, juror accuracy).
- Public profile page showing commitment history and reputation.
- Notifications (deadline approaching, jury vote needed, result posted).

### v2 — Governance accountability skin
- Import commitments from DAO proposal data (on-chain read).
- Jury = token-weighted voting instead of friend-group.
- Commitment linked to a specific proposal/roadmap item with milestone tracking.

### v3 — Public-figure accountability skin
- Commitment sourcing from news/statements (manual submission + moderation queue initially, NLP-assisted extraction later).
- Larger, open jury pools with reputation-weighted voting to resist brigading.
- Contradiction detection: flag when a public figure's new statement conflicts with a past one.

## 7. Data Model (sketch)

```
User
 - id, handle, reputation_score, created_at

Commitment
 - id, author_id, title, description,
   measurable_condition, deadline,
   status (open | evidence_submitted | in_verification | met | broken | disputed)

Evidence
 - id, commitment_id, submitter_id, type (link|image|text|onchain_tx), content, submitted_at

Jury
 - id, commitment_id, juror_id, stake_amount, vote (met|broken|abstain), voted_at

ReputationEvent
 - id, user_id, delta, reason (commitment_kept | commitment_broken | jury_accurate | jury_inaccurate), commitment_id, created_at
```

## 8. Suggested Tech Stack

Mapped to your existing stack so this is mostly assembly, not new tooling:

- **Frontend:** Next.js (web) + React Native (mobile, for check-ins/notifications)
- **Backend:** FastAPI for the API layer, business logic, reputation calculation
- **Database:** Supabase/PostgreSQL for commitments, evidence, users; Redis for notification queues and vote-window timers
- **On-chain layer (optional even for MVP, required for v2):** reputation and jury stakes recorded on Polygon or Aptos for tamper-resistance — you already have this from VERA, so the pattern transfers directly
- **AI layer:** LLM-assisted checks — flag non-falsifiable commitment wording at submission, summarize evidence for jurors, detect contradictions in v3

## 9. Reputation Algorithm (starting point)

Keep v1 simple and explainable, not black-box:

```
reputation_score = (commitments_met / total_commitments) * 100
                    + streak_bonus
                    - dispute_penalty

juror_accuracy = (votes_matching_final_consensus / total_votes_cast) * 100
```

Weight recent commitments more heavily than old ones (decay factor) so the score reflects current behavior, not a distant track record.

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Jury collusion / friend groups always voting "met" | Track juror accuracy over time; flag juries with suspiciously uniform voting for review |
| Non-falsifiable or ambiguous commitments | Require a measurable condition field; LLM-assisted flag at submission |
| Public-figure skin invites legal/defamation risk | Defer to v3; require sourced evidence only, add a dispute/appeal process, avoid unilateral "false" labeling — surface community verdict as opinion-with-evidence, not a legal claim |
| Cold start (no users, no jurors) | MVP launches inside your own social/friend circle first, where a jury already exists |

## 11. Success Metrics (MVP)

- % of commitments that reach a final jury verdict (not abandoned)
- Average juror participation rate per commitment
- Retention: % of committers who create a second commitment after their first resolves
- Reputation score correlation with actual completion rate (sanity check that the algorithm reflects reality)

## 12. Roadmap

- **Phase 1 (4–6 weeks):** Core loop for personal accountability — commitment creation, evidence submission, friend-jury voting, basic reputation score. No blockchain yet, pure Postgres.
- **Phase 2:** Public profiles, notifications, streaks, polish.
- **Phase 3:** On-chain reputation/staking (Polygon/Aptos), enabling the DAO-governance skin.
- **Phase 4:** Public-figure skin with moderation tooling and contradiction detection.