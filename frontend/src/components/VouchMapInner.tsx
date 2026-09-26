"use client";

/**
 * VouchMapInner — the actual Leaflet map (loaded client-side only via the
 * VouchMap.tsx dynamic wrapper).
 *
 * - CartoDB "dark_matter" raster tiles (OSM data, no API key) to match the
 *   app's dark theme
 * - Commitments are plotted at their real lat/lng from GET /area/activity
 *   as circular category markers: orange civic (Landmark) / mint vendor
 *   (Briefcase) — same tokens the old static widget used
 * - Clicking a marker opens a popup with the title, status badge and a
 *   link to the commitment detail page
 */

import { useEffect, useRef } from "react";
import { divIcon } from "leaflet";
import {
  Circle,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  ZoomControl,
  useMap,
} from "react-leaflet";
import { renderToStaticMarkup } from "react-dom/server";
import Link from "next/link";
import { Landmark, Briefcase, MapPin } from "lucide-react";
import { getStatusLabel } from "@/lib/utils";
import "leaflet/dist/leaflet.css";
import "./VouchMap.css";

/**
 * Basemap — keyless by default.
 *
 * CARTO's dark_matter raster tiles used to be the free keyless choice, but
 * as of Aug 2026 basemaps.cartocdn.com serves an "API KEY REQUIRED"
 * watermark to anonymous requests (the free key now comes via email). The
 * keyless default below is Esri's World Dark Gray Canvas (base + labels
 * reference layer) — dark, city-level detail, no account, no billing.
 *
 * To switch to CARTO dark_matter later: get their free basemaps key and set
 * NEXT_PUBLIC_MAP_TILE_URL=https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?apikey=YOUR_KEY
 * (restart the dev server; no code change needed).
 */
const CUSTOM_TILE_URL = process.env.NEXT_PUBLIC_MAP_TILE_URL;

const ESRI_DARK_BASE =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
const ESRI_DARK_LABELS =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}";
const ESRI_ATTRIBUTION =
  'Tiles &copy; Esri — Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), &copy; OpenStreetMap contributors, GIS User Community';
const GENERIC_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const STATUS_CLASS: Record<string, string> = {
  open: "open",
  evidence_submitted: "evidence_submitted",
  in_verification: "in_verification",
  met: "met",
  broken: "broken",
  disputed: "disputed",
  expired: "expired",
};

export interface MapPin {
  id: string;
  category: "civic" | "vendor" | "personal";
  title: string;
  ward: string | null;
  status: string;
  lat: number;
  lng: number;
}

export interface AreaHighlight {
  lat: number;
  lng: number;
  /** Radius in metres — drawn as a dashed outline around the home area. */
  radiusM: number;
  label: string;
}

/** The device's real position — rendered as a pulsing "you are here" dot. */
export interface UserLocationPoint {
  lat: number;
  lng: number;
}

