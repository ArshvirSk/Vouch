"use client";

/**
 * Shared area/location state — one setting used by the home rail's
 * "Active in Your Area" panel and the Nearby page.
 *
 * Resolution order:
 *   1. A previously stored location (localStorage "vouch_area_v2") —
 *      either device-derived (source "geo") or manually picked (source
 *      "manual") — is used as-is.
 *   2. No stored location → the UI shows an explanation-first prompt
 *      ("Allow location"); clicking it is the user gesture that fires the
 *      browser's geolocation dialog. On grant we reverse-geocode via
 *      Nominatim and persist coords + display name.
 *   3. Denial / error / "not now" → session-scoped decline (sessionStorage,
 *      cleared when the tab closes) so we never nag more than once per
 *      session, and the app keeps working on the pilot default (Bandra
 *      West). The manual ward picker stays available everywhere.
 *
 * Query helper: when the resolved place snaps to a pilot ward we query
 * /area/activity by ward (exact pilot semantics); otherwise we pass raw
 * lat/lng and the backend haversine-filters around the user's position.
 */

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  ReactNode,
  useCallback,
} from "react";
import { reverseGeocode } from "./reverse-geocode";

export const PILOT_WARDS = [
  // Western suburbs
  { ward: "Bandra West", label: "Bandra West, Mumbai", lat: 19.0596, lng: 72.8295, pincode: "400050", radiusM: 2000 },
  { ward: "Bandra East", label: "Bandra East, Mumbai", lat: 19.0639, lng: 72.8483, pincode: "400051", radiusM: 2000 },
  { ward: "Khar", label: "Khar, Mumbai", lat: 19.0726, lng: 72.8364, pincode: "400052", radiusM: 2000 },
  { ward: "Santacruz West", label: "Santacruz West, Mumbai", lat: 19.0816, lng: 72.8416, pincode: "400054", radiusM: 2000 },
  { ward: "Vile Parle", label: "Vile Parle, Mumbai", lat: 19.1003, lng: 72.8426, pincode: "400056", radiusM: 2000 },
  { ward: "Juhu", label: "Juhu, Mumbai", lat: 19.0968, lng: 72.8267, pincode: "400049", radiusM: 2000 },
  { ward: "Andheri West", label: "Andheri West, Mumbai", lat: 19.1364, lng: 72.8296, pincode: "400058", radiusM: 2000 },
  { ward: "Andheri East", label: "Andheri East, Mumbai", lat: 19.1136, lng: 72.8697, pincode: "400069", radiusM: 2000 },
  { ward: "Jogeshwari", label: "Jogeshwari, Mumbai", lat: 19.1554, lng: 72.8518, pincode: "400060", radiusM: 2000 },
  { ward: "Goregaon", label: "Goregaon, Mumbai", lat: 19.1663, lng: 72.8526, pincode: "400062", radiusM: 2000 },
  { ward: "Malad", label: "Malad, Mumbai", lat: 19.1864, lng: 72.8493, pincode: "400064", radiusM: 2000 },
  { ward: "Kandivali", label: "Kandivali, Mumbai", lat: 19.2015, lng: 72.8526, pincode: "400067", radiusM: 2000 },
  { ward: "Borivali", label: "Borivali, Mumbai", lat: 19.2307, lng: 72.8567, pincode: "400066", radiusM: 2000 },
  { ward: "Dahisar", label: "Dahisar, Mumbai", lat: 19.2519, lng: 72.8618, pincode: "400068", radiusM: 2000 },
  // Central / South Mumbai
  { ward: "Colaba", label: "Colaba, Mumbai", lat: 18.9067, lng: 72.8147, pincode: "400005", radiusM: 2000 },
  { ward: "Fort", label: "Fort, Mumbai", lat: 18.9322, lng: 72.8331, pincode: "400001", radiusM: 2000 },
  { ward: "Marine Lines", label: "Marine Lines, Mumbai", lat: 18.944, lng: 72.823, pincode: "400020", radiusM: 2000 },
  { ward: "Girgaon", label: "Girgaon, Mumbai", lat: 18.9517, lng: 72.8156, pincode: "400006", radiusM: 2000 },
  { ward: "Byculla", label: "Byculla, Mumbai", lat: 18.9784, lng: 72.8341, pincode: "400027", radiusM: 2000 },
  { ward: "Worli", label: "Worli, Mumbai", lat: 19.0176, lng: 72.8155, pincode: "400018", radiusM: 2000 },
  { ward: "Lower Parel", label: "Lower Parel, Mumbai", lat: 18.9977, lng: 72.8273, pincode: "400013", radiusM: 2000 },
  { ward: "Dadar", label: "Dadar, Mumbai", lat: 19.0178, lng: 72.8478, pincode: "400014", radiusM: 2000 },
  { ward: "Mahim", label: "Mahim, Mumbai", lat: 19.038, lng: 72.843, pincode: "400016", radiusM: 2000 },
  { ward: "Sion", label: "Sion, Mumbai", lat: 19.0406, lng: 72.8656, pincode: "400022", radiusM: 2000 },
  // Eastern suburbs
  { ward: "Kurla", label: "Kurla, Mumbai", lat: 19.0728, lng: 72.8826, pincode: "400070", radiusM: 2000 },
  { ward: "Ghatkopar", label: "Ghatkopar, Mumbai", lat: 19.0863, lng: 72.9081, pincode: "400077", radiusM: 2000 },
  { ward: "Vikhroli", label: "Vikhroli, Mumbai", lat: 19.1085, lng: 72.9362, pincode: "400079", radiusM: 2000 },
  { ward: "Bhandup", label: "Bhandup, Mumbai", lat: 19.1416, lng: 72.9369, pincode: "400078", radiusM: 2000 },
  { ward: "Mulund", label: "Mulund, Mumbai", lat: 19.1726, lng: 72.9425, pincode: "400080", radiusM: 2000 },
  { ward: "Chembur", label: "Chembur, Mumbai", lat: 19.0522, lng: 72.9006, pincode: "400071", radiusM: 2000 },
  { ward: "Powai", label: "Powai, Mumbai", lat: 19.1176, lng: 72.906, pincode: "400076", radiusM: 2000 },
  // Extended metro
  { ward: "Vashi", label: "Vashi, Navi Mumbai", lat: 19.0771, lng: 72.9986, pincode: "400703", radiusM: 2500 },
  { ward: "Nerul", label: "Nerul, Navi Mumbai", lat: 19.0335, lng: 73.0197, pincode: "400706", radiusM: 2500 },
  { ward: "Thane", label: "Thane", lat: 19.2183, lng: 72.9781, pincode: "400601", radiusM: 2500 },
] as const;

