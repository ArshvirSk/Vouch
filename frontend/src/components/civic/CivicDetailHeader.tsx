"use client";

/**
 * CivicDetailHeader — Stage 1 of the enriched civic commitment detail page.
 *
 * Layout per the reference screenshot:
 *   [ before/after slider (or single image fallback) ]
 *   location caption
 *   badge row: Civic + Public ... verdict badge (right)
 *   title + subtitle
 *   description
 *   VERIFIABLE CONDITION callout
 *   stat chip row: Created · Due · Resolved (if resolved) · Jurors
 *
 * Vendor/personal commitments keep the existing detail page untouched.
 * All colors come from existing CSS tokens — no retheme.
 */

import { useMemo, useRef, useState, useEffect } from "react";
import { Landmark, MapPin, Globe, Check, X, Scale, CalendarDays, Hourglass, Flag, Users } from "lucide-react";
import type { Commitment, Evidence } from "@/lib/api";
import { formatDate } from "@/lib/utils";

/** Unsplash URL → image evidence usable in the hero; text/link evidence can't render. */
function isImageEvidence(ev: Evidence): boolean {
  if (ev.type !== "image") return false;
  return /^https?:\/\//.test(ev.content);
}

export function CivicDetailHeader({
  commitment,
  evidenceList,
}: {
  commitment: Commitment;
  evidenceList: Evidence[];
}) {
  const resolved = ["met", "broken", "disputed"].includes(commitment.status);

  // Before/after image pair — falls back to a single image when either
  // side is missing (never a broken slider with placeholders).
  const { beforeImage, afterImage } = useMemo(() => {
    const imgs = evidenceList.filter(isImageEvidence);
    const before = imgs.find((e) => e.phase === "before");
    const after = imgs.find((e) => e.phase === "after");
    // Unphased images can stand in when no explicit tag exists.
    const unphased = imgs.filter((e) => e.phase !== "before" && e.phase !== "after");
    return {
      beforeImage: before?.content ?? unphased[0]?.content ?? null,
      afterImage: after?.content ?? (unphased.length > 1 ? unphased[unphased.length - 1].content : null),
    };
  }, [evidenceList]);

  const heroImage = afterImage ?? beforeImage;

  return (
    <div style={{ marginBottom: "24px" }}>
      {/* ── Hero: slider or single image ─────────────────────────── */}
      <div
        style={{
          position: "relative",
          borderRadius: "16px",
          overflow: "hidden",
          border: "1px solid var(--border-subtle)",
          background: "var(--bg-surface-raised)",
          minHeight: "220px",
        }}
      >
        {heroImage ? (
          beforeImage && afterImage ? (
            <BeforeAfterSlider before={beforeImage} after={afterImage} />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={heroImage}
              alt={commitment.title}
              style={{ width: "100%", height: "340px", objectFit: "cover", display: "block" }}
            />
          )
        ) : (
          // No image evidence at all — quiet placeholder, not a broken layout
          <div
            style={{
              height: "220px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
              gap: "8px",
              background: "linear-gradient(135deg, #1A1C24 0%, #22242E 60%, #1A1C24 100%)",
            }}
          >
            <Landmark size={28} /> No site imagery submitted yet
          </div>
        )}

        {/* Location caption overlays the image bottom-left */}
        {commitment.ward && (
          <div
            style={{
              position: "absolute",
              left: "14px",
              bottom: "12px",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              borderRadius: "100px",
              background: "rgba(22, 23, 29, 0.85)",
              border: "1px solid var(--border-subtle)",
              fontSize: "var(--font-caption)",
              color: "var(--text-primary)",
              backdropFilter: "blur(4px)",
            }}
          >
            <MapPin size={13} color="var(--accent-primary)" />
            {commitment.ward}
          </div>
        )}
      </div>

      {/* ── Badge row: Civic + Public ... verdict (right) ────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          marginTop: "14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            className="pill active"
            style={{ display: "inline-flex", alignItems: "center", gap: "5px", padding: "5px 12px" }}
          >
            <Landmark size={13} /> Civic
          </span>
          {commitment.is_public && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "var(--font-caption)",
                fontWeight: 600,
                color: "var(--text-primary)",
                background: "var(--bg-surface-raised)",
                border: "1px solid var(--border-subtle)",
                padding: "5px 12px",
                borderRadius: "100px",
              }}
            >
              <Globe size={13} /> Public
            </span>
          )}
        </div>

        <span className={`verdict-badge ${commitment.status}`} style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
          {resolved ? (
            commitment.status === "met" ? <Check size={15} /> : commitment.status === "broken" ? <X size={15} /> : <Scale size={15} />
          ) : null}
          {commitment.status === "met" ? "MET" : commitment.status === "broken" ? "BROKEN" : commitment.status === "disputed" ? "DISPUTED" : commitment.status === "in_verification" ? "IN VERIFICATION" : commitment.status === "expired" ? "EXPIRED" : commitment.status === "evidence_submitted" ? "AWAITING EVIDENCE" : "OPEN"}
        </span>
      </div>

      {/* ── Title + subtitle ─────────────────────────────────────── */}
      <h1
        style={{
          fontSize: "var(--font-title)",
          fontWeight: 700,
          margin: "10px 0 4px",
          lineHeight: 1.25,
        }}
      >
        {commitment.title}
      </h1>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          fontSize: "var(--font-caption)",
          color: "var(--text-secondary)",
        }}
      >
        <Landmark size={13} color="var(--accent-primary)" />
        {commitment.official_name ?? "Public official"}
        {commitment.ward ? ` · ${commitment.ward}` : ""}
      </div>

      {/* ── Description ──────────────────────────────────────────── */}
      {commitment.description && (
        <p style={{ color: "var(--text-secondary)", marginTop: "12px", marginBottom: 0, lineHeight: 1.55 }}>
          {commitment.description}
        </p>
      )}

      {/* ── Verifiable condition callout ─────────────────────────── */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          alignItems: "flex-start",
          background: "rgba(255, 107, 53, 0.06)",
          border: "1px solid rgba(255, 107, 53, 0.25)",
          borderRadius: "12px",
          padding: "14px 16px",
          marginTop: "16px",
        }}
      >
        <div
          style={{
            width: "34px",
            height: "34px",
            borderRadius: "10px",
            background: "rgba(255, 107, 53, 0.15)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            color: "var(--accent-primary)",
          }}
        >
          <Check size={17} />
        </div>
        <div>
          <div
            style={{
              fontSize: "10px",
              fontWeight: 700,
              letterSpacing: "0.8px",
              color: "var(--accent-primary)",
              marginBottom: "3px",
            }}
          >
            VERIFIABLE CONDITION
          </div>
          <div style={{ fontSize: "var(--font-body)", color: "var(--text-primary)", lineHeight: 1.5 }}>
            {commitment.measurable_condition}
          </div>
        </div>
      </div>

      {/* ── Stat chip row ────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: "10px", marginTop: "16px", flexWrap: "wrap" }}>
        <StatChip icon={<CalendarDays size={13} />} label="Created" value={formatDay(commitment.created_at)} />
        <StatChip
          icon={<Hourglass size={13} />}
          label="Due date"
          value={formatDay(commitment.deadline)}
          tone={new Date(commitment.deadline) < new Date() && !resolved ? "danger" : "default"}
        />
        {commitment.resolved_at && (
          <StatChip icon={<Flag size={13} />} label="Resolved" value={formatDay(commitment.resolved_at)} tone="success" />
        )}
        <StatChip icon={<Users size={13} />} label="Jurors" value={String(commitment.juror_count ?? commitment.vote_count ?? 0)} />
      </div>
    </div>
  );
}

/** Date-only formatting for stat chips — the shared formatDate includes time, too noisy here. */
function formatDay(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function StatChip({
  icon,
  label,
  value,
  tone = "default",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: "default" | "success" | "danger";
}) {
  const toneColor =
    tone === "success" ? "var(--accent-verified)" : tone === "danger" ? "var(--accent-broken)" : "var(--text-primary)";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        background: "var(--bg-surface-raised)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "10px",
        padding: "8px 12px",
      }}
    >
      <span style={{ color: "var(--accent-primary)", display: "flex" }}>{icon}</span>
      <div>
        <div style={{ fontSize: "10px", color: "var(--text-secondary)" }}>{label}</div>
        <div style={{ fontSize: "var(--font-caption)", fontWeight: 600, color: toneColor }}>{value}</div>
      </div>
    </div>
  );
}

