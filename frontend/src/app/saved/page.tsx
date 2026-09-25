"use client";

import { CommitmentListPage } from "@/components/CommitmentListPage";

export default function SavedPage() {
  return (
    <div className="shell-content">
      <h1 style={{ fontSize: "var(--font-display)", fontWeight: 700, marginBottom: "4px" }}>
        Saved
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Commitments you've saved for later.
      </p>
      <CommitmentListPage category="" />
    </div>
  );
}
