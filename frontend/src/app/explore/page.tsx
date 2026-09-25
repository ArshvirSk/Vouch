"use client";

/**
 * Explore Page — Public commitments feed.
 * Uses the project's vanilla CSS design system.
 */

import { useState, useEffect } from "react";
import { listCommitments, type Commitment } from "@/lib/api";
import { CommitmentCard } from "@/components/CommitmentCard";
import { Globe, TrendingUp, Users } from "lucide-react";

export default function ExplorePage() {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await listCommitments();
        setCommitments(data.commitments.filter((c) => c.is_public));
      } catch {
        setCommitments([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="container" style={{ paddingTop: "24px", paddingBottom: "40px" }}>
      {/* Header */}
      <div style={{ marginBottom: "32px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
          <Globe size={28} style={{ color: "var(--accent-primary)" }} />
          <h1
            style={{
              fontSize: "var(--font-display)",
              fontWeight: 700,
              margin: 0,
            }}
          >
            Explore Public Pledges
          </h1>
        </div>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "var(--font-body)",
            maxWidth: "600px",
          }}
        >
          Hold public figures and organizations accountable. Join jury pools and
          help verify high-stakes commitments.
        </p>
      </div>

      {/* Stats bar */}
      <div
        style={{
          display: "flex",
          gap: "24px",
          marginBottom: "24px",
          padding: "16px 20px",
          background: "var(--surface-elevated)",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <TrendingUp size={16} style={{ color: "var(--accent-primary)" }} />
          <span style={{ fontSize: "var(--font-caption)", color: "var(--text-secondary)" }}>
            {commitments.length} public pledge{commitments.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Users size={16} style={{ color: "var(--accent-secondary, var(--accent-primary))" }} />
          <span style={{ fontSize: "var(--font-caption)", color: "var(--text-secondary)" }}>
            Open for community verification
          </span>
        </div>
      </div>

      {/* Commitment list */}
      {loading ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 0",
            color: "var(--text-secondary)",
          }}
        >
          Loading public commitments...
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
            background: "var(--surface-elevated)",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <Globe size={48} style={{ marginBottom: "16px", opacity: 0.4 }} />
          <p style={{ fontSize: "var(--font-subtitle)", marginBottom: "8px", color: "var(--text-primary)" }}>
            No public commitments yet
          </p>
          <p style={{ margin: 0 }}>Public pledges from verified figures will appear here.</p>
        </div>
      ) : (
        commitments.map((c) => <CommitmentCard key={c.id} commitment={c} />)
      )}
    </div>
  );
}
