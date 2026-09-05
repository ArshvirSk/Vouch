"use client";

/**
 * Vote buttons — Design Doc §5.4.
 * Three large vote buttons: Met (mint), Broken (red), Abstain (neutral gray outline).
 * Deliberately oversized and unambiguous — highest-stakes tap in the app.
 */

import { Check, X, Minus } from "lucide-react";

interface VoteButtonsProps {
  onVote: (choice: "met" | "broken" | "abstain") => void;
  disabled?: boolean;
}

export function VoteButtons({ onVote, disabled }: VoteButtonsProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <button
        className="btn btn-met"
        onClick={() => onVote("met")}
        disabled={disabled}
        style={{ width: "100%", opacity: disabled ? 0.5 : 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
      >
        <Check size={20} /> Commitment Met
      </button>
      <button
        className="btn btn-broken"
        onClick={() => onVote("broken")}
        disabled={disabled}
        style={{ width: "100%", opacity: disabled ? 0.5 : 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
      >
        <X size={20} /> Commitment Broken
      </button>
      <button
        className="btn btn-abstain"
        onClick={() => onVote("abstain")}
        disabled={disabled}
        style={{ width: "100%", opacity: disabled ? 0.5 : 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
      >
        <Minus size={20} /> Abstain
      </button>
    </div>
  );
}