export const DEFAULT_WARD = "Bandra West";

/** How the current area was chosen. */
export type AreaSource = "geo" | "manual" | "default";

export interface SelectedArea {
  /** Matched pilot ward if the place snapped to one, else a locality name. */
  ward: string;
  label: string;
  lat: number;
  lng: number;
  pincode: string | null;
  radiusM: number;
  source: AreaSource;
}

/** Pilot-ward metadata for a ward name (exact, case-insensitive). */
export function pilotWard(ward: string) {
  return PILOT_WARDS.find((w) => w.ward.toLowerCase() === ward.toLowerCase());
}

/** Build the default (pilot) area — the pre-location fallback. */
export function defaultArea(): SelectedArea {
  const w = PILOT_WARDS[0];
  return { ward: w.ward, label: w.label, lat: w.lat, lng: w.lng, pincode: w.pincode, radiusM: w.radiusM, source: "default" };
}

/** Build a manual-selection area from a pilot ward name. */
export function manualArea(ward: string): SelectedArea | null {
  const w = pilotWard(ward);
  if (!w) return null;
  return { ward: w.ward, label: w.label, lat: w.lat, lng: w.lng, pincode: w.pincode, radiusM: w.radiusM, source: "manual" };
}

/**
 * Query params for /area/activity for this area. Pilot-ward-snapped areas
 * (and manual picks) use exact ward matching; device-resolved areas that
 * didn't snap query by coordinates and let the backend radius-filter.
 */
export function areaActivityParams(
  area: SelectedArea,
  opts: { scaleKm?: number } = {}
): { ward?: string; lat?: number; lng?: number; scale_km?: number; radius_km?: number } {
  const snapped = pilotWard(area.ward) != null;
  if (snapped) {
    return { ward: area.ward, ...(opts.scaleKm ? { scale_km: opts.scaleKm } : {}) };
  }
  return {
    lat: area.lat,
    lng: area.lng,
    ...(opts.scaleKm ? { radius_km: opts.scaleKm } : {}),
  };
}

