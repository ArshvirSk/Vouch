"use client";

/**
 * DEV-ONLY geolocation stub.
 *
 * The preview/embedded browser hard-blocks the Geolocation API for this
 * origin, which makes the location-consent flow impossible to exercise.
 * Append ?geo=lat,lng (or ?geo=deny) to the URL in development to stub the
 * browser dialog: the module replaces navigator.geolocation and reports
 * "prompt" for the permissions query before the app mounts.
 *
 * Rendered as a client component from the root layout (it must run in the
 * browser before AreaProvider's mount effect).
 * No-op in production builds and without the ?geo= param.
 */

import { useEffect } from "react";

export function GeoDevStub() {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") return;

    const params = new URLSearchParams(window.location.search);
    const raw = params.get("geo");
    if (!raw) return;

    if (raw === "deny") {
      Object.defineProperty(navigator, "geolocation", {
        value: {
          getCurrentPosition: (_success: PositionCallback, error?: PositionErrorCallback) =>
            setTimeout(
              () =>
                error?.({
                  code: 1,
                  message: "User denied Geolocation (dev stub)",
                  PERMISSION_DENIED: 1,
                  POSITION_UNAVAILABLE: 2,
                  TIMEOUT: 3,
                } as GeolocationPositionError),
              300
            ),
        },
        configurable: true,
      });
      // Permissions stay effectively "denied" for the provider's check.
      Object.defineProperty(navigator, "permissions", {
        value: {
          query: (opts: { name?: string }) =>
            Promise.resolve({
              state: "denied",
              onchange: null,
              addEventListener: () => {},
              removeEventListener: () => {},
            }),
        },
        configurable: true,
      });
      return;
    }

    const [latS, lngS] = raw.split(",");
    const lat = parseFloat(latS);
    const lng = parseFloat(lngS);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;

    Object.defineProperty(navigator, "geolocation", {
      value: {
        getCurrentPosition: (success: PositionCallback) =>
          setTimeout(
            () =>
              success({
                coords: { latitude: lat, longitude: lng, accuracy: 25 },
                timestamp: Date.now(),
              } as GeolocationPosition),
            400
          ),
      },
      configurable: true,
    });
    Object.defineProperty(navigator, "permissions", {
      value: {
        query: (opts: { name?: string }) =>
          Promise.resolve({
            state: "prompt",
            onchange: null,
            addEventListener: () => {},
            removeEventListener: () => {},
          }),
      },
      configurable: true,
    });
  }, []);

  return null;
}
