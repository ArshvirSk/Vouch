# Design Doc — Vouch

## 1. Reference Breakdown

**Ref A — "Accountability Partner App" (dark, orange-accent):** calendar-strip day picker, colorful category filter pills, task cards with progress bars and a **"Send Evidence"** CTA, achievement badge grid, and three data-viz patterns worth stealing directly — a circular efficiency gauge, a waveform bar chart, and a dot-matrix "punch card" heatmap for productivity over time.

**Ref B — "weCare" (light, mint/teal):** soft rounded cards on an off-white background with decorative wave lines, a Profile screen built around a stats row (count-based credentials — "12 Accountability Partners," "8 Rewards unlocked"), a partners list showing shared track record ("Goals achieved together: 3, Total goals set: 8"), warm conversational onboarding copy, and an emoji-based check-in pattern.

**Synthesis logic:** Ref A's dark, evidence-first, gamified structure maps almost one-to-one onto Vouch's core loop (a commitment card *is* their task card; "Send Evidence" *is* our evidence submission). Ref B solves a problem Ref A doesn't touch at all — how to visually represent a **relationship's track record and a person's reputation** — which is central to Vouch. So: Ref A's visual language is the primary system; Ref B's information architecture is borrowed specifically for the Profile/Reputation and Jury-relationship screens.

Neither reference has a jury/voting screen — that's new, designed fresh in §5.4, following the visual system established below.

## 2. Design Principles

