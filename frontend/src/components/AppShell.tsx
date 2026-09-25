"use client";

/**
 * App Shell — persistent top bar + left sidebar (India redesign).
 * Wraps every page: logo, centered search ("/" shortcut), Explore link,
 * notification bell, + New Commitment, user chip; sidebar with
 * Home/Civic/Vendors/Nearby + My Commitments/My Activity/Saved + promo card.
 * Uses existing color tokens only.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Search,
  Home,
  Landmark,
  Briefcase,
  MapPin,
  CheckCircle,
  BarChart3,
  Bookmark,
  ChevronDown,
  ChevronRight,
  Star,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { NotificationBell } from "./NotificationBell";

const NAV_MAIN = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/civic", label: "Civic", icon: Landmark, chevron: true },
  { href: "/vendors", label: "Vendors", icon: Briefcase, chevron: true },
  { href: "/nearby", label: "Nearby", icon: MapPin },
];

const NAV_SECONDARY = [
  { href: "/my-commitments", label: "My Commitments", icon: CheckCircle },
  { href: "/my-activity", label: "My Activity", icon: BarChart3 },
  { href: "/saved", label: "Saved", icon: Bookmark },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, login, logout, isAuthenticated } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // "/" focuses search
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const typing =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;
      if (e.key === "/" && !typing) {
        e.preventDefault();
        document.getElementById("topbar-search-input")?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link href="/" className="sidebar-brand">
          Vouch
        </Link>

        {NAV_MAIN.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-item ${isActive(item.href, item.exact) ? "active" : ""}`}
          >
            <span className="sidebar-item-icon">
              <item.icon size={18} />
            </span>
            {item.label}
            {item.chevron && (
              <span className="sidebar-item-chevron">
                <ChevronRight size={15} />
              </span>
            )}
          </Link>
        ))}

        <div className="sidebar-divider" />

        {NAV_SECONDARY.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-item ${isActive(item.href) ? "active" : ""}`}
          >
            <span className="sidebar-item-icon">
              <item.icon size={18} />
            </span>
            {item.label}
          </Link>
        ))}

        {/* Promo card — static, not a link */}
        <div className="sidebar-promo">
          <div className="sidebar-promo-icon">
            <Star size={16} />
          </div>
          <div className="sidebar-promo-title">
            Build a more accountable India
          </div>
          <div className="sidebar-promo-sub">
            Track. Verify. Make promises count.
          </div>
          <svg
            className="sidebar-promo-wave"
            viewBox="0 0 232 46"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden
          >
            <path
              d="M0 46 C 40 20, 70 40, 110 26 S 190 8, 232 22 L 232 46 Z"
              fill="rgba(255, 107, 53, 0.16)"
            />
            <path
              d="M0 46 C 50 32, 90 44, 130 34 S 200 22, 232 30 L 232 46 Z"
              fill="rgba(255, 107, 53, 0.22)"
            />
          </svg>
        </div>
      </aside>

      <div className="shell-main">
        <header className="topbar">
          {/* Mobile-only brand (sidebar is hidden under 960px) */}
          <Link
            href="/"
            className="sidebar-brand"
            style={{ display: "none" }}
            data-mobile-brand
          >
            Vouch
          </Link>

          <div className="topbar-search">
            <span className="topbar-search-icon">
              <Search size={15} />
            </span>
            <input
              id="topbar-search-input"
              type="text"
              placeholder="Search promises, people, or services..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.currentTarget.value.trim()) {
                  router.push(`/explore?q=${encodeURIComponent(e.currentTarget.value.trim())}`);
                }
              }}
            />
            <span className="topbar-search-kbd">/</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <Link
              href="/explore"
              style={{
                color: "var(--text-secondary)",
                textDecoration: "none",
                fontSize: "var(--font-body)",
              }}
            >
              Explore
            </Link>
            <NotificationBell />
            <Link
              href="/create"
              className="btn btn-primary"
              style={{ padding: "8px 18px", fontSize: "var(--font-caption)" }}
            >
              + New Commitment
            </Link>

            {isAuthenticated ? (
              <div style={{ position: "relative" }}>
                <button
                  className="user-chip"
                  onClick={() => setUserMenuOpen((v) => !v)}
                >
                  <span className="user-chip-avatar">
                    {(user?.handle ?? "U").slice(0, 2).toUpperCase()}
                  </span>
                  @{user?.handle ?? "you"}
                  <ChevronDown size={14} />
                </button>
                {userMenuOpen && (
                  <div
                    style={{
                      position: "absolute",
                      top: "calc(100% + 6px)",
                      right: 0,
                      minWidth: "160px",
                      background: "var(--bg-surface-raised)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "10px",
                      padding: "6px",
                      zIndex: 100,
                      boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
                    }}
                  >
                    <Link
                      href={`/profile/${user?.handle}`}
                      onClick={() => setUserMenuOpen(false)}
                      className="sidebar-item"
                      style={{ fontSize: "var(--font-caption)" }}
                    >
                      Profile
                    </Link>
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        logout();
                      }}
                      className="sidebar-item"
                      style={{ fontSize: "var(--font-caption)", color: "var(--accent-broken)" }}
                    >
                      Log out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={login}
                className="btn btn-primary"
                style={{ padding: "8px 18px", fontSize: "var(--font-caption)" }}
              >
                Sign In
              </button>
            )}
          </div>
        </header>

        {children}
      </div>
    </div>
  );
}