interface AreaContextType {
  area: SelectedArea;
  /** The device's actual coordinates, independent of the browsed area —
   *  rendered as the "you are here" dot on maps. Null when unknown. */
  deviceLocation: { lat: number; lng: number } | null;
  /** Lifecycle of the location prompt: idle until the provider decides. */
  geoStatus: "checking" | "prompt" | "locating" | "granted" | "declined" | "unsupported";
  /** Human-readable reason for the last decline (denied vs unavailable). */
  declineReason: string | null;
  requestLocation: () => void;
  /** Decline without triggering the browser dialog ("Not now"). */
  declineLocation: () => void;
  setWard: (ward: string) => void;
  /** True until the persisted value has been read (avoids hydration flicker). */
  ready: boolean;
}

const AreaContext = createContext<AreaContextType>({
  area: defaultArea(),
  deviceLocation: null,
  geoStatus: "checking",
  declineReason: null,
  requestLocation: () => {},
  declineLocation: () => {},
  setWard: () => {},
  ready: false,
});

const STORAGE_KEY = "vouch_area_v2";
const LEGACY_STORAGE_KEY = "vouch_area"; // pre-geolocation format: plain ward name
const DECLINE_KEY = "vouch_geo_declined"; // sessionStorage — one ask per session
/** Last known device fix, independent of the browsed area — the "you are
 *  here" dot survives manual ward switches and reloads. */
const DEVICE_FIX_KEY = "vouch_device_fix";

interface StoredArea {
  label: string;
  lat: number;
  lng: number;
  matchedWard: string | null;
  pincode: string | null;
  source: AreaSource;
}

function readStored(): SelectedArea | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const s = JSON.parse(raw) as StoredArea;
      if (
        typeof s.lat === "number" &&
        typeof s.lng === "number" &&
        typeof s.label === "string"
      ) {
        const pilot = s.matchedWard ? pilotWard(s.matchedWard) : undefined;
        return {
          ward: pilot ? pilot.ward : s.label,
          label: s.label,
          lat: s.lat,
          lng: s.lng,
          pincode: s.pincode ?? (pilot ? pilot.pincode : null),
          radiusM: pilot ? pilot.radiusM : 2000,
          source: s.source === "geo" || s.source === "manual" ? s.source : "manual",
        };
      }
    }
    // Migrate the pre-geolocation format (a bare ward name).
    const legacy = window.localStorage.getItem(LEGACY_STORAGE_KEY);
    if (legacy && pilotWard(legacy)) {
      return manualArea(legacy);
    }
  } catch {
    /* corrupted storage → fall through to default */
  }
  return null;
}

function persist(area: SelectedArea) {
  const s: StoredArea = {
    label: area.label,
    lat: area.lat,
    lng: area.lng,
    matchedWard: pilotWard(area.ward)?.ward ?? null,
    pincode: area.pincode,
    source: area.source,
  };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
}

