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

/** Demo data for when the API is not available */
function getDemoCommitments(): Commitment[] {
  const now = new Date();
  const day = 24 * 60 * 60 * 1000;
  return [
    // ── Personal ──
    {
      id: "demo-1",
      author_id: "demo-user",
      title: "Complete 90 LeetCode problems",
      description: "Solve 3 problems per day for 30 days",
      measurable_condition: "Solve exactly 90 LeetCode problems by the deadline, tracked via LeetCode profile",
      deadline: new Date(now.getTime() + 15 * day).toISOString(),
      status: "open",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 5 * day).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 3,
      evidence_count: 2,
      category: "personal",
      vote_count: 0,
    },
    {
      id: "demo-2",
      author_id: "demo-user",
      title: "Ship MVP by end of sprint",
      description: "Complete all milestone 1 tasks",
      measurable_condition: "All 12 user stories in Jira sprint board marked as Done",
      deadline: new Date(now.getTime() + 3 * day).toISOString(),
      status: "evidence_submitted",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 10 * day).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 2,
      evidence_count: 5,
      category: "personal",
      vote_count: 0,
    },
    {
      id: "demo-3",
      author_id: "demo-user-2",
      title: "Run a half marathon under 2 hours",
      description: null,
      measurable_condition: "Complete a half marathon (21.1km) in under 2:00:00, verified by official race results",
      deadline: new Date(now.getTime() - 2 * day).toISOString(),
      status: "met",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 30 * day).toISOString(),
      resolved_at: new Date(now.getTime() - 1 * day).toISOString(),
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 4,
      evidence_count: 3,
      category: "personal",
      vote_count: 0,
    },
    // ── Civic (India PRD §5) ──
    {
      id: "demo-c1",
      author_id: "demo-official",
      title: "Ward road resurfacing by March",
      description: "Promised at the L-Ward citizen meeting",
      measurable_condition: "The 1.2km stretch from Matunga station to the market is resurfaced and pothole-free, verified by site photos",
      deadline: new Date(now.getTime() + 120 * day).toISOString(),
      status: "open",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 12 * day).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: true,
      jury_pool_size: null,
      juror_count: 0,
      evidence_count: 1,
      category: "civic",
      official_name: "Sunita Rao",
      official_role: "Corporator, L-Ward",
      ward: "L-Ward, Mumbai",
      source_type: "sourced",
      source_citation: "https://timesofindia.indiatimes.com/city/mumbai/ward-150-citizen-meeting",
      vote_count: 14,
    },
    {
      id: "demo-c2",
      author_id: "demo-official",
      title: "24/7 water supply for Sector 8 pipeline",
      description: null,
      measurable_condition: "Continuous water supply reported by at least 10 households in Sector 8 for 30 consecutive days",
      deadline: new Date(now.getTime() + 200 * day).toISOString(),
      status: "in_verification",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 90 * day).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: true,
      jury_pool_size: null,
      juror_count: 0,
      evidence_count: 6,
      category: "civic",
      official_name: "Sunita Rao",
      official_role: "Corporator, L-Ward",
      ward: "L-Ward, Mumbai",
      source_type: "crowd",
      source_citation: null,
      vote_count: 7,
    },
    {
      id: "demo-c3",
      author_id: "demo-mla",
      title: "New municipal school building by June",
      description: "Manifesto commitment from the 2026 election",
      measurable_condition: "The new 12-classroom school building on Ambedkar Road has an occupancy certificate issued by June 30",
      deadline: new Date(now.getTime() - 10 * day).toISOString(),
      status: "disputed",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 380 * day).toISOString(),
      resolved_at: new Date(now.getTime() - 8 * day).toISOString(),
      onchain_tx_hash: null,
      is_public: true,
      jury_pool_size: null,
      juror_count: 0,
      evidence_count: 9,
      category: "civic",
      official_name: "Vikram Deshmukh",
      official_role: "MLA, Dadar constituency",
      ward: "Dadar, Mumbai",
      source_type: "sourced",
      source_citation: "Party manifesto 2026, page 14",
      vote_count: 23,
    },
    // ── Vendors (India PRD §6) ──
    {
      id: "demo-v1",
      author_id: "demo-contractor",
      title: "Kitchen renovation in 6 weeks for ₹2.8L",
      description: "Modular kitchen, full civil + electrical work",
      measurable_condition: "Renovation complete with all agreed scope items installed, photographed, and signed off by the customer within 6 weeks",
      deadline: new Date(now.getTime() + 30 * day).toISOString(),
      status: "open",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 12 * day).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 1,
      evidence_count: 3,
      category: "vendor",
      official_name: "Sharma Interiors",
      official_role: "Contractor",
      ward: null,
      source_type: null,
      source_citation: null,
      vote_count: 0,
    },
    {
      id: "demo-v2",
      author_id: "demo-contractor2",
      title: "Wedding catering for 400 guests, on time",
      description: null,
      measurable_condition: "All 400 meals served within the agreed 90-minute window with the agreed menu, confirmed by the customer",
      deadline: new Date(now.getTime() - 4 * day).toISOString(),
      status: "met",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 40 * day).toISOString(),
      resolved_at: new Date(now.getTime() - 3 * day).toISOString(),
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 2,
      evidence_count: 5,
      category: "vendor",
      official_name: "Gupta Caterers",
      official_role: "Wedding vendor",
      ward: null,
      source_type: null,
      source_citation: null,
      vote_count: 2,
    },
  ];
}
