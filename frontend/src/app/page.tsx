"use client";

/**
 * Home / Commitments Feed — Design Doc §5.1, now inside the new app shell.
 * Status strip tabs, category pills (India PRD §4), commitment cards.
 */

import { useState, useEffect } from "react";
import { type Commitment } from "@/lib/api";
import { CommitmentCard } from "@/components/CommitmentCard";
import { getDemoCommitments } from "@/components/CommitmentListPage";

const STATUS_TABS = [
  { key: "all", label: "All" },
  { key: "open", label: "Open" },
  { key: "evidence_submitted", label: "Awaiting Evidence" },
  { key: "in_verification", label: "In Verification" },
  { key: "resolved", label: "Resolved" },
];

/** Category pills — India PRD §4 (Personal / Civic / Vendors) */
const CATEGORY_TABS = [
  { key: "personal", label: "Personal" },
  { key: "civic", label: "Civic" },
  { key: "vendor", label: "Vendors" },
];

export default function HomePage() {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [activeTab, setActiveTab] = useState("all");
  const [activeCategory, setActiveCategory] = useState("personal");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const { listCommitments } = await import("@/lib/api");
        const statusParam =
          activeTab === "all"
            ? undefined
            : activeTab === "resolved"
              ? undefined // We'll filter client-side for resolved
              : activeTab;
        const data = await listCommitments({
          ...(statusParam ? { status: statusParam } : {}),
          category: activeCategory,
        });
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
        setCommitments(
          getDemoCommitments().filter((c) => c.category === activeCategory)
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activeTab, activeCategory]);

  return (
    <div className="shell-content">
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

      {/* Category pills — India PRD §4: Personal / Civic / Vendors.
          Same pill component and visual treatment as before, now wired to
          actually filter the feed. */}
      <div style={{ marginBottom: "20px", display: "flex", gap: "8px" }}>
        {CATEGORY_TABS.map((cat) => (
          <button
            key={cat.key}
            className={`pill ${activeCategory === cat.key ? "active" : ""}`}
            onClick={() => setActiveCategory(cat.key)}
          >
            {cat.label}
          </button>
        ))}
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
            No {activeCategory === "personal" ? "commitments" : `${activeCategory} commitments`} yet
          </p>
          <p style={{ margin: 0 }}>
            {activeCategory === "personal"
              ? "Create your first commitment to get started."
              : activeCategory === "civic"
                ? "Log a promise from a local official to get your ward's ledger started."
                : "Log a contractor's job promise to start their track record."}
          </p>
        </div>
      ) : (
        commitments.map((c) => <CommitmentCard key={c.id} commitment={c} />)
      )}
    </div>
  );
}
