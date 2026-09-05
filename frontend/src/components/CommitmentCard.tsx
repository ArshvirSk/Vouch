"use client";

import Link from "next/link";
import type { Commitment } from "@/lib/api";
import { formatRelativeTime, calcTimeProgress, getStatusLabel, getInitials } from "@/lib/utils";
import { Paperclip } from "lucide-react";

interface CommitmentCardProps {
  commitment: Commitment;
}

/**
 * Commitment card — Design Doc §5.1, §6.
 * Displays: title, category tag, deadline countdown, time-based progress bar,
 * jury avatars (stacked circles), and "Send Evidence" button.
 */
export function CommitmentCard({ commitment }: CommitmentCardProps) {
  const progress = calcTimeProgress(commitment.created_at, commitment.deadline);
  const isPastDeadline = new Date(commitment.deadline) < new Date();
  const isResolved = ["met", "broken", "disputed", "expired"].includes(commitment.status);

  return (
    <Link
      href={`/commitment/${commitment.id}`}
      style={{ textDecoration: "none" }}
    >
      <div className="card animate-in" style={{ marginBottom: "12px" }}>
        {/* Header row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: "12px",
          }}
        >
          <div style={{ flex: 1 }}>
            <h3
              style={{
                fontSize: "var(--font-subtitle)",
                fontWeight: 600,
                color: "var(--text-primary)",
                marginBottom: "4px",
              }}
            >
              {commitment.title}
            </h3>
            <p
              style={{
                fontSize: "var(--font-caption)",
                color: "var(--text-secondary)",
              }}
            >
              {commitment.measurable_condition}
            </p>
          </div>
          <span className={`verdict-badge ${commitment.status}`}>
            {getStatusLabel(commitment.status)}
          </span>
        </div>

        {/* Progress bar (time-based) — Design Doc §5.1 */}
        {!isResolved && (
          <div className="progress-bar" style={{ marginBottom: "12px" }}>
            <div
              className={`progress-bar-fill ${progress > 80 ? "warning" : "on-track"}`}
              style={{ width: `${progress}%` }}
            />
          </div>
        )}

        {/* Footer row */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          {/* Deadline countdown */}
          <span
            style={{
              fontSize: "var(--font-caption)",
              color: isPastDeadline
                ? "var(--accent-broken)"
                : "var(--text-secondary)",
            }}
          >
            {isPastDeadline ? "Deadline passed" : `Due ${formatRelativeTime(commitment.deadline)}`}
          </span>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {/* Jury avatars — stacked circles */}
            {commitment.juror_count > 0 && (
              <div className="avatar-stack">
                {Array.from({ length: Math.min(commitment.juror_count, 5) }).map((_, i) => (
                  <div key={i} className="avatar">
                    J{i + 1}
                  </div>
                ))}
              </div>
            )}

            {/* Evidence count */}
            {commitment.evidence_count > 0 && (
              <span
                style={{
                  fontSize: "var(--font-caption)",
                  color: "var(--accent-primary)",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px"
                }}
              >
                <Paperclip size={14} /> {commitment.evidence_count}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
