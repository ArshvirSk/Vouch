"use client";

/**
 * Commitment Detail + Evidence Timeline — Design Doc §5.3.
 * Hero: countdown/verdict badge. Evidence timeline. Send Evidence CTA.
 */

import { useState, useEffect, use } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  getCommitment, submitEvidence, listEvidence, getVotes, getJuryPool, joinJuryPool,
  type Commitment, type Evidence, type Vote, type JuryPoolInfo
} from "@/lib/api";
import { formatRelativeTime, formatDate, getStatusLabel, calcTimeProgress } from "@/lib/utils";
import { VoteButtons } from "@/components/VoteButtons";
import { castVote } from "@/lib/api";
import { CivicDetailPage } from "@/components/civic/CivicDetailPage";
import Link from "next/link";
import { ArrowLeft, Check, X, Scale, ChevronDown, ChevronRight, Paperclip, Globe, Users } from "lucide-react";

export default function CommitmentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user } = useAuth();
  const [commitment, setCommitment] = useState<Commitment | null>(null);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEvidenceForm, setShowEvidenceForm] = useState(false);
  const [evidenceContent, setEvidenceContent] = useState("");
  const [evidenceType, setEvidenceType] = useState("text");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Voting state
  const [showVoting, setShowVoting] = useState(false);
  const [voteReason, setVoteReason] = useState("");
  const [voted, setVoted] = useState(false);

  // Jury pool state
  const [juryPool, setJuryPool] = useState<JuryPoolInfo | null>(null);
  const [joiningPool, setJoiningPool] = useState(false);

  // Vote results state
  const [voteResults, setVoteResults] = useState<Vote[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const data = await getCommitment(id);
        setCommitment(data);

        // Load evidence from API
        try {
          const ev = await listEvidence(id);
          setEvidenceList(ev);
        } catch { /* Evidence list not critical */ }

        // Load jury pool info for public commitments
        if (data.is_public) {
          try {
            const pool = await getJuryPool(id);
            setJuryPool(pool);
          } catch { /* Pool info not critical */ }
        }

        // Load vote results for resolved commitments
        if (["met", "broken", "disputed"].includes(data.status)) {
          try {
            const votes = await getVotes(id);
            setVoteResults(votes);
          } catch { /* Votes not critical */ }
        }
      } catch {
        setCommitment(getDemoCommitment(id));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const isPastDeadline = commitment
    ? new Date(commitment.deadline) < new Date()
    : false;
  const isResolved = commitment
    ? ["met", "broken", "disputed", "expired"].includes(commitment.status)
    : false;
  const isVerification = commitment?.status === "in_verification";

  const handleSubmitEvidence = async () => {
    if (!user || !commitment) return;
    setSubmitting(true);
    setError(null);
    try {
      const evidence = await submitEvidence(
        commitment.id,
        { type: evidenceType, content: evidenceContent },
        user.token
      );
      setEvidenceList([evidence, ...evidenceList]);
      setEvidenceContent("");
      setShowEvidenceForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit evidence");
    } finally {
      setSubmitting(false);
    }
  };

  const handleVote = async (choice: "met" | "broken" | "abstain") => {
    if (!user || !commitment) return;
    try {
      await castVote(
        commitment.id,
        { vote: choice, reason: voteReason || undefined },
        user.token
      );
      setVoted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cast vote");
    }
  };

  if (loading) {
    return (
      <div
        className="container"
        style={{
          paddingTop: "60px",
          textAlign: "center",
          color: "var(--text-secondary)",
        }}
      >
        Loading...
      </div>
    );
  }

  if (!commitment) {
    return (
      <div
        className="container"
        style={{
          paddingTop: "60px",
          textAlign: "center",
          color: "var(--text-secondary)",
        }}
      >
        Commitment not found
      </div>
    );
  }

  // Civic commitments get the enriched detail page (redesign); vendor and
  // personal keep the existing simpler detail page untouched.
  if (commitment.category === "civic") {
    return (
      <CivicDetailPage
        commitment={commitment}
        evidenceList={evidenceList}
        voteResults={voteResults}
        counts={{ news: 0, discussion: 0, related: 0 }}
      />
    );
  }

  const progress = calcTimeProgress(commitment.created_at, commitment.deadline);

  return (
    <div
      className="container"
      style={{ paddingTop: "24px", paddingBottom: "40px" }}
    >
      {/* Back link */}
      <Link
        href="/"
        style={{
          color: "var(--text-secondary)",
          textDecoration: "none",
          fontSize: "var(--font-caption)",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          marginBottom: "20px",
        }}
      >
        <ArrowLeft size={16} /> Back to Feed
      </Link>

      {/* Hero area — Design Doc §5.3 */}
      <div className="card" style={{ marginBottom: "20px", padding: "24px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: "16px",
          }}
        >
          <h1
            style={{
              fontSize: "var(--font-title)",
              fontWeight: 700,
              flex: 1,
            }}
          >
            {commitment.title}
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {commitment.is_public && (
              <span
                style={{
                  display: "flex", alignItems: "center", gap: "4px",
                  fontSize: "var(--font-caption)",
                  color: "var(--accent-primary)",
                  background: "rgba(var(--accent-primary-rgb, 99,102,241), 0.1)",
                  padding: "4px 10px",
                  borderRadius: "var(--radius-full, 999px)",
                  border: "1px solid rgba(var(--accent-primary-rgb, 99,102,241), 0.2)",
                }}
              >
                <Globe size={14} /> Public
              </span>
            )}
            <span
              className={`verdict-badge ${commitment.status}`}
              style={{
                animation: isResolved ? "verdictReveal 0.4s ease" : undefined,
                display: "flex",
                alignItems: "center",
                gap: "4px"
              }}
            >
              {isResolved ? (commitment.status === "met" ? <Check size={16} /> : commitment.status === "broken" ? <X size={16} /> : <Scale size={16} />) : ""}
              {getStatusLabel(commitment.status)}
            </span>
          </div>
        </div>

        {commitment.description && (
          <p
            style={{
              color: "var(--text-secondary)",
              marginBottom: "12px",
            }}
          >
            {commitment.description}
          </p>
        )}

        <div
          style={{
            background: "var(--bg-surface-raised)",
            borderRadius: "10px",
            padding: "12px 16px",
            marginBottom: "16px",
          }}
        >
          <div
            style={{
              fontSize: "var(--font-caption)",
              color: "var(--text-secondary)",
              marginBottom: "4px",
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            Verifiable Condition
          </div>
          <div style={{ color: "var(--accent-primary)" }}>
            {commitment.measurable_condition}
          </div>
        </div>

        {/* Countdown or verdict */}
        {!isResolved && (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "8px",
                fontSize: "var(--font-caption)",
                color: "var(--text-secondary)",
              }}
            >
              <span>
                {isPastDeadline
                  ? "Deadline passed"
                  : `Due ${formatRelativeTime(commitment.deadline)}`}
              </span>
              <span>{Math.round(progress)}% time elapsed</span>
            </div>
            <div className="progress-bar">
              <div
                className={`progress-bar-fill ${progress > 80 ? "warning" : "on-track"}`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </>
        )}

        <div
          style={{
            marginTop: "12px",
            fontSize: "var(--font-caption)",
            color: "var(--text-secondary)",
          }}
        >
          Created {formatDate(commitment.created_at)}
          {commitment.resolved_at &&
            ` · Resolved ${formatDate(commitment.resolved_at)}`}
        </div>
      </div>

      {/* Jury Pool section — for public commitments */}
      {commitment.is_public && juryPool && !isResolved && (
        <div className="card" style={{ marginBottom: "20px", padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <Users size={18} style={{ color: "var(--accent-primary)" }} />
                <h3 style={{ fontSize: "var(--font-body)", fontWeight: 600, margin: 0 }}>Jury Pool</h3>
              </div>
              <p style={{ fontSize: "var(--font-caption)", color: "var(--text-secondary)", margin: 0 }}>
                {juryPool.pool_size} joined{juryPool.target_size ? ` / ${juryPool.target_size} target` : ""}
              </p>
            </div>
            {user && !juryPool.user_has_joined && commitment.author_id !== user.id && (
              <button
                className="btn btn-primary"
                style={{ fontSize: "var(--font-caption)", padding: "8px 16px" }}
                disabled={joiningPool}
                onClick={async () => {
                  if (!user) return;
                  setJoiningPool(true);
                  try {
                    const result = await joinJuryPool(id, user.token);
                    setJuryPool({ ...juryPool, pool_size: result.pool_size, user_has_joined: true });
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Failed to join pool");
                  } finally {
                    setJoiningPool(false);
                  }
                }}
              >
                {joiningPool ? "Joining..." : "Join Jury Pool"}
              </button>
            )}
            {juryPool.user_has_joined && (
              <span style={{ fontSize: "var(--font-caption)", color: "var(--accent-verified, var(--accent-primary))" }}>
                <Check size={14} style={{ verticalAlign: "middle" }} /> Joined
              </span>
            )}
          </div>
        </div>
      )}

      {/* Vote Results — visible after resolution */}
      {isResolved && voteResults.length > 0 && (
        <div className="card" style={{ marginBottom: "20px", padding: "20px" }}>
          <h3 style={{ fontSize: "var(--font-subtitle)", fontWeight: 600, marginBottom: "16px" }}>Vote Results</h3>
          {(() => {
            const met = voteResults.filter(v => v.vote === "met").length;
            const broken = voteResults.filter(v => v.vote === "broken").length;
            const abstain = voteResults.filter(v => v.vote === "abstain").length;
            const total = voteResults.length;
            return (
              <div>
                <div style={{ display: "flex", gap: "16px", marginBottom: "12px", fontSize: "var(--font-caption)" }}>
                  <span style={{ color: "var(--accent-verified, #22c55e)" }}>Met: {met}</span>
                  <span style={{ color: "var(--accent-broken, #ef4444)" }}>Broken: {broken}</span>
                  <span style={{ color: "var(--text-secondary)" }}>Abstain: {abstain}</span>
                </div>
                <div style={{ display: "flex", height: "8px", borderRadius: "4px", overflow: "hidden", background: "var(--border-subtle)" }}>
                  {met > 0 && <div style={{ width: `${(met/total)*100}%`, background: "var(--accent-verified, #22c55e)" }} />}
                  {broken > 0 && <div style={{ width: `${(broken/total)*100}%`, background: "var(--accent-broken, #ef4444)" }} />}
                  {abstain > 0 && <div style={{ width: `${(abstain/total)*100}%`, background: "var(--text-secondary)" }} />}
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Jury Voting section — Design Doc §5.4 */}
      {isVerification && !voted && (
        <div className="card" style={{ marginBottom: "20px" }}>
          {/* AI summary card */}
          <div className="ai-summary" style={{ marginBottom: "20px" }}>
            <span className="ai-summary-label">AI Summary</span>
            <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-body)" }}>
              Evidence has been submitted for this commitment. Review the evidence
              below and cast your vote on whether the commitment was met, broken,
              or if you'd like to abstain.
            </p>
          </div>

          <h3
            style={{
              fontSize: "var(--font-subtitle)",
              fontWeight: 600,
              marginBottom: "16px",
            }}
          >
            Cast Your Vote
          </h3>
          <VoteButtons onVote={handleVote} />

          {/* Optional reason — collapsed by default (Design Doc §5.4) */}
          <div style={{ marginTop: "16px" }}>
            <button
              onClick={() => setShowVoting(!showVoting)}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "var(--font-caption)",
                display: "flex",
                alignItems: "center",
                gap: "4px"
              }}
            >
              {showVoting ? <><ChevronDown size={14} /> Hide reason</> : <><ChevronRight size={14} /> Add reason (optional)</>}
            </button>
            {showVoting && (
              <textarea
                className="input"
                placeholder="Explain your vote (optional)"
                value={voteReason}
                onChange={(e) => setVoteReason(e.target.value)}
                style={{ marginTop: "8px", minHeight: "60px" }}
              />
            )}
          </div>
        </div>
      )}

      {/* Post-vote state — Design Doc §5.4 */}
      {voted && (
        <div
          className="card"
          style={{
            marginBottom: "20px",
            textAlign: "center",
            padding: "24px",
          }}
        >
          <div
            style={{
              fontSize: "var(--font-subtitle)",
              color: "var(--accent-verified)",
              marginBottom: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px"
            }}
          >
            <Check size={20} /> Vote Recorded
          </div>
          <p style={{ color: "var(--text-secondary)" }}>
            Waiting on other jurors. Results will be revealed after all votes are
            in or the voting window closes.
          </p>
        </div>
      )}

      {/* Evidence Timeline — Design Doc §5.3 */}
      <div style={{ marginBottom: "20px" }}>
        <h3
          style={{
            fontSize: "var(--font-subtitle)",
            fontWeight: 600,
            marginBottom: "16px",
          }}
        >
          Evidence Timeline
        </h3>

        {evidenceList.length === 0 ? (
          <div
            style={{
              color: "var(--text-secondary)",
              textAlign: "center",
              padding: "32px",
            }}
          >
            No evidence submitted yet
          </div>
        ) : (
          <div className="timeline">
            {evidenceList.map((ev) => (
              <div key={ev.id} className="timeline-item animate-in">
                <div className="card" style={{ padding: "14px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "8px",
                      fontSize: "var(--font-caption)",
                    }}
                  >
                    <span style={{ color: "var(--accent-primary)" }}>
                      {ev.type.toUpperCase()}
                    </span>
                    <span style={{ color: "var(--text-secondary)" }}>
                      {formatDate(ev.submitted_at)}
                    </span>
                  </div>
                  <p>{ev.content}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Send Evidence CTA — persists until deadline (Design Doc §5.3) */}
      {!isResolved && !isPastDeadline && (
        <div>
          {showEvidenceForm ? (
            <div className="card-raised animate-in">
              <h4
                style={{
                  fontSize: "var(--font-body)",
                  fontWeight: 600,
                  marginBottom: "12px",
                }}
              >
                Submit Evidence
              </h4>
              <div style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
                {["text", "link", "image"].map((t) => (
                  <button
                    key={t}
                    className={`pill ${evidenceType === t ? "active" : ""}`}
                    onClick={() => setEvidenceType(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <textarea
                className="input"
                placeholder={
                  evidenceType === "link"
                    ? "Paste a URL..."
                    : evidenceType === "image"
                      ? "Paste image URL or path..."
                      : "Describe your evidence..."
                }
                value={evidenceContent}
                onChange={(e) => setEvidenceContent(e.target.value)}
              />
              {error && (
                <p
                  style={{
                    color: "var(--accent-broken)",
                    fontSize: "var(--font-caption)",
                    marginTop: "8px",
                  }}
                >
                  {error}
                </p>
              )}
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  marginTop: "12px",
                  justifyContent: "flex-end",
                }}
              >
                <button
                  className="btn btn-outline"
                  onClick={() => setShowEvidenceForm(false)}
                  style={{ fontSize: "var(--font-caption)", padding: "8px 16px" }}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleSubmitEvidence}
                  disabled={submitting || !evidenceContent.trim()}
                  style={{ fontSize: "var(--font-caption)", padding: "8px 16px" }}
                >
                  {submitting ? "Submitting..." : "Submit"}
                </button>
              </div>
            </div>
          ) : (
            <button
              className="btn btn-primary"
              onClick={() => setShowEvidenceForm(true)}
              style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}
            >
              <Paperclip size={18} /> Send Evidence
            </button>
          )}
        </div>
      )}

      {/* After deadline, in verification — show voting closes countdown */}
      {isVerification && (
        <div
          style={{
            textAlign: "center",
            padding: "16px",
            color: "var(--text-secondary)",
            fontSize: "var(--font-caption)",
          }}
        >
          Voting window closes in 72h from deadline
        </div>
      )}
    </div>
  );
}

function getDemoCommitment(id: string): Commitment {
  return {
    id,
    category: "personal",
    author_id: "demo-user",
    title: "Complete 90 LeetCode problems",
    description: "Solve 3 problems per day for 30 days",
    measurable_condition:
      "Solve exactly 90 LeetCode problems by the deadline, tracked via LeetCode profile screenshot",
    deadline: new Date(
      Date.now() + 15 * 24 * 60 * 60 * 1000
    ).toISOString(),
    status: "evidence_submitted",
    content_hash: "demo",
    created_at: new Date(
      Date.now() - 5 * 24 * 60 * 60 * 1000
    ).toISOString(),
    resolved_at: null,
    onchain_tx_hash: null,
    is_public: false,
    jury_pool_size: null,
    juror_count: 3,
    evidence_count: 2,
  };
}
