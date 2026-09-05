"use client";

/**
 * Login / Signup page for MVP auth.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { login, signup } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuth();
  const [isSignup, setIsSignup] = useState(false);
  const [handle, setHandle] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isSignup) {
        const result = await signup(handle, email, password);
        setAuth(handle, result.access_token);
      } else {
        const result = await login(email, password);
        // Extract handle from JWT payload
        const payload = JSON.parse(atob(result.access_token.split(".")[1]));
        setAuth(payload.handle, result.access_token);
      }
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="container"
      style={{
        paddingTop: "80px",
        maxWidth: "400px",
      }}
    >
      <div style={{ textAlign: "center", marginBottom: "40px" }}>
        <h1
          style={{
            fontSize: "var(--font-display)",
            fontWeight: 700,
            color: "var(--accent-primary)",
            marginBottom: "8px",
          }}
        >
          Vouch
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>
          {isSignup ? "Create your account" : "Welcome back"}
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        {isSignup && (
          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                display: "block",
                fontSize: "var(--font-caption)",
                color: "var(--text-secondary)",
                marginBottom: "6px",
              }}
            >
              Handle
            </label>
            <input
              className="input"
              type="text"
              placeholder="your_handle"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              required
              minLength={3}
            />
          </div>
        )}

        <div style={{ marginBottom: "16px" }}>
          <label
            style={{
              display: "block",
              fontSize: "var(--font-caption)",
              color: "var(--text-secondary)",
              marginBottom: "6px",
            }}
          >
            Email
          </label>
          <input
            className="input"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div style={{ marginBottom: "24px" }}>
          <label
            style={{
              display: "block",
              fontSize: "var(--font-caption)",
              color: "var(--text-secondary)",
              marginBottom: "6px",
            }}
          >
            Password
          </label>
          <input
            className="input"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </div>

        {error && (
          <div
            style={{
              color: "var(--accent-broken)",
              fontSize: "var(--font-caption)",
              marginBottom: "16px",
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading}
          style={{ width: "100%", marginBottom: "16px" }}
        >
          {loading
            ? "Loading..."
            : isSignup
              ? "Create Account"
              : "Sign In"}
        </button>

        <p
          style={{
            textAlign: "center",
            fontSize: "var(--font-caption)",
            color: "var(--text-secondary)",
          }}
        >
          {isSignup ? "Already have an account? " : "Don't have an account? "}
          <button
            type="button"
            onClick={() => {
              setIsSignup(!isSignup);
              setError(null);
            }}
            style={{
              background: "none",
              border: "none",
              color: "var(--accent-primary)",
              cursor: "pointer",
              fontSize: "inherit",
            }}
          >
            {isSignup ? "Sign in" : "Sign up"}
          </button>
        </p>
      </form>
    </div>
  );
}
