"use client";

/**
 * Client-side dynamic import of the actual Leaflet map. Leaflet touches
 * `window` at import time, so it must never load during SSR — pages import
 * this wrapper, not VouchMapInner.
 *
 * The loading placeholder is the old static-widget gradient so the panel
 * holds its shape while tiles load.
 */

import dynamic from "next/dynamic";
import type { VouchMapProps } from "./VouchMapInner";

export type { MapPin, AreaHighlight, UserLocationPoint } from "./VouchMapInner";

const VouchMapInner = dynamic(() => import("./VouchMapInner"), {
  ssr: false,
  loading: () => (
    <div
      className="vouch-map vouch-map-loading"
      style={{
        background: "linear-gradient(135deg, #1A1C24 0%, #22242E 60%, #1A1C24 100%)",
      }}
    />
  ),
});

export function VouchMap(props: VouchMapProps) {
  return <VouchMapInner {...props} />;
}
