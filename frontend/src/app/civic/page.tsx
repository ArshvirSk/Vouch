"use client";

import { CommitmentListPage } from "@/components/CommitmentListPage";

export default function CivicPage() {
  return (
    <div className="shell-content">
      <h1 style={{ fontSize: "var(--font-display)", fontWeight: 700, marginBottom: "4px" }}>
        Civic
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Promises by public representatives, verified by ward residents.
      </p>
      <CommitmentListPage category="civic" />
    </div>
  );
}
