"use client";

/**
 * Home / Recent Commitments feed — redesign stages 1–3.
 * Hero banner (stage 2) + Recent Commitments section with the new
 * image-left card variant (stage 3).
 */

import { useState, useEffect } from "react";
import { type Commitment } from "@/lib/api";
import { CommitmentFeedCard } from "@/components/CommitmentFeedCard";
import { getDemoCommitments } from "@/components/CommitmentListPage";
import { HeroBanner } from "@/components/HeroBanner";

/**
 * Filter row per the reference: "All" is a filled pill; the rest are text
 * tabs. Civic/Vendors filter by category; the remainder by status.
 */
const FEED_FILTERS = [
  { key: "all", label: "All" },
  { key: "civic", label: "Civic" },
  { key: "vendor", label: "Vendors" },
  { key: "open", label: "Open" },
  { key: "evidence_submitted", label: "Awaiting Evidence" },
  { key: "in_verification", label: "In Verification" },
  { key: "resolved", label: "Resolved" },
];

export default function HomePage() {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [activeFilter, setActiveFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const { listCommitments } = await import("@/lib/api");

        const isCategory = ["civic", "vendor"].includes(activeFilter);
        const isStatus = !["all", "resolved"].includes(activeFilter);

        const data = await listCommitments({
          ...(isCategory ? { category: activeFilter } : {}),
          ...(isStatus ? { status: activeFilter } : {}),
        });

        let filtered = data.commitments;
        if (activeFilter === "resolved") {
          filtered = filtered.filter((c) =>
            ["met", "broken", "disputed"].includes(c.status)
          );
        }
        setCommitments(filtered);
      } catch {
        // API unavailable → demo data, filtered to match the active tab
        const demo = getDemoCommitments();
        let filtered = demo;
        if (activeFilter === "resolved") {
          filtered = demo.filter((c) => ["met", "broken", "disputed"].includes(c.status));
        } else if (["civic", "vendor"].includes(activeFilter)) {
          filtered = demo.filter((c) => c.category === activeFilter);
        } else if (activeFilter !== "all") {
          filtered = demo.filter((c) => c.status === activeFilter);
        }
        setCommitments(filtered);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [activeFilter]);

  return (
    <div className="shell-content" style={{ maxWidth: "860px" }}>
      <HeroBanner />

      {/* Recent Commitments header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "14px",
        }}
      >
        <h2 style={{ fontSize: "var(--font-title)", fontWeight: 700, margin: 0 }}>
          Recent Commitments
        </h2>
        <a
          href="/explore"
          style={{
            color: "var(--accent-primary)",
            textDecoration: "none",
            fontSize: "var(--font-caption)",
            fontWeight: 600,
          }}
        >
          View all →
        </a>
      </div>

      {/* Filter row: All as filled pill, rest as text tabs (existing
          status-tab component restyled by sizing only) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "4px",
          marginBottom: "20px",
          flexWrap: "wrap",
        }}
      >
        {FEED_FILTERS.map((f) => {
          const active = activeFilter === f.key;
          if (f.key === "all") {
            return (
              <button
                key={f.key}
                className={`pill ${active ? "active" : ""}`}
                onClick={() => setActiveFilter(f.key)}
                style={{ padding: "7px 18px" }}
              >
                {f.label}
              </button>
            );
          }
          return (
            <button
              key={f.key}
              className={`status-tab ${active ? "active" : ""}`}
              onClick={() => setActiveFilter(f.key)}
              style={{
                padding: "7px 12px",
                borderRadius: "100px",
                background: active ? "rgba(255, 107, 53, 0.12)" : "transparent",
                color: active ? "var(--accent-primary)" : "var(--text-secondary)",
              }}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Feed */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-secondary)" }}>
          Loading commitments...
        </div>
      ) : commitments.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            color: "var(--text-secondary)",
          }}
        >
          Nothing here for this filter yet.
        </div>
      ) : (
        commitments.map((c) => <CommitmentFeedCard key={c.id} commitment={c} />)
      )}
    </div>
  );
}
