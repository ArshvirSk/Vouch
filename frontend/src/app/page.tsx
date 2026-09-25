"use client";

/**
 * Home / Commitments Feed — Design Doc §5.1.
 * Status strip tabs, category pill, commitment cards.
 */

import { useState, useEffect } from "react";
import { listCommitments, type Commitment } from "@/lib/api";
import { CommitmentCard } from "@/components/CommitmentCard";

const STATUS_TABS = [
  { key: "all", label: "All" },
  { key: "open", label: "Open" },
  { key: "evidence_submitted", label: "Awaiting Evidence" },
  { key: "in_verification", label: "In Verification" },
  { key: "resolved", label: "Resolved" },
];

export default function HomePage() {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [activeTab, setActiveTab] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const statusParam =
          activeTab === "all"
            ? undefined
            : activeTab === "resolved"
              ? undefined // We'll filter client-side for resolved
              : activeTab;
        const data = await listCommitments(
          statusParam ? { status: statusParam } : undefined
        );
        let filtered = data.commitments;
        if (activeTab === "resolved") {
          filtered = filtered.filter((c) =>
            ["met", "broken", "disputed"].includes(c.status)
          );
        }
        setCommitments(filtered);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load commitments");
        // Use demo data if API is not available
        setCommitments(getDemoCommitments());
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activeTab]);

  return (
    <div className="container" style={{ paddingTop: "24px", paddingBottom: "40px" }}>
      {/* Greeting */}
      <h1
        style={{
          fontSize: "var(--font-display)",
          fontWeight: 700,
          marginBottom: "4px",
        }}
      >
        Commitments
      </h1>
      <p
        style={{
          color: "var(--text-secondary)",
          marginBottom: "24px",
          fontSize: "var(--font-body)",
        }}
      >
        Track promises, submit evidence, verify together.
      </p>

      {/* Status strip — Design Doc §5.1 */}
      <div className="status-strip" style={{ marginBottom: "16px" }}>
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            className={`status-tab ${activeTab === tab.key ? "active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Category pill — Design Doc §5.1 (MVP: Personal only) */}
      <div style={{ marginBottom: "20px" }}>
        <span className="pill active">Personal</span>
      </div>

      {/* Commitments list */}
      {loading ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 0",
            color: "var(--text-secondary)",
          }}
        >
          Loading commitments...
        </div>
      ) : commitments.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
            padding: "60px 20px",
            color: "var(--text-secondary)",
          }}
        >
          <p style={{ fontSize: "var(--font-subtitle)", marginBottom: "8px", color: "var(--text-primary)" }}>
            No commitments yet
          </p>
          <p style={{ margin: 0 }}>Create your first commitment to get started.</p>
        </div>
      ) : (
        commitments.map((c) => <CommitmentCard key={c.id} commitment={c} />)
      )}
    </div>
  );
}

/** Demo data for when the API is not available */
function getDemoCommitments(): Commitment[] {
  const now = new Date();
  return [
    {
      id: "demo-1",
      author_id: "demo-user",
      title: "Complete 90 LeetCode problems",
      description: "Solve 3 problems per day for 30 days",
      measurable_condition: "Solve exactly 90 LeetCode problems by the deadline, tracked via LeetCode profile",
      deadline: new Date(now.getTime() + 15 * 24 * 60 * 60 * 1000).toISOString(),
      status: "open",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 3,
      evidence_count: 2,
    },
    {
      id: "demo-2",
      author_id: "demo-user",
      title: "Ship MVP by end of sprint",
      description: "Complete all milestone 1 tasks",
      measurable_condition: "All 12 user stories in Jira sprint board marked as Done",
      deadline: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
      status: "evidence_submitted",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 2,
      evidence_count: 5,
    },
    {
      id: "demo-3",
      author_id: "demo-user-2",
      title: "Run a half marathon under 2 hours",
      description: null,
      measurable_condition: "Complete a half marathon (21.1km) in under 2:00:00, verified by official race results",
      deadline: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      status: "met",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      resolved_at: new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000).toISOString(),
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 4,
      evidence_count: 3,
    },
    {
      id: "demo-4",
      author_id: "demo-user-3",
      title: "Read 12 books this quarter",
      description: "One book per week minimum",
      measurable_condition: "Read and summarize 12 complete books, summaries shared in weekly check-ins",
      deadline: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      status: "broken",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000).toISOString(),
      resolved_at: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 3,
      evidence_count: 4,
    },
    {
      id: "demo-5",
      author_id: "demo-user",
      title: "Launch personal blog with 5 articles",
      description: null,
      measurable_condition: "Blog live at custom domain with 5 published articles, each 1000+ words",
      deadline: new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      status: "in_verification",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 20 * 24 * 60 * 60 * 1000).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 5,
      evidence_count: 6,
    },
  ];
}