function userDotIcon(): ReturnType<typeof divIcon> {
  return divIcon({
    className: "vouch-pin-wrapper",
    html: '<span class="vouch-user-dot"></span>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

/** Rough haversine distance in metres — good enough for marker declutter. */
function distanceM(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const R = 6371000;
  const p1 = (a.lat * Math.PI) / 180;
  const p2 = (b.lat * Math.PI) / 180;
  const dp = ((b.lat - a.lat) * Math.PI) / 180;
  const dl = ((b.lng - a.lng) * Math.PI) / 180;
  const h =
    Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function pinIcon(category: string, isHome: boolean): ReturnType<typeof divIcon> {
  const isCivic = category === "civic";
  const Icon = isCivic ? Landmark : Briefcase;
  const size = isHome ? 36 : 26;
  const bg = isHome
    ? "var(--text-primary)" // home-base marker stands apart from category pins
    : isCivic
      ? "var(--accent-primary)"
      : "var(--accent-verified)";
  return divIcon({
    className: "vouch-pin-wrapper",
    html: renderToStaticMarkup(
      <span
        style={{
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: bg,
          color: "#0E0F14",
          border: isHome ? "2px solid var(--bg-primary)" : "none",
          boxShadow: "0 2px 8px rgba(0,0,0,0.5)",
        }}
      >
        {isHome ? <MapPin size={size - 16} /> : <Icon size={size - 13} />}
      </span>
    ),
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

/**
 * Floating "show my position" control for interactive maps — pans to the
 * device dot when the browsed area has left it off-screen.
 */
function LocateControl({ target }: { target: { lat: number; lng: number } | null }) {
  const map = useMap();
  if (!target) return null;
  return (
    <button
      className="vouch-locate-btn"
      title="Show my location"
      aria-label="Show my location"
      onClick={(e) => {
        e.preventDefault();
        map.flyTo([target.lat, target.lng], Math.max(map.getZoom(), 14), {
          duration: 0.8,
        });
      }}
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
        <circle cx="12" cy="12" r="7" />
      </svg>
    </button>
  );
}

/**
 * Pan the map when the `center` prop changes after mount — react-leaflet
 * only honours `center` on first render. Lets callers re-centre on the
 * device fix when it arrives asynchronously (e.g. the silent geo refresh)
 * and makes ward switches animate to the new area.
 */
function MapRecenter({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  const last = useRef<string | null>(null);
  useEffect(() => {
    const key = `${lat},${lng}`;
    // First run: MapContainer was already created at this center — skip so
    // we never fight the initial layout.
    if (last.current === null) {
      last.current = key;
      return;
    }
    if (last.current === key) return;
    last.current = key;
    map.panTo([lat, lng], { animate: true });
  }, [lat, lng, map]);
  return null;
}

export interface VouchMapProps {
  pins: MapPin[];
  center: [number, number];
  zoom: number;
  /** Show +/- buttons and enable pan/zoom interactions (Nearby). */
  interactive?: boolean;
  /** Draw the home-base outline + distinct marker at the given point. */
  highlightArea?: AreaHighlight | null;
  /** The device's actual position — "you are here" dot. */
  userLocation?: UserLocationPoint | null;
  className?: string;
}

export default function VouchMapInner({
  pins,
  center,
  zoom,
  interactive = true,
  highlightArea = null,
  userLocation = null,
  className,
}: VouchMapProps) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      className={`vouch-map ${className ?? ""}`}
      zoomControl={false}
      scrollWheelZoom={interactive}
      dragging={interactive}
      touchZoom={interactive}
      doubleClickZoom={interactive}
      keyboard={interactive}
      attributionControl={interactive}
    >
      {CUSTOM_TILE_URL ? (
        <TileLayer
          url={CUSTOM_TILE_URL}
          attribution={GENERIC_ATTRIBUTION}
          maxZoom={20}
        />
      ) : (
        <>
          <TileLayer
            url={ESRI_DARK_BASE}
            attribution={ESRI_ATTRIBUTION}
            maxNativeZoom={16}
            maxZoom={20}
          />
          {/* Street/place labels overlay */}
          <TileLayer
            url={ESRI_DARK_LABELS}
            opacity={0.9}
            maxNativeZoom={16}
            maxZoom={20}
          />
        </>
      )}
      {interactive && <ZoomControl position="bottomright" />}
      {interactive && <LocateControl target={userLocation} />}
      <MapRecenter lat={center[0]} lng={center[1]} />

      {highlightArea && (
        <>
          <Circle
            center={[highlightArea.lat, highlightArea.lng]}
            radius={highlightArea.radiusM}
            pathOptions={{
              color: "#f5f6f8",
              weight: 1.5,
              opacity: 0.8,
              fillColor: "#f5f6f8",
              fillOpacity: 0.06,
              dashArray: "4 4",
            }}
          />
          {/* When the device fix IS the area center (geo-resolved area), the
              blue "you are here" dot already marks it — skip the redundant
              white home pin so they don't stack. */}
          {!(
            userLocation &&
            distanceM(userLocation, highlightArea) < 100
          ) && (
            <Marker
              position={[highlightArea.lat, highlightArea.lng]}
              icon={pinIcon("home", true)}
              zIndexOffset={500}
              interactive={false}
            />
          )}
        </>
      )}

      {/* "You are here" dot — the device's real position, above all pins */}
      {userLocation && (
        <Marker
          position={[userLocation.lat, userLocation.lng]}
          icon={userDotIcon()}
          zIndexOffset={1000}
          interactive={false}
        />
      )}

      {pins.map((pin) => {
        const isCivic = pin.category === "civic";
        return (
          <Marker key={pin.id} position={[pin.lat, pin.lng]} icon={pinIcon(pin.category, false)}>
            <Popup>
              <div className="vouch-popup">
                <span className={`verdict-badge ${STATUS_CLASS[pin.status] ?? ""}`}>
                  {getStatusLabel(pin.status)}
                </span>
                <strong className="vouch-popup-title">{pin.title}</strong>
                {pin.ward && <span className="vouch-popup-ward">{pin.ward}</span>}
                <Link href={`/commitment/${pin.id}`} className="vouch-popup-link">
                  View commitment →
                </Link>
              </div>
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
