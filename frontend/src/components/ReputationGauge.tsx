"use client";

/**
 * Reputation gauge — Design Doc §5.5 (from Ref A efficiency dial).
 * Circular SVG gauge showing a percentage.
 */

interface ReputationGaugeProps {
  value: number; // 0-100
  label: string;
  color?: string;
  size?: number;
}

export function ReputationGauge({
  value,
  label,
  color = "var(--accent-primary)",
  size = 120,
}: ReputationGaugeProps) {
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(100, Math.max(0, value)) / 100) * circumference;

  return (
    <div
      className="gauge-container"
      style={{
        width: size,
        height: size,
        position: "relative",
      }}
    >
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          className="gauge-bg"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
        />
        <circle
          className="gauge-fill"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: "var(--font-title)",
            fontWeight: 700,
            color: "var(--text-primary)",
          }}
        >
          {Math.round(value)}%
        </div>
        <div
          style={{
            fontSize: "10px",
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: "0.5px",
          }}
        >
          {label}
        </div>
      </div>
    </div>
  );
}
