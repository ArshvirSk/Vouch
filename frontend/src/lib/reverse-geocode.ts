/**
 * Reverse geocoding via Nominatim (OpenStreetMap's free service) — no API
 * key, consistent with the app's OSM-based map stack.
 *
 * Usage policy: https://operations.osmfoundation.org/policies/nominatim/ —
 * max 1 req/s, and requests must identify the app. Browsers send the
 * Referer header automatically (Nominatim accepts it); the UA cannot be
 * overridden from the browser (forbidden header name).
 *
 * INDIA ACCURACY FLAG (PRD geography model is ward/pincode-based):
 * Nominatim gives free locality/suburb-level names in Indian metros
 * (e.g. "Bandra West", "Khar") which is usually right for our pilot
 * wards, but municipal *ward numbers/names* (Ward 104 etc.) are often
 * missing or stale in OSM India. If ward-exact resolution ever matters
 * (eligibility for ward juries), a paid geocoder would help:
 *   - Google Geocoding API: best-in-class for Indian localities, has
 *     `sublocality_level_1` which maps well to our pilot wards — but
 *     billing account required (ruled out for this MVP).
 *   - MapmyIndia (now Mappls) — the strongest option for Indian ward/
 *     pincode accuracy specifically, made in India, has a free dev tier.
 * Recommendation stays Nominatim for now: free, keyless, and our pilot
 * ward list is small enough to snap the result to a known ward.
 */

import { PILOT_WARDS } from "./area-context";

export interface GeoLocation {
  lat: number;
  lng: number;
}

export interface ResolvedPlace {
  /** Display name for the area chip, e.g. "Bandra West, Mumbai". */
  label: string;
  /** Matched pilot ward if the point falls in/near one, else null. */
  ward: string | null;
  /** Raw locality fields from Nominatim, for debugging/inspection. */
  raw: {
    suburb?: string;
    neighbourhood?: string;
    city_district?: string;
    city?: string;
    town?: string;
    state_district?: string;
    state?: string;
    postcode?: string;
  };
}

const NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse";

export async function reverseGeocode(loc: GeoLocation): Promise<ResolvedPlace> {
  const params = new URLSearchParams({
    lat: String(loc.lat),
    lon: String(loc.lng),
    format: "jsonv2",
    addressdetails: "1",
    zoom: "16", // suburb/locality level — ward-ish granularity
  });

  const res = await fetch(`${NOMINATIM_REVERSE}?${params}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`Nominatim error ${res.status}`);
  const data = await res.json();
  const a = data.address ?? {};

  // Best available locality name for Indian metro addresses, most
  // specific first.
  const locality =
    a.suburb || a.neighbourhood || a.city_district || a.quarter || a.village || null;
  const city = a.city || a.town || a.state_district || null;

  // Snap to a pilot ward when the locality matches one (case-insensitive
  // contains, e.g. "Bandra West" ⊂ "Bandra West, Mumbai" or "Khar West"
  // matching suburb "Khar"). Also match by postcode when Nominatim
  // returns one of our pilot pincodes.
  const byName = locality
    ? PILOT_WARDS.find(
        (w) =>
          locality.toLowerCase().includes(w.ward.toLowerCase().replace(" West", "")) ||
          w.ward.toLowerCase().includes(locality.toLowerCase())
      )
    : undefined;
  const byPin = a.postcode
    ? PILOT_WARDS.find((w) => w.pincode === a.postcode)
    : undefined;
  const ward = (byPin ?? byName)?.ward ?? null;

  const parts = [locality, city].filter(Boolean) as string[];
  const label = parts.length ? parts.join(", ") : "your area";

  return {
    label,
    ward,
    raw: {
      suburb: a.suburb,
      neighbourhood: a.neighbourhood,
      city_district: a.city_district,
      city: a.city,
      town: a.town,
      state_district: a.state_district,
      state: a.state,
      postcode: a.postcode,
    },
  };
}