1. **Evidence is the hero, not the streak.** Where habit-tracker apps foreground streaks and guilt, Vouch foregrounds the *proof* — evidence thumbnails, jury reasoning, resolution history are always visible, never buried behind a tap.
2. **Reputation is earned in public.** Scores, vote history, and track record are legible at a glance (Ref B's stats-row pattern), never hidden in a settings menu.
3. **Verdicts feel weighty, not gamified.** Resolution moments (met/broken/disputed) get restrained, confident visual treatment — no confetti-heavy game skin. Save celebratory motion for genuine milestones (long streaks, high reputation tiers).

## 3. Color System

Dark mode is primary (from Ref A) since evidence photos/screenshots read best against dark cards, and the "serious commitment" tone suits accountability better than the wellness-app pastel of Ref B.

| Token | Value | Use |
|---|---|---|
| `bg/primary` | `#0E0F14` | App background |
| `bg/surface` | `#1A1C24` | Cards |
| `bg/surface-raised` | `#22242E` | Modals, sheets |
| `accent/primary` | `#FF6B35` (orange, from Ref A) | Primary CTAs, active states, "evidence" tag |
| `accent/verified` | `#3DDC97` (mint, borrowed from Ref B) | "Met" verdict, positive reputation delta |
| `accent/broken` | `#FF4D6A` | "Broken" verdict, negative reputation delta |
| `accent/disputed` | `#9B7EDE` | Disputed status, tie-break states |
| `text/primary` | `#F5F5F7` | Headlines, body |
| `text/secondary` | `#9A9CAB` | Metadata, timestamps |
| `border/subtle` | `#2E3140` | Card borders, dividers |

The mint from Ref B is repurposed as the *positive verdict* color rather than a whole-app palette — this is the one direct color borrow across the two refs, and it works because both apps already use teal/green for "good outcome."

## 4. Typography & Iconography

- **Typeface:** A geometric sans (Inter or General Sans) — clean like Ref A, slightly warmer than a pure fintech font to match Ref B's approachability.
- **Scale:** 32/24/18/15/13px (display/title/subtitle/body/caption), consistent with both refs' generous whitespace.
- **Iconography:** Outlined, single-weight icons (matches Ref A's minimal line icons for categories/nav), not Ref B's softer filled-illustration style — keeps evidence photos as the only "warm" visual element on a page.

## 5. Key Screens

### 5.1 Home / Commitments Feed
Direct evolution of Ref A's task-card list:
- Top: greeting + a horizontal **status strip** (replaces Ref A's calendar strip) — tabs for `Open / Awaiting Evidence / In Verification / Resolved`, since Vouch's rhythm is deadline-driven, not daily-calendar-driven.
- Category pills below (Ref A pattern, unchanged) — Personal / DAO / Public Figure, once those skins exist; MVP shows only Personal.
- Commitment card: title, category tag, deadline countdown, progress bar (time elapsed vs. deadline, not % complete — you can't partially keep a promise), jury avatars (small stacked circles, new element), and the **"Send Evidence"** button lifted near-verbatim from Ref A since it's already the right pattern.

### 5.2 Create Commitment
- Conversational, step-by-step form (Ref B's onboarding tone: "What are you committing to?") rather than Ref A's dense single-screen form.
- Falsifiability check surfaces inline as a soft warning chip ("This might be hard to verify — try adding a number or deadline") rather than a blocking error, styled like a gentle nudge, not a form-validation red flash.
- Juror picker: contact-style multi-select with avatars, capped visually at 5 slots.

### 5.3 Commitment Detail + Evidence
- Hero area: countdown to deadline or, post-deadline, the verdict badge (mint/red/purple per §3).
- Evidence feed: chronological cards (image, link-preview, or text), each tagged with submitter avatar + timestamp — visually similar to a lightweight chat/timeline, not a gallery grid, so the *order and provenance* of evidence stays legible.
- "Send Evidence" CTA persists at the bottom until deadline, then is replaced by "Voting closes in Xh" once verification opens.

### 5.4 Jury Voting (new — no reference equivalent)
Designed fresh, following the established system:
- Evidence summary card up top (the LLM-generated neutral digest from the TRD) — visually distinct from raw evidence via a subtle "AI summary" label and desaturated border, so jurors know it's assistive, not authoritative.
- Three large vote buttons: **Met** (mint), **Broken** (red), **Abstain** (neutral gray outline) — deliberately oversized and unambiguous, since this is the highest-stakes tap in the app.
- Optional reason field below, collapsed by default.
- After voting: the juror's own vote is shown immediately but other jurors' votes stay hidden until resolution (prevents anchoring/groupthink) — a small "Waiting on 2 more jurors" status replaces the vote buttons.

### 5.5 Profile / Reputation
Directly restructures Ref B's Profile screen for Vouch's data:
- Stats row (Ref B pattern): **Reputation Score**, **Commitments Kept**, **Jury Accuracy** — three numbers up top, exactly like weCare's "12 Partners / 8 Rewards / 85% Life Expectancy" row.
- Tabs: **History** / **As Juror** (mirrors Ref B's "My Rewards / Goals" tab pattern).
- Reputation trend uses Ref A's **waveform bar chart** pattern (recent commitment outcomes over time, met=mint bars, broken=red bars, disputed=purple) instead of a plain line graph — visually consistent with the dark data-viz language from Ref A.
- A jury-accuracy **circular gauge** (borrowed directly from Ref A's "Efficiency" dial) shows % of votes matching consensus.

### 5.6 Partners / Jurors List
Adopts Ref B's relational framing almost directly: each row shows a person's avatar, name, and **shared track record** — "6 commitments together · 5 kept" — rather than Ref B's generic "goals achieved together," since Vouch's version is specifically about mutual verification history.

## 6. Component Library (summary)

| Component | Style source |
|---|---|
| Commitment card | Ref A task card, adapted |
| Category pill | Ref A, unchanged |
| Progress bar (time-based) | Ref A, re-purposed semantics |
| Stats row | Ref B profile pattern |
| Verdict badge | New — mint/red/purple system |
| Vote buttons (large, 3-way) | New |
| Evidence timeline card | New, chat-like |
| Reputation gauge | Ref A dial, re-labeled |
| Reputation trend bars | Ref A waveform, re-colored by verdict |
| Onboarding copy tone | Ref B, warm/conversational |

## 7. Motion & Microinteractions

- Verdict reveal: a brief (400ms) color-wash on the badge from neutral gray to mint/red/purple — restrained, not confetti.
- Evidence submission: card slides in at the top of the timeline, subtle haptic on mobile.
- Reputation delta: small "+2.4" or "-1.1" floats up from the stats row number and fades, echoing Ref B's reward-unlock micro-animation but tied to reputation instead of coupons.

## 8. Accessibility Notes

- Verdict colors (mint/red/purple) always paired with icon + text label, never color alone — critical since red/green is the most common colorblind confusion pair and this is a high-stakes UI moment.
- Vote buttons in §5.4 sized for large touch targets (min 56px height) given their importance.
- Dark background (`#0E0F14`) tested against `text/secondary` (`#9A9CAB`) for AA contrast on captions/timestamps.