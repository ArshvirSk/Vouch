"use client";

/**
 * HomeRightRail — redesign stage 4. Home-only right column:
 * - Quick Create: two rows linking into /create?type=civic|vendor
 * - Your Impact: 2x2 stat grid — all four values are real backend fields
 *   (profile stats: evidence_submitted / total_votes_cast /
 *   commitments_authored / reputation_score)
 * - Active in Your Area: real Leaflet map (shared VouchMap component) with
 *   civic/vendor pins + stats from GET /area/activity (ward-scoped counts)
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
  ChevronDown,
} from "lucide-react";
import { getUserProfile, getAreaActivity } from "@/lib/api";
import { VouchMap } from "@/components/VouchMap";
import {
  PILOT_WARDS,
  useSelectedArea,
  areaActivityParams,
  pilotWard,
} from "@/lib/area-context";
import { LocateFixed } from "lucide-react";

const REFRESH_MS = 60_000;

export function HomeRightRail() {
  const { area, deviceLocation, setWard, requestLocation, geoStatus, ready: areaReady } = useSelectedArea();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [stats, setStats] = useState({
    contributions: 0,
    jurorVotes: 0,
    promisesTracked: 0,
    reputation: 0,
  });
  const [loaded, setLoaded] = useState(false);
  const [areaData, setAreaData] = useState<{
    civic: number;
    vendor: number;
    inVerification: number;
    pins: Parameters<typeof VouchMap>[0]["pins"];
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const handle = localStorage.getItem("vouch_handle");
      if (!handle) return;
      try {
        const profile = await getUserProfile(handle);
        if (cancelled) return;
        setStats({
          // Evidence submissions by this user (backend: evidence_submitted)
          contributions: profile.stats.evidence_submitted ?? 0,
          // Real backend field
          jurorVotes: profile.stats.total_votes_cast ?? 0,
          // Commitments authored by this user (backend: commitments_authored)
          promisesTracked: profile.stats.commitments_authored ?? 0,
          reputation: profile.user.reputation_score ?? 0,
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

  // Area activity — real query backing the map pins + stat row. Queries by
  // ward when the area snapped to a pilot ward, by coordinates otherwise.
  useEffect(() => {
    if (!areaReady) return;
    let cancelled = false;
    async function load() {
      try {
        const data = await getAreaActivity(areaActivityParams(area));
        if (cancelled) return;
        setAreaData({
          civic: data.civic_count,
          vendor: data.vendor_count,
          inVerification: data.in_verification_count,
          pins: data.pins,
        });
      } catch {
        if (!cancelled) setAreaData(null);
      }
    }
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [areaReady, area.ward, area.lat, area.lng]);

  return (
    <aside
      style={{
        width: "380px",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        gap: "18px",
        paddingTop: "24px",
        position: "sticky",
        top: "70px",
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
            { icon: ClipboardList, value: stats.contributions, label: "Contributions" },
            { icon: Vote, value: stats.jurorVotes, label: "Juror votes" },
            { icon: BarChart3, value: stats.promisesTracked, label: "Promises tracked" },
            { icon: Star, value: stats.reputation, label: "Reputation score" },
          ].map(({ icon: Icon, value, label }) => (
            <div
              key={label}
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
            onClick={(e) => {
              e.preventDefault();
              setPickerOpen((v) => !v);
            }}
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
            position: "relative",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "var(--font-caption)",
            color: "var(--text-secondary)",
            marginBottom: "12px",
          }}
        >
          <MapPin size={13} /> {area.label}
          {area.source === "geo" && (
            <span
              title="Set from your device location — change any time"
              style={{
                fontSize: "9px",
                color: "var(--accent-primary)",
                border: "1px solid rgba(255, 107, 53, 0.35)",
                borderRadius: "100px",
                padding: "1px 7px",
              }}
            >
              GPS
            </span>
          )}

          {/* Ward picker — manual override; location sets the default only */}
          {pickerOpen && (
            <div
              style={{
                position: "absolute",
                top: "100%",
                left: 0,
                zIndex: 30,
                minWidth: "220px",
                maxHeight: "340px",
                overflowY: "auto",
                background: "var(--bg-surface-raised)",
                border: "1px solid var(--border-color)",
                borderRadius: "10px",
                boxShadow: "0 6px 20px rgba(0,0,0,0.5)",
                marginTop: "4px",
              }}
            >
              {geoStatus !== "granted" && area.source !== "geo" && (
                <button
                  onClick={() => {
                    requestLocation();
                    setPickerOpen(false);
                  }}
                  disabled={geoStatus === "locating"}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    width: "100%",
                    textAlign: "left",
                    padding: "10px 14px",
                    background: "transparent",
                    color: "var(--accent-primary)",
                    border: "none",
                    borderBottom: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                    fontSize: "var(--font-caption)",
                    fontWeight: 600,
                    opacity: geoStatus === "locating" ? 0.6 : 1,
                  }}
                >
                  <LocateFixed size={14} /> Use my location
                </button>
              )}
              {PILOT_WARDS.map((w) => {
                const active = area.ward === w.ward || (pilotWard(area.ward)?.ward === w.ward && area.source === "geo");
                return (
                <button
                  key={w.ward}
                  onClick={() => {
                    setWard(w.ward);
                    setPickerOpen(false);
                  }}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    padding: "10px 14px",
                    background:
                      active ? "rgba(255, 107, 53, 0.12)" : "transparent",
                    color: active ? "var(--accent-primary)" : "var(--text-primary)",
                    border: "none",
                    borderBottom: "1px solid var(--border-subtle)",
                    cursor: "pointer",
                    fontSize: "var(--font-caption)",
                  }}
                >
                  {w.label}
                </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Real map preview — pins at their actual lat/lng via shared VouchMap.
            Non-interactive: this is a sidebar glance, not the main event. */}
        <div
          style={{
            position: "relative",
            height: "150px",
            borderRadius: "12px",
            overflow: "hidden",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <VouchMap
            pins={areaReady && areaData ? areaData.pins : []}
            // Centre on the device fix when known so the blue "you are
            // here" dot sits mid-panel, not wherever the ward centroid is.
            center={
              deviceLocation
                ? [deviceLocation.lat, deviceLocation.lng]
                : [area.lat, area.lng]
            }
            zoom={14}
            interactive={false}
            userLocation={areaReady ? deviceLocation : null}
          />
        </div>

        {/* Area stat row — real ward-scoped counts from /area/activity */}
        <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
          {[
            { value: areaData?.civic ?? "–", label: "Civic promises" },
            { value: areaData?.vendor ?? "–", label: "Vendors" },
            { value: areaData?.inVerification ?? "–", label: "In verification" },
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
