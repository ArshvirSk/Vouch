"use client";

import { CommitmentListPage } from "@/components/CommitmentListPage";

export default function MyActivityPage() {
  return (
    <div className="shell-content">
      <h1 style={{ fontSize: "var(--font-display)", fontWeight: 700, marginBottom: "4px" }}>
        My activity
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Your votes, verifications, and reputation history.
      </p>
      <CommitmentListPage category="" />
    </div>
  );
}
