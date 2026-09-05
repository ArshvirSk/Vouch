"use client";

/**
 * Waveform trend bars — Design Doc §5.5 (from Ref A waveform bar chart).
 * Shows recent commitment outcomes: met=mint bars, broken=red bars, disputed=purple.
 */

import type { ReputationEvent } from "@/lib/api";

interface WaveformBarsProps {
  events: ReputationEvent[];
  maxBars?: number;
}

export function WaveformBars({ events, maxBars = 20 }: WaveformBarsProps) {
  const recent = events.slice(0, maxBars).reverse(); // oldest to newest left-to-right

  if (recent.length === 0) {
    return (
      <div style={{ color: "var(--text-secondary)", fontSize: "var(--font-caption)" }}>
        No reputation history yet
      </div>
    );
  }

  const maxDelta = Math.max(...recent.map((e) => Math.abs(e.delta)), 1);

  return (
    <div className="waveform">
      {recent.map((event) => {
        const height = (Math.abs(event.delta) / maxDelta) * 100;
        let className = "waveform-bar ";
        if (event.reason === "commitment_kept" || event.reason === "jury_accurate") {
          className += "met";
        } else if (
          event.reason === "commitment_broken" ||
          event.reason === "jury_inaccurate"
        ) {
          className += "broken";
        } else {
          className += "disputed";
        }

        return (
          <div
            key={event.id}
            className={className}
            style={{ height: `${Math.max(height, 8)}%` }}
            title={`${event.delta > 0 ? "+" : ""}${event.delta} (${event.reason})`}
          />
        );
      })}
    </div>
  );
}
