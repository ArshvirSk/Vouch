"use client";

/**
 * Hero banner — home redesign stage 2.
 * Mumbai dusk photo + dark gradient overlay, eyebrow label, headline with
 * orange-accented "word.", subtext, and three feed-filter pills
 * (Civic active by default). Uses existing tokens only.
 */

import { useRouter } from "next/navigation";
import { Landmark, Briefcase, MapPin } from "lucide-react";

const FILTERS = [
  { key: "civic", label: "Civic", icon: Landmark, style: "filled" as const },
  { key: "vendor", label: "Vendors", icon: Briefcase, style: "outline" as const },
  { key: "nearby", label: "Nearby", icon: MapPin, style: "outline" as const },
];

export function HeroBanner() {
  const router = useRouter();

  return (
    <div style={{ position: "relative", marginBottom: "28px" }}>
      <div
        style={{
          position: "relative",
          borderRadius: "20px",
          overflow: "hidden",
          minHeight: "224px",
          display: "flex",
          alignItems: "center",
          border: "1px solid var(--border-subtle)",
        }}
      >
      {/* Banner image with the glow radiating from behind it (right side,
          matching the reference's halo around the Gateway of India) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
        }}
      >
        <div
          aria-hidden
          style={{
            position: "absolute",
            inset: "-40px -60px -40px 30%",
            background:
              "radial-gradient(55% 120% at 70% 40%, rgba(255,107,53,0.35) 0%, rgba(255,107,53,0.14) 45%, rgba(255,107,53,0) 75%)",
            filter: "blur(26px)",
          }}
        />
        <img
          src="/assets/mumbai-hero-banner.png"
          alt="Mumbai skyline at dusk"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>

      {/* Dark-to-transparent gradient overlay (left dark for legibility) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(90deg, rgba(14,15,20,0.92) 0%, rgba(14,15,20,0.72) 38%, rgba(14,15,20,0.25) 70%, rgba(14,15,20,0.15) 100%)",
        }}
      />

      {/* Content */}
      <div
        style={{
          position: "relative",
          padding: "24px 32px",
          maxWidth: "500px",
          display: "flex",
          flexDirection: "column",
          gap: "9px",
        }}
      >
        <span
          style={{
            fontSize: "11px",
            fontWeight: 700,
            letterSpacing: "1.2px",
            color: "var(--accent-primary)",
            textTransform: "uppercase",
          }}
        >
          Local promises. Real impact.
        </span>

        <h1
          style={{
            fontSize: "30px",
            lineHeight: 1.15,
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "-0.5px",
          }}
        >
          Hold people to their{" "}
          <span style={{ color: "var(--accent-primary)" }}>word.</span>
        </h1>

        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "var(--font-body)",
            lineHeight: 1.5,
            margin: 0,
            maxWidth: "400px",
          }}
        >
          Track civic commitments, verify vendor work, and build a more
          accountable India.
        </p>

        {/* Feed filter pills */}
        <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
          {FILTERS.map(({ key, label, icon: Icon, style }) => (
            <button
              key={key}
              onClick={() =>
                router.push(key === "nearby" ? "/nearby" : `/${key === "vendor" ? "vendors" : key}`)
              }
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "7px",
                padding: "9px 18px",
                borderRadius: "100px",
                fontSize: "var(--font-caption)",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s ease",
                ...(style === "filled"
                  ? {
                      background: "var(--accent-primary)",
                      color: "white",
                      border: "1px solid var(--accent-primary)",
                    }
                  : {
                      background: "rgba(14, 15, 20, 0.55)",
                      color: "var(--text-primary)",
                      border: "1px solid var(--border-subtle)",
                      backdropFilter: "blur(6px)",
                    }),
              }}
              onMouseEnter={(e) => {
                if (style === "outline") {
                  e.currentTarget.style.borderColor = "var(--accent-primary)";
                  e.currentTarget.style.color = "var(--accent-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (style === "outline") {
                  e.currentTarget.style.borderColor = "var(--border-subtle)";
                  e.currentTarget.style.color = "var(--text-primary)";
                }
              }}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>
      </div>
      </div>
    </div>
  );
}
