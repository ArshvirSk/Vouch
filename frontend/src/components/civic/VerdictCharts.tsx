"use client";

/**
 * VerdictCharts — Stage 2 of the civic detail redesign.
 *
 * - VerdictOverTimeChart: met/broken/abstain percentage lines with
 *   annotated event markers, driven by verdict_history snapshots.
 * - CurrentVerdictDonut: final met/broken/abstain split + juror count.
 *
 * Hand-rolled SVG (no chart lib in the project); all colors from the
 * existing CSS tokens.
 */

import { useMemo, useState } from "react";
import type { VerdictHistoryData, Vote } from "@/lib/api";

const MET_COLOR = "var(--accent-verified)";
const BROKEN_COLOR = "var(--accent-broken)";
const ABSTAIN_COLOR = "var(--text-secondary)";

const monthLabels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function shortDate(iso: string): string {
  const d = new Date(iso);
  return `${monthLabels[d.getMonth()]} ${d.getFullYear()}`;
}

/* ── Over-time line chart ─────────────────────────────────────────── */

export function VerdictOverTimeChart({ history }: { history: VerdictHistoryData }) {
  const W = 560;
  const H = 260;
  const PAD = { l: 40, r: 16, t: 26, b: 30 };
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;

  const snapshots = history.snapshots;
  const { series, markers, xTicks } = useMemo(() => {
    const times = snapshots.map((s) => new Date(s.created_at).getTime());
    const t0 = Math.min(...times);
    const t1 = Math.max(...times);
    const span = Math.max(t1 - t0, 1);

    const x = (iso: string) => PAD.l + ((new Date(iso).getTime() - t0) / span) * iw;
    const y = (pct: number) => PAD.t + (1 - pct / 100) * ih;

    const pctSeries = (key: "met" | "broken" | "abstain") =>
      snapshots.map((s) => {
        const denom = s.met + s.broken + s.abstain;
        return { x: x(s.created_at), y: y(denom ? (s[key] / denom) * 100 : 0) };
      });

    const markers = snapshots
      .map((s, i) => ({ ...s, i, x: x(s.created_at) }))
      .filter((s) => s.event_label && (s.event_type === "status" || i_iscritical(snapshots, s.i)));

    const xTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
      x: PAD.l + f * iw,
      label: shortDate(new Date(t0 + f * span).toISOString()),
    }));

    return {
      series: {
        met: pctSeries("met"),
        broken: pctSeries("broken"),
        abstain: pctSeries("abstain"),
      },
      markers,
      xTicks,
    };
  }, [snapshots, iw, ih]);

  const [hover, setHover] = useState<number | null>(null);

  const path = (pts: { x: number; y: number }[]) =>
    pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  const line = (color: string, pts: { x: number; y: number }[], key: string) => (
    <g key={key}>
      <path d={path(pts)} fill="none" stroke={color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      {pts.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={hover === i ? 5 : 3}
          fill={color}
          onMouseEnter={() => setHover(i)}
          onMouseLeave={() => setHover(null)}
          style={{ cursor: "pointer" }}
        />
      ))}
    </g>
  );

  if (snapshots.length < 2) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)", fontSize: "var(--font-caption)" }}>
        Not enough history yet — the chart fills in as votes and evidence arrive.
      </div>
    );
  }

  return (
    <div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }} role="img" aria-label="Public verdict over time">
        {/* horizontal gridlines + % labels */}
        {[0, 50, 100].map((p) => {
          const y = PAD.t + (1 - p / 100) * ih;
          return (
            <g key={p}>
              <line x1={PAD.l} y1={y} x2={W - PAD.r} y2={y} stroke="var(--border-subtle)" strokeWidth="1" />
              <text x={PAD.l - 8} y={y + 4} textAnchor="end" fontSize="10" fill="var(--text-secondary)">
                {p}%
              </text>
            </g>
          );
        })}
        {/* x labels */}
        {xTicks.map((t, i) => (
          <text key={i} x={t.x} y={H - 8} textAnchor={i === 0 ? "start" : i === xTicks.length - 1 ? "end" : "middle"} fontSize="10" fill="var(--text-secondary)">
            {t.label}
          </text>
        ))}

        {/* event markers — dashed verticals + dots on top edge; labels
            alternate rows to avoid collisions on dense timelines */}
        {markers.map((m, i) => {
          const nearRight = m.x > W - PAD.r - 90;
          const labelY = PAD.t + 6 + (i % 3) * 11;
          const label = m.event_label && m.event_label.length > 22 ? `${m.event_label.slice(0, 21)}…` : m.event_label;
          return (
            <g key={`m-${m.i}`}>
              <line x1={m.x} y1={PAD.t} x2={m.x} y2={PAD.t + ih} stroke="var(--border-subtle)" strokeWidth="1" strokeDasharray="3 3" />
              <circle cx={m.x} cy={PAD.t - 6} r="3.5" fill="var(--accent-primary)">
                <title>{`${m.event_label} — ${shortDate(m.created_at)}`}</title>
              </circle>
              <text
                x={nearRight ? m.x - 5 : m.x + 5}
                y={labelY}
                textAnchor={nearRight ? "end" : "start"}
                fontSize="9"
                fill="var(--text-secondary)"
              >
                {label}
              </text>
            </g>
          );
        })}

        {line(MET_COLOR, series.met, "met")}
        {line(BROKEN_COLOR, series.broken, "broken")}
        {line(ABSTAIN_COLOR, series.abstain, "abstain")}
      </svg>

      {/* Legend + hover readout */}
      <div style={{ display: "flex", gap: "16px", fontSize: "var(--font-caption)", color: "var(--text-secondary)", marginTop: "4px" }}>
        <LegendDot color={MET_COLOR} label="Met" />
        <LegendDot color={BROKEN_COLOR} label="Broken" />
        <LegendDot color={ABSTAIN_COLOR} label="Abstain" />
        {hover != null && snapshots[hover] && (
          <span style={{ marginLeft: "auto", color: "var(--text-primary)" }}>
            {new Date(snapshots[hover].created_at).toLocaleDateString()} · {snapshots[hover].met}M /{" "}
            {snapshots[hover].broken}B / {snapshots[hover].abstain}A
            {snapshots[hover].event_label ? ` · ${snapshots[hover].event_label}` : ""}
          </span>
        )}
      </div>
    </div>
  );
}

