"use client";

/**
 * LocationPrompt — the explanation-first consent banner.
 *
 * Browsers fire the geolocation permission dialog on the user gesture, so
 * the banner explains WHY first ("Vouch shows civic promises and vendor
 * commitments near you…") and only requests on click. Shown when no
 * location is known; hides itself for the session on decline so the app
 * never nags more than once per session.
 */

import { useSelectedArea, useDeclineLocation } from "@/lib/area-context";
import { MapPin, X, Loader2 } from "lucide-react";

export function LocationPrompt() {
  const { area, geoStatus, requestLocation, ready } = useSelectedArea();
  const decline = useDeclineLocation();

  if (!ready) return null;
  if (area.source !== "default") return null; // a location is already known
  if (geoStatus !== "prompt" && geoStatus !== "locating") return null;

  return (
    <div
      className="card animate-in"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "14px 16px",
        marginBottom: "16px",
        border: "1px solid rgba(255, 107, 53, 0.35)",
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
        <MapPin size={16} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: "var(--font-caption)" }}>
          See what&apos;s active in your ward
        </div>
        <div style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
          Vouch shows civic promises and vendor commitments near you — allow
          location to see what&apos;s active in your ward.
        </div>
      </div>
      {geoStatus === "locating" ? (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "var(--font-caption)",
            color: "var(--text-secondary)",
            flexShrink: 0,
          }}
        >
          <Loader2 size={14} className="spin" /> Locating…
        </span>
      ) : (
        <button
          className="btn btn-primary"
          onClick={requestLocation}
          style={{ padding: "8px 16px", fontSize: "var(--font-caption)", flexShrink: 0 }}
        >
          Allow location
        </button>
      )}
      <button
        onClick={decline}
        title="Not now"
        aria-label="Not now"
        style={{
          background: "none",
          border: "none",
          color: "var(--text-secondary)",
          cursor: "pointer",
          display: "flex",
          padding: "4px",
          flexShrink: 0,
        }}
      >
        <X size={16} />
      </button>
    </div>
  );
}
