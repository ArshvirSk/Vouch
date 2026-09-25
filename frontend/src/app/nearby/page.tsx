"use client";

import { CommitmentListPage } from "@/components/CommitmentListPage";

export default function NearbyPage() {
  return (
    <div className="shell-content">
      <h1 style={{ fontSize: "var(--font-display)", fontWeight: 700, marginBottom: "4px" }}>
        Nearby
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Everything local to your area — civic and vendor promises blended.
      </p>
      <CommitmentListPage category="" />
    </div>
  );
}
