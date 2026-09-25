"use client";

import { CommitmentListPage } from "@/components/CommitmentListPage";

export default function VendorsPage() {
  return (
    <div className="shell-content">
      <h1 style={{ fontSize: "var(--font-display)", fontWeight: 700, marginBottom: "4px" }}>
        Vendors
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "24px" }}>
        Contractor and service commitments, verified by customers.
      </p>
      <CommitmentListPage category="vendor" />
    </div>
  );
}
