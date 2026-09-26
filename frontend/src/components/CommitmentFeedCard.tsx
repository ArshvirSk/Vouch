"use client";

/**
 * CommitmentFeedCard — the new image-left horizontal card variant for the
 * redesigned home feed (stage 3). Distinct from the existing text-only
 * CommitmentCard used on Civic/Vendors/etc. pages.
 *
 * Shows: left thumbnail, type badge (Civic/Vendor), title, byline
 * (Accountable Party · location), quoted commitment text, status pill
 * (orange OPEN / amber IN VERIFICATION / blue-gray AWAITING EVIDENCE,
 * existing verdict colors for resolved), deadline countdown, time progress
 * bar, and metadata row (evidence / jurors / rating).
 *
 * Juror count intentionally shows the real (potentially large) open-jury
 * size for civic commitments — do not collapse to the old fixed 2-juror
 * model.
 */

import Link from "next/link";
import type { Commitment } from "@/lib/api";
import { formatRelativeTime, calcTimeProgress, getStatusLabel } from "@/lib/utils";
import { Paperclip, Users, Star, Landmark, Briefcase } from "lucide-react";

/** Deterministic placeholder thumbnail per commitment (no asset uploads yet). */
function thumbnailFor(c: Commitment): string {
  if (c.category === "vendor") {
    // Kitchen/interior work
    return "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=400&h=400&fit=crop";
  }
  if (c.category === "civic") {
    // Road/infrastructure construction
    return "https://images.unsplash.com/photo-1503708928676-1cb796a0891e?w=400&h=400&fit=crop";
  }
  // Personal — study/desk
  return "https://images.unsplash.com/photo-1488190211105-8b0e65b80b4e?w=400&h=400&fit=crop";
}

/** Status pill colors — resolved states use existing verdict tokens. */
function statusPillClass(status: string): string {
  switch (status) {
    case "open":
      return "feed-status-open";
    case "in_verification":
      return "feed-status-verification";
    case "evidence_submitted":
      return "feed-status-awaiting";
    default:
      return ""; // met/broken/disputed/expired → existing verdict-badge colors
  }
}

export function CommitmentFeedCard({ commitment }: { commitment: Commitment }) {
  const progress = calcTimeProgress(commitment.created_at, commitment.deadline);
  const isPastDeadline = new Date(commitment.deadline) < new Date();
  const isResolved = ["met", "broken", "disputed", "expired"].includes(commitment.status);

  const isCivic = commitment.category === "civic";
  const TypeIcon = isCivic ? Landmark : Briefcase;
  const typeLabel = isCivic ? "Civic" : commitment.category === "vendor" ? "Vendor" : "Personal";

  const byline = isCivic
    ? `${commitment.official_name ?? "Public official"} · ${commitment.ward ?? "Ward undisclosed"}`
    : commitment.category === "vendor"
      ? `${commitment.official_name ?? "Service provider"} · ${commitment.official_role ?? "Local business"}`
      : commitment.author?.handle
        ? `@${commitment.author.handle}`
        : "Personal commitment";

  // Rating: not yet a backend field — derived placeholder from reputation
  // (flagged for stage 4 backend work)
  const rating = (3.2 + ((commitment.evidence_count % 9) * 0.2)).toFixed(1);

  return (
    <Link href={`/commitment/${commitment.id}`} style={{ textDecoration: "none", display: "block" }}>
      <div
        className="card feed-card"
        style={{
          display: "flex",
          gap: "16px",
          padding: "14px",
          marginBottom: "14px",
        }}
      >
        {/* Left thumbnail */}
        <img
          src={thumbnailFor(commitment)}
          alt=""
          style={{
            width: "128px",
            height: "128px",
            borderRadius: "12px",
            objectFit: "cover",
            flexShrink: 0,
            backgroundColor: "var(--bg-surface-raised)",
          }}
        />

        {/* Body */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
          {/* Top row: type badge + title ... status pill + deadline */}
          <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
            <div style={{ minWidth: 0 }}>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "5px",
                  fontSize: "var(--font-caption)",
                  fontWeight: 600,
                  color: "var(--accent-primary)",
                  marginBottom: "2px",
                }}
              >
                <TypeIcon size={12} />
                {typeLabel}
              </span>
              <h3
                style={{
                  fontSize: "var(--font-subtitle)",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  margin: "0 0 2px",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {commitment.title}
              </h3>
              <div
                style={{
                  fontSize: "var(--font-caption)",
                  color: "var(--text-secondary)",
                  marginBottom: "4px",
                }}
              >
                {byline}
              </div>
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-end",
                gap: "4px",
                flexShrink: 0,
              }}
            >
              <span className={`verdict-badge ${commitment.status} ${statusPillClass(commitment.status)}`}>
                {commitment.status === "evidence_submitted"
                  ? "Awaiting Evidence"
                  : getStatusLabel(commitment.status)}
              </span>
              <span
                style={{
                  fontSize: "var(--font-caption)",
                  color: isPastDeadline ? "var(--accent-broken)" : "var(--text-secondary)",
                }}
              >
                {isPastDeadline
                  ? "Deadline passed"
                  : `Due ${formatRelativeTime(commitment.deadline)}`}
              </span>
            </div>
          </div>

          {/* Quoted commitment text */}
          <p
            style={{
              fontStyle: "italic",
              color: "var(--text-secondary)",
              fontSize: "var(--font-caption)",
              margin: "0 0 8px",
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
            }}
          >
            {commitment.measurable_condition}
          </p>

          {/* Progress bar */}
          {!isResolved && (
            <div className="progress-bar" style={{ marginBottom: "10px" }}>
              <div
                className={`progress-bar-fill ${progress > 80 ? "warning" : "on-track"}`}
                style={{ width: `${progress}%` }}
              />
            </div>
          )}

          {/* Metadata row */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "18px",
              fontSize: "var(--font-caption)",
              color: "var(--text-secondary)",
              marginTop: "auto",
            }}
          >
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              <Paperclip size={13} /> {commitment.evidence_count} pieces of evidence
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              <Users size={13} /> {commitment.juror_count || commitment.vote_count || 0} jurors
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              <Star size={13} color="var(--accent-primary)" /> {rating} rating
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
