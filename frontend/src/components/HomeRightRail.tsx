"use client";

/**
 * HomeRightRail — redesign stage 4. Home-only right column:
 * - Quick Create: two rows linking into /create?type=civic|vendor
 * - Your Impact: 2x2 stat grid (reputation + juror votes are real backend
 *   fields; contributions + promises tracked are placeholders pending
 *   backend work — flagged in code)
 * - Active in Your Area: map widget with civic/vendor pin clusters + stats
 */

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Landmark,
  Briefcase,
  ChevronRight,
  ClipboardList,
  Vote,
  BarChart3,
  Star,
  MapPin,
} from "lucide-react";
import { getUserProfile } from "@/lib/api";

const REFRESH_MS = 60_000;

export function HomeRightRail() {
  const [stats, setStats] = useState({
    contributions: 0,
    jurorVotes: 0,
    promisesTracked: 0,
    reputation: 0,
  });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const handle = localStorage.getItem("vouch_handle");
      if (!handle) return;
      try {
        const profile = await getUserProfile(handle);
        if (cancelled) return;
        setStats({
          // Real backend field
          reputation: profile.user.reputation_score ?? 0,
          // Real backend field
          jurorVotes: profile.stats.total_votes_cast ?? 0,
          // PLACEHOLDER: no backend field yet — contributions = distinct
          // evidence submissions is the intended definition (stage 4 backend)
          contributions: profile.stats.commitments_total ?? 0,
          // PLACEHOLDER: promises tracked = commitments authored so far
          promisesTracked: profile.stats.commitments_total ?? 0,
        });
      } catch {
        /* keep zeros */
      } finally {
        if (!cancelled) setLoaded(true);
      }
    }
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  return (
    <aside
      style={{
        width: "300px",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        gap: "18px",
        paddingTop: "24px",
        paddingRight: "24px",
      }}
    >
      {/* ── Quick Create ── */}
      <section className="card" style={{ padding: "18px" }}>
        <h3 style={{ fontSize: "var(--font-subtitle)", fontWeight: 700, margin: 0 }}>
          Quick Create
        </h3>
        <p
          style={{
            fontSize: "var(--font-caption)",
            color: "var(--text-secondary)",
            margin: "2px 0 14px",
          }}
        >
          Log a new commitment
        </p>

        {[
          {
            href: "/create?type=civic",
            icon: Landmark,
            title: "Civic promise",
            sub: "Add a promise by a public representative",
          },
          {
            href: "/create?type=vendor",
            icon: Briefcase,
            title: "Vendor commitment",
            sub: "Add a service or project commitment",
          },
        ].map(({ href, icon: Icon, title, sub }) => (
          <Link
            key={href}
            href={href}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "12px",
              borderRadius: "12px",
              border: "1px solid var(--border-subtle)",
              background: "var(--bg-surface-raised)",
              textDecoration: "none",
              marginBottom: "10px",
              transition: "border-color 0.2s ease",
            }}
          >
            <span
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "9px",
                background: "rgba(255, 107, 53, 0.14)",
                color: "var(--accent-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Icon size={16} />
            </span>
            <span style={{ flex: 1, minWidth: 0 }}>
              <span
                style={{
                  display: "block",
                  fontWeight: 600,
                  fontSize: "var(--font-caption)",
                  color: "var(--text-primary)",
                }}
              >
                {title}
              </span>
              <span
                style={{
                  display: "block",
                  fontSize: "11px",
                  color: "var(--text-secondary)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {sub}
              </span>
            </span>
            <ChevronRight size={15} color="var(--text-secondary)" />
          </Link>
        ))}
      </section>

      {/* ── Your Impact ── */}
      <section className="card" style={{ padding: "18px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "12px",
          }}
        >
          <h3 style={{ fontSize: "var(--font-subtitle)", fontWeight: 700, margin: 0 }}>
            Your Impact
          </h3>
          <Link
            href="/profile/me"
            style={{
              color: "var(--accent-primary)",
              textDecoration: "none",
              fontSize: "var(--font-caption)",
              fontWeight: 600,
            }}
          >
            View profile →
          </Link>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
          {[
            { icon: ClipboardList, value: stats.contributions, label: "Contributions", real: false },
            { icon: Vote, value: stats.jurorVotes, label: "Juror votes", real: true },
            { icon: BarChart3, value: stats.promisesTracked, label: "Promises tracked", real: false },
            { icon: Star, value: stats.reputation, label: "Reputation score", real: true },
          ].map(({ icon: Icon, value, label, real }) => (
            <div
              key={label}
              title={real ? undefined : `${label}: placeholder — backend field pending`}
              style={{
                border: "1px solid var(--border-subtle)",
                borderRadius: "12px",
                background: "var(--bg-surface-raised)",
                padding: "12px",
              }}
            >
              <Icon size={15} color="var(--accent-primary)" style={{ marginBottom: "6px" }} />
              <div style={{ fontWeight: 700, fontSize: "var(--font-subtitle)" }}>
                {loaded ? value : "–"}
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Active in Your Area ── */}
      <section className="card" style={{ padding: "18px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "2px",
          }}
        >
          <h3 style={{ fontSize: "var(--font-subtitle)", fontWeight: 700, margin: 0 }}>
            Active in Your Area
          </h3>
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            style={{
              color: "var(--accent-primary)",
              textDecoration: "none",
              fontSize: "var(--font-caption)",
              fontWeight: 600,
            }}
          >
            Change
          </a>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "var(--font-caption)",
            color: "var(--text-secondary)",
            marginBottom: "12px",
          }}
        >
          <MapPin size={13} /> Bandra West, Mumbai
        </div>

        {/* Map widget with pin clusters (static stand-in — no map SDK yet) */}
        <div
          style={{
            position: "relative",
            height: "150px",
            borderRadius: "12px",
            overflow: "hidden",
            border: "1px solid var(--border-subtle)",
            background:
              "linear-gradient(135deg, #1A1C24 0%, #22242E 60%, #1A1C24 100%)",
          }}
        >
          {/* Faint street-grid hint */}
          <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.25 }}>
            <path d="M0 40 L300 60" stroke="var(--border-subtle)" strokeWidth="2" />
            <path d="M0 100 L300 90" stroke="var(--border-subtle)" strokeWidth="2" />
            <path d="M80 0 L110 150" stroke="var(--border-subtle)" strokeWidth="2" />
            <path d="M200 0 L180 150" stroke="var(--border-subtle)" strokeWidth="2" />
          </svg>

          {[
            { x: "22%", y: "30%", kind: "civic" },
            { x: "58%", y: "22%", kind: "vendor" },
            { x: "44%", y: "58%", kind: "vendor" },
            { x: "74%", y: "62%", kind: "civic" },
          ].map((pin, i) => (
            <span
              key={i}
              style={{
                position: "absolute",
                left: pin.x,
                top: pin.y,
                width: "26px",
                height: "26px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background:
                  pin.kind === "civic"
                    ? "var(--accent-primary)"
                    : "var(--accent-verified)",
                color: "#0E0F14",
                boxShadow: "0 2px 8px rgba(0,0,0,0.5)",
              }}
              title={pin.kind === "civic" ? "Civic commitment" : "Vendor commitment"}
            >
              {pin.kind === "civic" ? <Landmark size={13} /> : <Briefcase size={13} />}
            </span>
          ))}
        </div>

        {/* Area stat row (placeholder counts until a ward-scoped query exists) */}
        <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
          {[
            { value: 18, label: "Civic promises" },
            { value: 27, label: "Vendors" },
            { value: 5, label: "In verification" },
          ].map(({ value, label }) => (
            <div
              key={label}
              style={{
                flex: 1,
                border: "1px solid var(--border-subtle)",
                borderRadius: "10px",
                background: "var(--bg-surface-raised)",
                padding: "8px",
                textAlign: "center",
              }}
            >
              <div style={{ fontWeight: 700 }}>{value}</div>
              <div style={{ fontSize: "10px", color: "var(--text-secondary)" }}>{label}</div>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}
