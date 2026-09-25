"use client";

/**
 * Reusable commitments list — shared by Civic, Vendors, Nearby,
 * My Commitments pages. Same data logic as the Home feed, parameterized
 * by category ("" = all categories).
 */

import { useState, useEffect } from "react";
import { listCommitments, type Commitment } from "@/lib/api";
import { CommitmentCard } from "./CommitmentCard";

const STATUS_TABS = [
  { key: "all", label: "All" },
  { key: "open", label: "Open" },
  { key: "evidence_submitted", label: "Awaiting Evidence" },
  { key: "in_verification", label: "In Verification" },
  { key: "resolved", label: "Resolved" },
];

export function CommitmentListPage({ category }: { category: string }) {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [activeTab, setActiveTab] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const statusParam =
          activeTab === "all" || activeTab === "resolved" ? undefined : activeTab;
        const data = await listCommitments({
          ...(statusParam ? { status: statusParam } : {}),
          ...(category ? { category } : {}),
        });
        let filtered = data.commitments;
        if (activeTab === "resolved") {
          filtered = filtered.filter((c) =>
            ["met", "broken", "disputed"].includes(c.status)
          );
        }
        setCommitments(filtered);
      } catch {
        setCommitments(
          getDemoCommitments().filter((c) => !category || c.category === category)
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activeTab, category]);

  return (
    <>
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
            textAlign: "center",
            padding: "60px 20px",
            color: "var(--text-secondary)",
          }}
        >
          <p
            style={{
              fontSize: "var(--font-subtitle)",
              marginBottom: "8px",
              color: "var(--text-primary)",
            }}
          >
            Nothing here yet
          </p>
          <p style={{ margin: 0 }}>
            {category === "civic"
              ? "Log a promise from a local official to get your ward's ledger started."
              : category === "vendor"
                ? "Log a contractor's job promise to start their track record."
                : "Create your first commitment to get started."}
          </p>
        </div>
      ) : (
        commitments.map((c) => <CommitmentCard key={c.id} commitment={c} />)
      )}
    </>
  );
}

/** Demo data for offline/API-down fallback — all three categories. */
export function getDemoCommitments(): Commitment[] {
  const now = new Date();
  const day = 24 * 60 * 60 * 1000;

  const personal: Commitment[] = [
    {
      id: "demo-1",
      category: "personal",
      author_id: "demo-user",
      title: "Complete 90 LeetCode problems",
      description: "Solve 3 problems per day for 30 days",
      measurable_condition:
        "Solve exactly 90 LeetCode problems by the deadline, tracked via LeetCode profile",
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
      vote_count: 0,
    },
    {
      id: "demo-2",
      category: "personal",
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
      vote_count: 0,
    },
    {
      id: "demo-3",
      category: "personal",
      author_id: "demo-user-2",
      title: "Run a half marathon under 2 hours",
      description: null,
      measurable_condition:
        "Complete a half marathon (21.1km) in under 2:00:00, verified by official race results",
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
      vote_count: 0,
    },
  ];

  const civic: Commitment[] = [
    {
      id: "demo-c1",
      category: "civic",
      author_id: "demo-official",
      title: "Resurface Linking Road (Ward 104)",
      description: "Promised at the ward citizen meeting",
      measurable_condition: '"This road will be resurfaced before March 2026."',
      deadline: new Date(now.getTime() + 72 * day).toISOString(),
      status: "open",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 12 * day).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: true,
      jury_pool_size: null,
      juror_count: 48,
      evidence_count: 12,
      vote_count: 14,
      official_name: "Milind Deora",
      official_role: "Representative",
      ward: "Ward 104, Mumbai",
      source_type: "sourced",
      source_citation: "https://timesofindia.indiatimes.com/city/mumbai/linking-road",
    },
    {
      id: "demo-c2",
      category: "civic",
      author_id: "demo-official-2",
      title: "Clear monsoon drain blockage (Lane 3)",
      description: null,
      measurable_condition: '"All drains in Lane 3 to be cleared before monsoon."',
      deadline: new Date(now.getTime() - 15 * day).toISOString(),
      status: "evidence_submitted",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 40 * day).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: true,
      jury_pool_size: null,
      juror_count: 23,
      evidence_count: 5,
      vote_count: 3,
      official_name: "Ward 104 Civic Office",
      official_role: "Municipal office",
      ward: "Bandra West, Mumbai",
      source_type: "crowd",
      source_citation: null,
    },
  ];

  const vendor: Commitment[] = [
    {
      id: "demo-v1",
      category: "vendor",
      author_id: "demo-contractor",
      title: "Kitchen Renovation – 2 BHK",
      description: "Modular kitchen, full civil + electrical",
      measurable_condition: '"Complete modular kitchen in 6 weeks for ₹2.4L."',
      deadline: new Date(now.getTime() + 6 * day).toISOString(),
      status: "in_verification",
      content_hash: "demo",
      created_at: new Date(now.getTime() - 40 * day).toISOString(),
      resolved_at: null,
      onchain_tx_hash: null,
      is_public: false,
      jury_pool_size: null,
      juror_count: 2,
      evidence_count: 8,
      vote_count: 1,
      official_name: "Sharma Interiors",
      official_role: "Contractor",
      ward: null,
      source_type: null,
      source_citation: null,
    },
  ];

  return [...personal, ...civic, ...vendor];
}
