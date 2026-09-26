"use client";

/**
 * Nearby — the explorable map view of local commitments.
 *
 * - Large interactive VouchMap (pan/zoom) centered on the selected area
 *   (shared area state — Home's "Change" control drives this too), with a
 *   dashed outline + distinct marker marking the home base
 * - Wider radius than the home panel via /area/activity?scale_km=… so
 *   neighboring pilot wards are visible
 * - Filter row (All / Civic / Vendors) reusing the feed's .pill component
 * - List of the same filtered commitments below the map using the
 *   existing CommitmentFeedCard, so the page works as map + feed
 */

import { useEffect, useMemo, useState } from "react";
import { MapPin } from "lucide-react";
import { getAreaActivity, type AreaPin } from "@/lib/api";
import { VouchMap } from "@/components/VouchMap";
import { CommitmentFeedCard } from "@/components/CommitmentFeedCard";
import { useSelectedArea, areaActivityParams, pilotWard } from "@/lib/area-context";
// deviceLocation comes from the same context object below
import type { Commitment } from "@/lib/api";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "civic", label: "Civic" },
  { key: "vendor", label: "Vendors" },
] as const;

type FilterKey = (typeof FILTERS)[number]["key"];

/** How far around the home area the Nearby map reaches (km) — city-wide:
 *  covers Dahisar→Colaba and out to Thane/Navi Mumbai. */
const NEARBY_SCALE_KM = 40;

/** Widen the ward-scoped /area/activity query into full commitments. */
async function listCommitmentsRaw(): Promise<Commitment[]> {
  const { listCommitments } = await import("@/lib/api");
  const data = await listCommitments({ limit: 100 });
  return data.commitments.filter((c) => c.ward); // only placeable ones
}

export default function NearbyPage() {
  const { area, deviceLocation, ready: areaReady } = useSelectedArea();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [pins, setPins] = useState<AreaPin[]>([]);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [loading, setLoading] = useState(true);

  // Map pins: wider radius around the selected area — ward-scoped with a
  // neighbor-including scale for pilot wards, pure radius for geo-resolved
  // areas that didn't snap to one.
  useEffect(() => {
    if (!areaReady) return;
    let cancelled = false;
    setLoading(true);
    const snapped = pilotWard(area.ward) != null;
    const params = snapped
      ? { ward: area.ward, scale_km: NEARBY_SCALE_KM }
      : { lat: area.lat, lng: area.lng, radius_km: NEARBY_SCALE_KM };
    getAreaActivity(params)
      .then((data) => {
        if (!cancelled) setPins(data.pins);
      })
      .catch(() => {
        if (!cancelled) setPins([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [areaReady, area.ward, area.lat, area.lng]);

  // List view: full commitment cards (feed needs fields pins don't carry).
  useEffect(() => {
    let cancelled = false;
    listCommitmentsRaw()
      .then((rows) => {
        if (!cancelled) setCommitments(rows);
      })
      .catch(() => {
        if (!cancelled) setCommitments([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredPins = useMemo(
    () => (filter === "all" ? pins : pins.filter((p) => p.category === filter)),
    [pins, filter]
  );

  // The list shows exactly what the map shows: only commitments inside the
  // same radius the pins come from, home-ward first.
  const filteredCommitments = useMemo(() => {
    const visibleIds = new Set(filteredPins.map((p) => p.id));
    return commitments
      .filter((c) => visibleIds.has(c.id))
      .filter((c) => filter === "all" || c.category === filter)
      .sort((a, b) => {
        const homeWard = pilotWard(area.ward)?.ward ?? area.ward;
        return (
          (a.ward === homeWard ? 0 : 1) - (b.ward === homeWard ? 0 : 1) ||
          a.title.localeCompare(b.title)
        );
      });
  }, [commitments, filteredPins, filter, area.ward]);

  const visibleCount = filteredPins.length;

  return (
    <div className="shell-content" style={{ paddingBottom: "40px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <h1 style={{ fontSize: "var(--font-display)", fontWeight: 700, marginBottom: "4px" }}>
            Nearby
          </h1>
          <p style={{ color: "var(--text-secondary)", margin: 0 }}>
            Everything local to your area — civic and vendor promises blended.
          </p>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "var(--font-caption)",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "100px",
            padding: "7px 14px",
            background: "var(--bg-surface-raised)",
          }}
        >
          <MapPin size={13} color="var(--accent-primary)" /> {area.label}
        </div>
      </div>

      {/* Filter row — same .pill component as the Recent Commitments feed */}
      <div style={{ display: "flex", gap: "4px", margin: "18px 0 14px", flexWrap: "wrap" }}>
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`pill ${filter === f.key ? "active" : ""}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
        <span
          style={{
            marginLeft: "auto",
            fontSize: "var(--font-caption)",
            color: "var(--text-secondary)",
            alignSelf: "center",
          }}
        >
          {loading
            ? "Loading…"
            : `${visibleCount} commitments within ${NEARBY_SCALE_KM} km of ${area.ward}`}
        </span>
      </div>

      {/* Main interactive map */}
      <div
        style={{
          height: "440px",
          borderRadius: "14px",
          overflow: "hidden",
          border: "1px solid var(--border-subtle)",
          marginBottom: "20px",
        }}
      >
        <VouchMap
          pins={areaReady ? filteredPins : []}
          center={[area.lat, area.lng]}
          zoom={11}
          interactive
          highlightArea={
            areaReady
              ? {
                  // The home-area outline follows the device fix — "my
                  // location" — so the circle rings the blue dot. Falls back
                  // to the browsed-area center when no device fix is known.
                  lat: deviceLocation?.lat ?? area.lat,
                  lng: deviceLocation?.lng ?? area.lng,
                  radiusM: area.radiusM,
                  label: area.label,
                }
              : null
          }
          userLocation={areaReady ? deviceLocation : null}
        />
      </div>

      {/* List view of the same commitments visible on the map (map + feed,
          always in sync) */}
      <h2 style={{ fontSize: "var(--font-title)", fontWeight: 700, margin: "0 0 14px" }}>
        {filter === "all" ? "All nearby commitments" : filter === "civic" ? "Civic nearby" : "Vendors nearby"}
      </h2>
      {loading ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-secondary)" }}>
          Loading commitments…
        </div>
      ) : filteredCommitments.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-secondary)" }}>
          Nothing here for this filter yet.
        </div>
      ) : (
        filteredCommitments.map((c) => <CommitmentFeedCard key={c.id} commitment={c} />)
      )}
    </div>
  );
}