/**
 * BeforeAfterSlider — draggable comparison between two images.
 * Pure CSS + pointer events; no external dependency. If either image fails
 * to load (e.g. a dead seed URL) it degrades to the surviving image.
 */
export function BeforeAfterSlider({ before, after }: { before: string; after: string }) {
  const [pos, setPos] = useState(50); // percent
  const [showHint, setShowHint] = useState(true);
  const [errors, setErrors] = useState<{ before: boolean; after: boolean }>({ before: false, after: false });
  const ref = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  useEffect(() => {
    const t = setTimeout(() => setShowHint(false), 3500);
    return () => clearTimeout(t);
  }, []);

  // Degrade gracefully if a source 404s — one surviving image renders solo.
  if (errors.before || errors.after) {
    const surviving = !errors.before ? before : !errors.after ? after : null;
    if (surviving) {
      return (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={surviving} alt="Site" style={{ width: "100%", height: "340px", objectFit: "cover", display: "block" }} />
      );
    }
  }

  const updateFromClientX = (clientX: number) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setPos(Math.min(96, Math.max(4, pct)));
  };

  return (
    <div
      ref={ref}
      style={{ position: "relative", width: "100%", height: "340px", cursor: "ew-resize", touchAction: "none" }}
      onPointerDown={(e) => {
        dragging.current = true;
        (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
        updateFromClientX(e.clientX);
        setShowHint(false);
      }}
      onPointerMove={(e) => {
        if (dragging.current) updateFromClientX(e.clientX);
      }}
      onPointerUp={() => {
        dragging.current = false;
      }}
      onPointerLeave={() => {
        dragging.current = false;
      }}
    >
      {/* After = base layer (full) */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={after}
        alt="After"
        onError={() => setErrors((p) => ({ ...p, after: true }))}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
      />

      {/* Before = clipped overlay */}
      <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={before}
          alt="Before"
          onError={() => setErrors((p) => ({ ...p, before: true }))}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>

      {/* Divider handle */}
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: `${pos}%`,
          width: "2px",
          background: "rgba(255,255,255,0.9)",
          transform: "translateX(-1px)",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "34px",
            height: "34px",
            borderRadius: "50%",
            background: "rgba(22, 23, 29, 0.85)",
            border: "2px solid rgba(255,255,255,0.9)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontSize: "13px",
            backdropFilter: "blur(3px)",
          }}
        >
          ‹›
        </div>
      </div>

      {/* Corner labels */}
      <span
        style={{
          position: "absolute",
          left: "10px",
          bottom: "10px",
          padding: "3px 9px",
          borderRadius: "6px",
          background: "rgba(22, 23, 29, 0.85)",
          fontSize: "10px",
          fontWeight: 700,
          letterSpacing: "0.6px",
          color: "#fff",
        }}
      >
        Before
      </span>
      <span
        style={{
          position: "absolute",
          right: "10px",
          top: "10px",
          padding: "3px 9px",
          borderRadius: "6px",
          background: "rgba(22, 23, 29, 0.85)",
          fontSize: "10px",
          fontWeight: 700,
          letterSpacing: "0.6px",
          color: "#fff",
        }}
      >
        After
      </span>

      {showHint && (
        <span
          style={{
            position: "absolute",
            top: "12px",
            left: "50%",
            transform: "translateX(-50%)",
            padding: "4px 12px",
            borderRadius: "100px",
            background: "rgba(22, 23, 29, 0.85)",
            fontSize: "10px",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          Drag to compare
        </span>
      )}
    </div>
  );
}
