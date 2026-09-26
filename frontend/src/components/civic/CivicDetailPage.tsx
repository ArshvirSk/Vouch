"use client";

/**
 * CivicDetailPage — enriched detail page for CIVIC commitments only
 * (reference: redesign screenshot). Vendor/personal keep the existing page.
 *
 * Stage 1 ships the header + tab row; tab panels land in later stages:
 *   Overview      → Stage 2 (verdict charts)
 *   News          → Stage 3 (auto-linked external content)
 *   Evidence      → existing evidence timeline, restyled here
 *   Discussion    → Stage 6 (community notes)
 *   Jurors        → juror list
 *   Related       → Stage 5 (similar commitments)
 *
 * All colors come from existing CSS tokens — no retheme.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ChevronRight } from "lucide-react";
import type { Commitment, Evidence, Vote, VerdictHistoryData } from "@/lib/api";
import { getVerdictHistory } from "@/lib/api";
import { CivicDetailHeader } from "./CivicDetailHeader";
import { VerdictOverview } from "./VerdictCharts";

export interface CivicCounts {
  news: number;
  discussion: number;
  related: number;
}

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "news", label: "News & Updates" },
  { key: "evidence", label: "Evidence" },
  { key: "discussion", label: "Discussion" },
  { key: "jurors", label: "Jurors" },
  { key: "related", label: "Related" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export function CivicDetailPage({
  commitment,
  evidenceList,
  voteResults,
  counts,
}: {
  commitment: Commitment;
  evidenceList: Evidence[];
  voteResults: Vote[];
  counts: CivicCounts;
}) {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  const tabCount = (key: TabKey): number | null => {
    switch (key) {
      case "news":
        return counts.news || null;
      case "evidence":
        return evidenceList.length || null;
      case "discussion":
        return counts.discussion || null;
      case "jurors":
        return commitment.juror_count || null;
      case "related":
        return counts.related || null;
      default:
        return null;
    }
  };

  return (
    <div
      style={{
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "24px 28px 40px",
        display: "flex",
        gap: "28px",
        alignItems: "flex-start",
      }}
    >
      {/* ── Main column ──────────────────────────────────────────── */}
      <div style={{ flex: "1 1 0%", minWidth: 0 }}>
        <Link
          href="/"
          style={{
            color: "var(--text-secondary)",
            textDecoration: "none",
            fontSize: "var(--font-caption)",
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            marginBottom: "16px",
          }}
        >
          <ArrowLeft size={15} /> Back to Feed
        </Link>

        <CivicDetailHeader commitment={commitment} evidenceList={evidenceList} />

        {/* ── Tab row ────────────────────────────────────────────── */}
        <div
          style={{
            display: "flex",
            gap: "4px",
            borderBottom: "1px solid var(--border-subtle)",
            marginBottom: "20px",
            overflowX: "auto",
          }}
        >
          {TABS.map((t) => {
            const n = tabCount(t.key);
            const active = activeTab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                style={{
                  background: "none",
                  border: "none",
                  borderBottom: active ? "2px solid var(--accent-primary)" : "2px solid transparent",
                  color: active ? "var(--text-primary)" : "var(--text-secondary)",
                  fontWeight: active ? 600 : 500,
                  fontSize: "var(--font-caption)",
                  padding: "10px 14px",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  marginBottom: "-1px",
                }}
              >
                {t.label}
                {n != null && n > 0 ? ` (${n})` : ""}
              </button>
            );
          })}
        </div>

        {/* ── Tab panels ─────────────────────────────────────────── */}
        {activeTab === "overview" && <OverviewPanel voteResults={voteResults} commitment={commitment} />}
        {activeTab === "news" && <ComingSoon label="News & Updates lands in Stage 3" />}
        {activeTab === "evidence" && <EvidencePanel evidenceList={evidenceList} />}
        {activeTab === "discussion" && <ComingSoon label="Discussion opens in Stage 6" />}
        {activeTab === "jurors" && <JurorsPanel count={commitment.juror_count ?? 0} />}
        {activeTab === "related" && <ComingSoon label="Related commitments land in Stage 5" />}
      </div>

      {/* ── Right rail — Stages 4–6 mount here ───────────────────── */}
      <aside style={{ width: "300px", flexShrink: 0, display: "none" }} aria-hidden />
    </div>
  );
}

function ComingSoon({ label }: { label: string }) {
  return (
    <div
      style={{
        textAlign: "center",
        padding: "48px 20px",
        color: "var(--text-secondary)",
        border: "1px dashed var(--border-subtle)",
        borderRadius: "12px",
        fontSize: "var(--font-caption)",
      }}
    >
      {label}
    </div>
  );
}

/** Overview tab — Stage 2: verdict-over-time + current-verdict charts. */
function OverviewPanel({ voteResults, commitment }: { voteResults: Vote[]; commitment: Commitment }) {
  const [history, setHistory] = useState<VerdictHistoryData | null>(null);

  useEffect(() => {
    let cancelled = false;
    getVerdictHistory(commitment.id)
      .then((d) => {
        if (!cancelled) setHistory(d);
      })
      .catch(() => {
        if (!cancelled) setHistory(null);
      });
    return () => {
      cancelled = true;
    };
  }, [commitment.id]);

  return (
    <VerdictOverview history={history} votes={voteResults} jurorCount={commitment.juror_count ?? 0} />
  );
}

function EvidencePanel({ evidenceList }: { evidenceList: Evidence[] }) {
  if (evidenceList.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "40px", color: "var(--text-secondary)" }}>
        No evidence submitted yet
      </div>
    );
  }
  return (
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
              <span style={{ color: "var(--accent-primary)", display: "inline-flex", alignItems: "center", gap: "6px" }}>
                {ev.type.toUpperCase()}
                {ev.phase && (
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      padding: "2px 8px",
                      borderRadius: "100px",
                      background: "var(--bg-surface-raised)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--text-secondary)",
                      textTransform: "uppercase",
                    }}
                  >
                    {ev.phase}
                  </span>
                )}
              </span>
              <span style={{ color: "var(--text-secondary)" }}>{new Date(ev.submitted_at).toLocaleDateString()}</span>
            </div>
            {ev.type === "image" && /^https?:\/\//.test(ev.content) && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={ev.content}
                alt="Evidence"
                style={{ width: "100%", maxHeight: "260px", objectFit: "cover", borderRadius: "8px", marginBottom: "10px" }}
              />
            )}
            <p style={{ margin: 0 }}>{ev.content}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function JurorsPanel({ count }: { count: number }) {
  return (
    <div style={{ textAlign: "center", padding: "40px", color: "var(--text-secondary)" }}>
      {count > 0
        ? `${count} jurors on the open ward jury — full roster view is part of a later stage.`
        : "No jurors assigned yet."}
      <div style={{ marginTop: "8px", display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--accent-primary)" }}>
        View juror activity <ChevronRight size={13} />
      </div>
    </div>
  );
}
