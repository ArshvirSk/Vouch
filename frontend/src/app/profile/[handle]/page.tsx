"use client";

/**
 * Profile / Reputation — Design Doc §5.5.
 * Stats row, History/As Juror tabs, waveform trend bars, jury accuracy gauge.
 */

import { useState, useEffect, use } from "react";
import { getUserProfile, getReputationHistory, type UserProfile, type ReputationEvent } from "@/lib/api";
import { ReputationGauge } from "@/components/ReputationGauge";
import { WaveformBars } from "@/components/WaveformBars";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import { Flame } from "lucide-react";

export default function ProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = use(params);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [events, setEvents] = useState<ReputationEvent[]>([]);
  const [activeTab, setActiveTab] = useState<"history" | "juror">("history");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [profileData, historyData] = await Promise.all([
          getUserProfile(handle),
          getReputationHistory(handle),
        ]);
        setProfile(profileData);
        setEvents(historyData.events);
      } catch {
        // Demo data
        setProfile(getDemoProfile(handle));
        setEvents(getDemoEvents());
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [handle]);

  if (loading) {
    return (
      <div
        className="container"
        style={{ paddingTop: "60px", textAlign: "center", color: "var(--text-secondary)" }}
      >
        Loading profile...
      </div>
    );
  }

  if (!profile) return null;

  const commitmentEvents = events.filter(
    (e) => e.reason === "commitment_kept" || e.reason === "commitment_broken"
  );
  const jurorEvents = events.filter(
    (e) => e.reason === "jury_accurate" || e.reason === "jury_inaccurate"
  );

  return (
    <div className="container" style={{ paddingTop: "24px", paddingBottom: "40px" }}>
      {/* Profile header */}
      <div style={{ textAlign: "center", marginBottom: "32px" }}>
        <div
          style={{
            width: "72px",
            height: "72px",
            borderRadius: "50%",
            background: "var(--bg-surface-raised)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 12px",
            fontSize: "var(--font-title)",
            fontWeight: 700,
            color: "var(--accent-primary)",
          }}
        >
          {handle.slice(0, 2).toUpperCase()}
        </div>
        <h1 style={{ fontSize: "var(--font-title)", fontWeight: 700 }}>
          @{handle}
        </h1>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "var(--font-caption)",
            marginTop: "4px",
          }}
        >
          Member since {formatDate(profile.user.created_at)}
        </p>
      </div>

      {/* Stats row — Design Doc §5.5 (Ref B pattern) */}
      <div className="stats-row" style={{ marginBottom: "32px" }}>
        <div className="stat-item">
          <div className="stat-value" style={{ color: "var(--accent-primary)" }}>
            {profile.user.reputation_score.toFixed(1)}
          </div>
          <div className="stat-label">Reputation</div>
        </div>
        <div className="stat-item">
          <div className="stat-value" style={{ color: "var(--accent-primary)", display: "flex", alignItems: "center", justifyContent: "center", gap: "4px" }}>
            <Flame size={20} /> {profile.user.current_streak}
          </div>
          <div className="stat-label">Streak</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">
            {profile.stats.commitments_met}/{profile.stats.commitments_total}
          </div>
          <div className="stat-label">Kept</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{profile.stats.jury_accuracy.toFixed(0)}%</div>
          <div className="stat-label">Accuracy</div>
        </div>
      </div>

      {/* Jury accuracy gauge + Waveform bars side by side */}
      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "space-around",
          alignItems: "center",
          padding: "24px",
          marginBottom: "24px",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "var(--font-caption)",
              color: "var(--text-secondary)",
              marginBottom: "12px",
              textAlign: "center",
            }}
          >
            Jury Accuracy
          </div>
          <ReputationGauge
            value={profile.stats.jury_accuracy}
            label="Accuracy"
            color="var(--accent-verified)"
          />
        </div>
        <div>
          <div
            style={{
              fontSize: "var(--font-caption)",
              color: "var(--text-secondary)",
              marginBottom: "12px",
              textAlign: "center",
            }}
          >
            Reputation Trend
          </div>
          <WaveformBars events={events} />
        </div>
      </div>

      {/* Tabs: History / As Juror — Design Doc §5.5 */}
      <div className="status-strip" style={{ marginBottom: "20px" }}>
        <button
          className={`status-tab ${activeTab === "history" ? "active" : ""}`}
          onClick={() => setActiveTab("history")}
        >
          History
        </button>
        <button
          className={`status-tab ${activeTab === "juror" ? "active" : ""}`}
          onClick={() => setActiveTab("juror")}
        >
          As Juror
        </button>
      </div>

      {/* Event list */}
      <div>
        {(activeTab === "history" ? commitmentEvents : jurorEvents).length ===
        0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "32px",
              color: "var(--text-secondary)",
            }}
          >
            No {activeTab === "history" ? "commitment" : "juror"} events yet
          </div>
        ) : (
          (activeTab === "history" ? commitmentEvents : jurorEvents).map((event) => (
            <div
              key={event.id}
              className="card animate-in"
              style={{
                marginBottom: "8px",
                padding: "14px 16px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <span
                  style={{
                    color:
                      event.delta > 0
                        ? "var(--accent-verified)"
                        : "var(--accent-broken)",
                    fontWeight: 600,
                    marginRight: "8px",
                  }}
                >
                  {event.delta > 0 ? "+" : ""}
                  {event.delta}
                </span>
                <span style={{ color: "var(--text-secondary)" }}>
                  {event.reason.replace(/_/g, " ")}
                </span>
              </div>
              <span
                style={{
                  fontSize: "var(--font-caption)",
                  color: "var(--text-secondary)",
                }}
              >
                {formatDate(event.created_at)}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Link to partners */}
      <Link
        href={`/partners/${handle}`}
        className="btn btn-outline"
        style={{
          width: "100%",
          marginTop: "24px",
          textDecoration: "none",
          display: "block",
          textAlign: "center",
        }}
      >
        View Partners & Jurors ({profile.stats.partner_count})
      </Link>

      {/* Web3 Export Section */}
      <div style={{ marginTop: "32px", padding: "16px", background: "var(--bg-surface)", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
        <h3 style={{ fontSize: "var(--font-body)", fontWeight: 600, marginBottom: "8px" }}>Web3 Reputation</h3>
        <p style={{ fontSize: "var(--font-caption)", color: "var(--text-secondary)", marginBottom: "16px" }}>
          Connect your wallet to export your reputation score as an immutable EAS attestation on Polygon.
        </p>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <button 
            className="btn btn-primary" 
            onClick={() => alert("EAS Attestation creation triggered! (Mock implementation)")}
            style={{ flex: 1 }}
          >
            Mint Attestation
          </button>
        </div>
      </div>
    </div>
  );
}

function getDemoProfile(handle: string): UserProfile {
  return {
    user: {
      id: "demo",
      handle,
      reputation_score: 72.5,
      current_streak: 2,
      created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    },
    stats: {
      commitments_total: 8,
      commitments_met: 6,
      completion_rate: 75.0,
      jury_accuracy: 85.7,
      total_votes_cast: 14,
      partner_count: 5,
    },
  };
}

function getDemoEvents(): ReputationEvent[] {
  const now = Date.now();
  return [
    { id: "1", user_id: "demo", delta: 5.0, reason: "commitment_kept", commitment_id: "c1", created_at: new Date(now - 1 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "2", user_id: "demo", delta: 2.0, reason: "jury_accurate", commitment_id: "c2", created_at: new Date(now - 2 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "3", user_id: "demo", delta: -5.0, reason: "commitment_broken", commitment_id: "c3", created_at: new Date(now - 5 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "4", user_id: "demo", delta: 5.0, reason: "commitment_kept", commitment_id: "c4", created_at: new Date(now - 8 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "5", user_id: "demo", delta: -2.0, reason: "jury_inaccurate", commitment_id: "c5", created_at: new Date(now - 10 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "6", user_id: "demo", delta: 5.0, reason: "commitment_kept", commitment_id: "c6", created_at: new Date(now - 12 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "7", user_id: "demo", delta: 2.0, reason: "jury_accurate", commitment_id: "c7", created_at: new Date(now - 15 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "8", user_id: "demo", delta: 5.0, reason: "commitment_kept", commitment_id: "c8", created_at: new Date(now - 20 * 24 * 60 * 60 * 1000).toISOString() },
  ];
}
