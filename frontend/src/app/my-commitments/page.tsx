"use client";

import { CommitmentListPage } from "@/components/CommitmentListPage";

export default function MyCommitmentsPage() {
  return (
    <div className="shell-content">
      <h1 style={{ fontSize: "var(--font-display)", fontWeight: 700, marginBottom: "4px" }}>
        My commitments
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Commitments you've made or follow.
      </p>
      <CommitmentListPage category="" />
    </div>
  );
}