function isDeclinedThisSession(): boolean {
  try {
    return window.sessionStorage.getItem(DECLINE_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Silent device-position refresh — no dialog (only works when permission
 * is already granted; errors are swallowed). Updates the "you are here"
 * dot without touching the browsed area.
 */
export function refreshDeviceFixSilently(
  onFix?: (loc: { lat: number; lng: number } | null) => void
): void {
  if (typeof navigator === "undefined" || !("geolocation" in navigator)) {
    onFix?.(null);
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const loc = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      onFix?.(loc);
    },
    () => onFix?.(null),
    { timeout: 8_000, maximumAge: 60_000 }
  );
}

function readDeviceFix(): { lat: number; lng: number } | null {
  try {
    const raw = window.localStorage.getItem(DEVICE_FIX_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw);
    return typeof v?.lat === "number" && typeof v?.lng === "number" ? v : null;
  } catch {
    return null;
  }
}

function persistDeviceFix(loc: { lat: number; lng: number }) {
  try {
    window.localStorage.setItem(DEVICE_FIX_KEY, JSON.stringify(loc));
  } catch {
    /* non-fatal */
  }
}

function markDeclinedThisSession(reason: string | null = null) {
  try {
    window.sessionStorage.setItem(DECLINE_KEY, "1");
  } catch {
    /* private mode — in-memory flag still limits nagging for this mount */
  }
}

export function AreaProvider({ children }: { children: ReactNode }) {
  const [area, setAreaState] = useState<SelectedArea>(defaultArea);
  const [deviceLocation, setDeviceLocation] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
  const [geoStatus, setGeoStatus] = useState<AreaContextType["geoStatus"]>("checking");
  const [declineReason, setDeclineReason] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const askedRef = useRef(false);

  useEffect(() => {
    // Restore the last known device fix regardless of how the area was
    // chosen — the dot tracks the device, not the browsed ward.
    const lastFix = readDeviceFix();
    if (lastFix) setDeviceLocation(lastFix);

    const applySilentFix = (loc: { lat: number; lng: number } | null) => {
      if (!loc) return;
      setDeviceLocation(loc);
      persistDeviceFix(loc);
    };

    const stored = readStored();
    if (stored) {
      setAreaState(stored);
      setGeoStatus("granted"); // a location (manual counts) is already known
      setReady(true);
      refreshDeviceFixSilently(applySilentFix);
      return;
    }
    setReady(true);

    const supported = "geolocation" in navigator;
    if (!supported) {
      setGeoStatus("unsupported");
      return;
    }
    // Respect a hard browser block without firing another dialog.
    if (typeof navigator.permissions?.query === "function") {
      navigator.permissions
        .query({ name: "geolocation" as PermissionName })
        .then((p) => {
          if (p.state === "denied" || isDeclinedThisSession()) {
            setGeoStatus("declined");
            setDeclineReason(p.state === "denied" ? "blocked" : null);
          } else {
            setGeoStatus("prompt");
          }
          if (p.state === "granted") {
            refreshDeviceFixSilently(applySilentFix);
          }
        })
        .catch(() => {
          setGeoStatus(isDeclinedThisSession() ? "declined" : "prompt");
        });
    } else {
      setGeoStatus(isDeclinedThisSession() ? "declined" : "prompt");
    }
  }, []);

  const decline = useCallback((reason: string | null) => {
    markDeclinedThisSession(reason);
    setDeclineReason(reason);
    setGeoStatus("declined");
  }, []);

  const declineLocation = useCallback(() => {
    decline("dismissed");
  }, [decline]);

  const requestLocation = useCallback(() => {
    if (askedRef.current) return; // one in-flight request at a time
    askedRef.current = true;
    setGeoStatus("locating");

    const finish = (err: string | null) => {
      askedRef.current = false;
      if (err) {
        decline(err);
      } else {
        setGeoStatus("granted");
      }
    };

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        // The device fix itself drives the "you are here" dot on maps,
        // wherever the user ends up browsing.
        const fix = { lat: latitude, lng: longitude };
        setDeviceLocation(fix);
        persistDeviceFix(fix);
        try {
          const place = await reverseGeocode({ lat: latitude, lng: longitude });
          const pilot = place.ward ? pilotWard(place.ward) : undefined;
          const next: SelectedArea = {
            ward: pilot ? pilot.ward : place.label,
            label: place.label,
            lat: latitude,
            lng: longitude,
            pincode: pilot ? pilot.pincode : place.raw.postcode ?? null,
            radiusM: pilot ? pilot.radiusM : 2000,
            source: "geo",
          };
          setAreaState(next);
          persist(next);
          finish(null);
        } catch {
          // Geocode failed but we still have good coordinates — use them
          // with a coordinate label rather than wasting the permission.
          const next: SelectedArea = {
            ward: defaultArea().ward,
            label: defaultArea().label,
            lat: latitude,
            lng: longitude,
            pincode: defaultArea().pincode,
            radiusM: defaultArea().radiusM,
            source: "geo",
          };
          setAreaState(next);
          persist(next);
          finish(null);
        }
      },
      (err) => {
        finish(
          err.code === err.PERMISSION_DENIED
            ? "denied"
            : err.code === err.POSITION_UNAVAILABLE || err.code === err.TIMEOUT
              ? "unavailable"
              : "error"
        );
      },
      { timeout: 12_000, maximumAge: 5 * 60 * 1000 }
    );
  }, [decline]);

  const setWard = useCallback((ward: string) => {
    const next = manualArea(ward);
    if (!next) return;
    setAreaState(next);
    persist(next);
    setGeoStatus("granted"); // a deliberate choice replaces the prompt
  }, []);

  return (
    <AreaContext.Provider
      value={{
        area,
        deviceLocation,
        geoStatus,
        declineReason,
        requestLocation,
        declineLocation,
        setWard,
        ready,
      }}
    >
      {children}
    </AreaContext.Provider>
  );
}

export function useSelectedArea() {
  return useContext(AreaContext);
}

/** Decline path for UI that never fires the browser dialog ("Not now"). */
export function useDeclineLocation() {
  return useContext(AreaContext).declineLocation;
}
