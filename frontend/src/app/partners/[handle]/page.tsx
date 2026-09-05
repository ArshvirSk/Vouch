"use client";

/**
 * Partners / Jurors List — Design Doc §5.6.
 * Shows shared track record: "6 commitments together · 5 kept".
 */

import { use } from "react";
import Link from "next/link";
import { getInitials } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";

interface Partner {
  handle: string;
  commitmentsTogether: number;
  kept: number;
}

// Demo data — in production, this would come from a /users/{handle}/partners endpoint
const demoPartners: Partner[] = [
  { handle: "alex_dev", commitmentsTogether: 6, kept: 5 },
  { handle: "sarah_runs", commitmentsTogether: 4, kept: 4 },
  { handle: "mike_codes", commitmentsTogether: 3, kept: 2 },
  { handle: "priya_reads", commitmentsTogether: 8, kept: 6 },
  { handle: "jordan_fit", commitmentsTogether: 2, kept: 2 },
];

export default function PartnersPage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = use(params);

  return (
    <div
      className="container"
      style={{ paddingTop: "24px", paddingBottom: "40px" }}
    >
      <Link
        href={`/profile/${handle}`}
        style={{
          color: "var(--text-secondary)",
          textDecoration: "none",
          fontSize: "var(--font-caption)",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          marginBottom: "20px",
        }}
      >
        <ArrowLeft size={16} /> Back to Profile
      </Link>

      <h1
        style={{
          fontSize: "var(--font-title)",
          fontWeight: 700,
          marginBottom: "4px",
        }}
      >
        Partners & Jurors
      </h1>
      <p
        style={{
          color: "var(--text-secondary)",
          marginBottom: "24px",
        }}
      >
        People @{handle} has shared accountability with
      </p>

      {/* Partner rows — Design Doc §5.6 (Ref B relational framing) */}
      {demoPartners.map((partner) => (
        <Link
          key={partner.handle}
          href={`/profile/${partner.handle}`}
          style={{ textDecoration: "none" }}
        >
          <div
            className="card"
            style={{
              marginBottom: "8px",
              padding: "16px",
              display: "flex",
              alignItems: "center",
              gap: "14px",
            }}
          >
            {/* Avatar */}
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "50%",
                background: "var(--bg-surface-raised)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "var(--font-body)",
                fontWeight: 600,
                color: "var(--accent-primary)",
                flexShrink: 0,
              }}
            >
              {getInitials(partner.handle)}
            </div>

            {/* Info */}
            <div style={{ flex: 1 }}>
              <div
                style={{
                  fontWeight: 600,
                  marginBottom: "2px",
                }}
              >
                @{partner.handle}
              </div>
              <div
                style={{
                  fontSize: "var(--font-caption)",
                  color: "var(--text-secondary)",
                }}
              >
                {partner.commitmentsTogether} commitments together ·{" "}
                <span style={{ color: "var(--accent-verified)" }}>
                  {partner.kept} kept
                </span>
              </div>
            </div>

            {/* Completion rate */}
            <div
              style={{
                fontSize: "var(--font-body)",
                fontWeight: 600,
                color:
                  partner.kept / partner.commitmentsTogether >= 0.8
                    ? "var(--accent-verified)"
                    : partner.kept / partner.commitmentsTogether >= 0.5
                      ? "var(--accent-primary)"
                      : "var(--accent-broken)",
              }}
            >
              {Math.round(
                (partner.kept / partner.commitmentsTogether) * 100
              )}
              %
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
