"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <nav className="nav">
      <Link
        href="/"
        style={{
          fontSize: "var(--font-title)",
          fontWeight: 700,
          color: "var(--accent-primary)",
          textDecoration: "none",
          letterSpacing: "-0.5px",
        }}
      >
        Vouch
      </Link>

      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {isAuthenticated ? (
          <>
            <Link
              href="/create"
              className="btn btn-primary"
              style={{ padding: "8px 18px", fontSize: "var(--font-caption)" }}
            >
              + New Commitment
            </Link>
            <Link
              href={`/profile/${user?.handle}`}
              style={{
                color: "var(--text-secondary)",
                textDecoration: "none",
                fontSize: "var(--font-body)",
              }}
            >
              @{user?.handle}
            </Link>
            <button
              onClick={logout}
              className="btn btn-outline"
              style={{ padding: "6px 14px", fontSize: "var(--font-caption)" }}
            >
              Logout
            </button>
          </>
        ) : (
          <Link
            href="/login"
            className="btn btn-primary"
            style={{ padding: "8px 18px", fontSize: "var(--font-caption)" }}
          >
            Sign In
          </Link>
        )}
      </div>
    </nav>
  );
}