/** Citizen-report/news labels decorate vote markers on alternating votes (seed convention). */
function i_iscritical(snapshots: { event_type: string }[], i: number): boolean {
  return snapshots[i]?.event_type === "vote" && i % 3 !== 0;
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
      <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: color, display: "inline-block" }} />
      {label}
    </span>
  );
}

/* ── Current verdict donut ────────────────────────────────────────── */

export function CurrentVerdictDonut({ votes, jurorCount }: { votes: Vote[]; jurorCount: number }) {
  const met = votes.filter((v) => v.vote === "met").length;
  const broken = votes.filter((v) => v.vote === "broken").length;
  const abstain = votes.filter((v) => v.vote === "abstain").length;
  const cast = met + broken + abstain;
  const total = Math.max(cast, jurorCount, 1);
  const pct = (n: number) => (n / total) * 100;

  const R = 52;
  const C = 2 * Math.PI * R;
  const segs = [
    { label: "Met", n: met, color: MET_COLOR },
    { label: "Broken", n: broken, color: BROKEN_COLOR },
    { label: "Abstain", n: abstain, color: ABSTAIN_COLOR },
  ];

  // Dominant segment share shows in the donut hole.
  const leader = [...segs].sort((a, b) => b.n - a.n)[0];
  const leaderPct = leader && leader.n > 0 ? Math.round(pct(leader.n)) : 0;

  let offset = 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
      <svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label="Current verdict split">
        <circle cx="70" cy="70" r={R} fill="none" stroke="var(--bg-surface-raised)" strokeWidth="14" />
        {segs.map((s) => {
          if (s.n === 0) return null;
          const frac = s.n / total;
          const dash = `${frac * C} ${C}`;
          const el = (
            <circle
              key={s.label}
              cx="70"
              cy="70"
              r={R}
              fill="none"
              stroke={s.color}
              strokeWidth="14"
              strokeDasharray={dash}
              strokeDashoffset={-offset * C}
              transform="rotate(-90 70 70)"
              strokeLinecap="butt"
            />
          );
          offset += frac;
          return el;
        })}
        <text x="70" y="66" textAnchor="middle" fontSize="20" fontWeight="700" fill="var(--text-primary)">
          {leaderPct}%
        </text>
        <text x="70" y="84" textAnchor="middle" fontSize="10" fill={leader?.n ? leader.color : "var(--text-secondary)"}>
          {leader?.n ? leader.label : "No votes"}
        </text>
      </svg>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
        {segs.map((s) => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "var(--font-caption)" }}>
            <span style={{ width: "10px", height: "10px", borderRadius: "3px", background: s.color, display: "inline-block" }} />
            <span style={{ color: "var(--text-secondary)" }}>{s.label}</span>
            <span style={{ marginLeft: "auto", fontWeight: 600, color: "var(--text-primary)" }}>{pct(s.n).toFixed(0)}%</span>
          </div>
        ))}
        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "8px", fontSize: "var(--font-caption)", color: "var(--text-secondary)" }}>
          Total jurors <span style={{ float: "right", fontWeight: 600, color: "var(--text-primary)" }}>{jurorCount}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Stage 2 overview tab composition ─────────────────────────────── */

export function VerdictOverview({
  history,
  votes,
  jurorCount,
}: {
  history: VerdictHistoryData | null;
  votes: Vote[];
  jurorCount: number;
}) {
  return (
    <div style={{ display: "flex", gap: "16px", alignItems: "stretch" }}>
      <div className="card" style={{ flex: "2 1 0%", padding: "18px", minWidth: 0 }}>
        <h3 style={{ fontSize: "var(--font-body)", fontWeight: 700, margin: "0 0 4px" }}>Public Verdict Over Time</h3>
        <p style={{ fontSize: "var(--font-caption)", color: "var(--text-secondary)", margin: "0 0 12px" }}>
          How people's opinions have changed as new evidence came in.
        </p>
        {history ? (
          <VerdictOverTimeChart history={history} />
        ) : (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>Loading history…</div>
        )}
      </div>

      <div className="card" style={{ flex: "1 1 0%", padding: "18px", minWidth: "260px" }}>
        <h3 style={{ fontSize: "var(--font-body)", fontWeight: 700, margin: "0 0 14px" }}>Current Verdict</h3>
        <CurrentVerdictDonut votes={votes} jurorCount={jurorCount} />
      </div>
    </div>
  );
}
