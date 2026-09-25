"use client";

/**
 * Create Commitment — Design Doc §5.2.
 * Conversational, step-by-step form with falsifiability check inline warning.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { createCommitment, searchUsers } from "@/lib/api";
import { AlertTriangle, X, ArrowLeft, ArrowRight } from "lucide-react";

type Step = "title" | "condition" | "deadline" | "jurors" | "review";

export default function CreateCommitmentPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [step, setStep] = useState<Step>("title");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [condition, setCondition] = useState("");
  const [deadline, setDeadline] = useState("");
  const [jurorHandles, setJurorHandles] = useState<string[]>([""]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [activeJurorIndex, setActiveJurorIndex] = useState<number | null>(null);
  const [searchResults, setSearchResults] = useState<{handle: string, id: string}[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Debounced search for jurors
  useEffect(() => {
    if (activeJurorIndex === null) {
      setSearchResults([]);
      return;
    }
    const query = jurorHandles[activeJurorIndex];
    if (!query || query.length < 2) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchUsers(query);
        // Filter out handles that are already selected, and the current user's handle
        const filtered = results.filter(
          (u) => u.handle !== user?.handle && !jurorHandles.includes(u.handle)
        );
        setSearchResults(filtered);
      } catch (err) {
        console.error("Search failed", err);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [activeJurorIndex, jurorHandles, user?.handle]);

  // Falsifiability warning — inline nudge (Design Doc §5.2)
  const showFalsifiabilityWarning =
    condition.length > 0 &&
    condition.length < 30 &&
    !/\d/.test(condition);

  const steps: { key: Step; label: string }[] = [
    { key: "title", label: "What" },
    { key: "condition", label: "How to verify" },
    { key: "deadline", label: "When" },
    { key: "jurors", label: "Who judges" },
    { key: "review", label: "Review" },
  ];

  const currentIdx = steps.findIndex((s) => s.key === step);

  const canNext = () => {
    switch (step) {
      case "title": return title.trim().length > 0;
      case "condition": return condition.trim().length >= 10;
      case "deadline": return deadline.length > 0;
      case "jurors": return jurorHandles.filter((h) => h.trim()).length >= 2;
      default: return true;
    }
  };

  const handleSubmit = async () => {
    if (!user) {
      setError("Please sign in to create a commitment");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await createCommitment(
        {
          title,
          description: description || undefined,
          measurable_condition: condition,
          deadline: new Date(deadline).toISOString(),
          juror_handles: jurorHandles.filter((h) => h.trim()),
        },
        user.token
      );
      router.push(`/commitment/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create commitment");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ paddingTop: "40px", paddingBottom: "40px", maxWidth: "540px" }}>
      {/* Step indicator */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "32px" }}>
        {steps.map((s, i) => (
          <div
            key={s.key}
            style={{
              flex: 1,
              height: "3px",
              borderRadius: "2px",
              background:
                i <= currentIdx
                  ? "var(--accent-primary)"
                  : "var(--border-subtle)",
              transition: "background 0.3s ease",
            }}
          />
        ))}
      </div>

      {/* Step: Title */}
      {step === "title" && (
        <div className="animate-in">
          <h2
            style={{
              fontSize: "var(--font-title)",
              fontWeight: 600,
              marginBottom: "8px",
            }}
          >
            What are you committing to?
          </h2>
          <p
            style={{
              color: "var(--text-secondary)",
              marginBottom: "24px",
            }}
          >
            Give your commitment a clear, specific title.
          </p>
          <input
            className="input"
            placeholder='e.g., "Complete 90 LeetCode problems"'
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
          <textarea
            className="input"
            placeholder="Add more context (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={{ marginTop: "12px", minHeight: "80px" }}
          />
        </div>
      )}

      {/* Step: Measurable Condition */}
      {step === "condition" && (
        <div className="animate-in">
          <h2
            style={{
              fontSize: "var(--font-title)",
              fontWeight: 600,
              marginBottom: "8px",
            }}
          >
            How will this be verified?
          </h2>
          <p
            style={{
              color: "var(--text-secondary)",
              marginBottom: "24px",
            }}
          >
            State a specific, measurable condition your jury can check.
          </p>
          <textarea
            className="input"
            placeholder='e.g., "Solve 90 LeetCode problems (verified via profile screenshot) by Oct 1st"'
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            autoFocus
          />
          {/* Falsifiability warning chip — Design Doc §5.2 */}
          {showFalsifiabilityWarning && (
            <div className="warning-chip" style={{ marginTop: "12px", display: "flex", gap: "8px", alignItems: "flex-start" }}>
              <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
              <span>
                This might be hard to verify — try adding a number, deadline, or
                measurable outcome.
              </span>
            </div>
          )}
        </div>
      )}

      {/* Step: Deadline */}
      {step === "deadline" && (
        <div className="animate-in">
          <h2
            style={{
              fontSize: "var(--font-title)",
              fontWeight: 600,
              marginBottom: "8px",
            }}
          >
            When's the deadline?
          </h2>
          <p
            style={{
              color: "var(--text-secondary)",
              marginBottom: "24px",
            }}
          >
            Your jury will vote after this date.
          </p>
          <input
            className="input"
            type="datetime-local"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            min={new Date().toISOString().slice(0, 16)}
            autoFocus
          />
        </div>
      )}

      {/* Step: Jurors */}
      {step === "jurors" && (
        <div className="animate-in">
          <h2
            style={{
              fontSize: "var(--font-title)",
              fontWeight: 600,
              marginBottom: "8px",
            }}
          >
            Who will be your jury?
          </h2>
          <p
            style={{
              color: "var(--text-secondary)",
              marginBottom: "24px",
            }}
          >
            Pick 2–5 people to verify your commitment.
          </p>
          {jurorHandles.map((handle, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                gap: "8px",
                marginBottom: "8px",
                alignItems: "center",
              }}
            >
              <div
                className="avatar"
                style={{
                  width: "36px",
                  height: "36px",
                  background: "var(--bg-surface-raised)",
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "14px",
                  color: "var(--text-secondary)",
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </div>
              <div style={{ flex: 1, position: "relative" }}>
                <input
                  className="input"
                  placeholder={`Juror ${i + 1} handle`}
                  value={handle}
                  onFocus={() => setActiveJurorIndex(i)}
                  onBlur={() => {
                    // Delay hiding so clicks on dropdown can register
                    setTimeout(() => {
                      if (activeJurorIndex === i) setActiveJurorIndex(null);
                    }, 200);
                  }}
                  onChange={(e) => {
                    const updated = [...jurorHandles];
                    updated[i] = e.target.value.replace('@', ''); // prevent them from typing @ prefix accidentally
                    setJurorHandles(updated);
                    setActiveJurorIndex(i);
                  }}
                  style={{ width: "100%" }}
                />
                
                {/* Autocomplete Dropdown */}
                {activeJurorIndex === i && searchResults.length > 0 && (
                  <div style={{
                    position: "absolute",
                    top: "100%",
                    left: 0,
                    right: 0,
                    marginTop: "4px",
                    background: "var(--bg-surface-raised)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "8px",
                    zIndex: 10,
                    overflow: "hidden",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.5)"
                  }}>
                    {searchResults.map((userRes) => (
                      <div
                        key={userRes.id}
                        onMouseDown={() => {
                          const updated = [...jurorHandles];
                          updated[i] = userRes.handle;
                          setJurorHandles(updated);
                          setSearchResults([]);
                          setActiveJurorIndex(null);
                        }}
                        style={{
                          padding: "12px 16px",
                          cursor: "pointer",
                          borderBottom: "1px solid var(--border-subtle)",
                          display: "flex",
                          alignItems: "center",
                          gap: "8px"
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = "var(--bg-primary)"}
                        onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                      >
                        <span style={{ fontWeight: 600 }}>@{userRes.handle}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {jurorHandles.length > 2 && (
                <button
                  onClick={() =>
                    setJurorHandles(jurorHandles.filter((_, idx) => idx !== i))
                  }
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--accent-broken)",
                    cursor: "pointer",
                    fontSize: "18px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <X size={18} />
                </button>
              )}
            </div>
          ))}
          {jurorHandles.length < 5 && (
            <button
              className="btn btn-outline"
              onClick={() => setJurorHandles([...jurorHandles, ""])}
              style={{
                width: "100%",
                marginTop: "8px",
                fontSize: "var(--font-caption)",
              }}
            >
              + Add Juror
            </button>
          )}
        </div>
      )}

      {/* Step: Review */}
      {step === "review" && (
        <div className="animate-in">
          <h2
            style={{
              fontSize: "var(--font-title)",
              fontWeight: 600,
              marginBottom: "24px",
            }}
          >
            Review your commitment
          </h2>
          <div className="card-raised" style={{ marginBottom: "16px" }}>
            <div
              style={{
                fontSize: "var(--font-caption)",
                color: "var(--text-secondary)",
                marginBottom: "4px",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              Title
            </div>
            <div style={{ fontWeight: 600, marginBottom: "16px" }}>{title}</div>

            {description && (
              <>
                <div
                  style={{
                    fontSize: "var(--font-caption)",
                    color: "var(--text-secondary)",
                    marginBottom: "4px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  Description
                </div>
                <div style={{ marginBottom: "16px" }}>{description}</div>
              </>
            )}

            <div
              style={{
                fontSize: "var(--font-caption)",
                color: "var(--text-secondary)",
                marginBottom: "4px",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              Verifiable Condition
            </div>
            <div style={{ marginBottom: "16px", color: "var(--accent-primary)" }}>
              {condition}
            </div>

            <div
              style={{
                fontSize: "var(--font-caption)",
                color: "var(--text-secondary)",
                marginBottom: "4px",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              Deadline
            </div>
            <div style={{ marginBottom: "16px" }}>
              {new Date(deadline).toLocaleString()}
            </div>

            <div
              style={{
                fontSize: "var(--font-caption)",
                color: "var(--text-secondary)",
                marginBottom: "4px",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              Jury
            </div>
            <div className="avatar-stack">
              {jurorHandles
                .filter((h) => h.trim())
                .map((h, i) => (
                  <div
                    key={i}
                    className="avatar"
                    title={h}
                    style={{ width: "32px", height: "32px" }}
                  >
                    {h.slice(0, 2).toUpperCase()}
                  </div>
                ))}
            </div>
          </div>

          {error && (
            <div
              style={{
                color: "var(--accent-broken)",
                marginBottom: "12px",
                fontSize: "var(--font-caption)",
              }}
            >
              {error}
            </div>
          )}
        </div>
      )}

      {/* Navigation buttons */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: "32px",
          gap: "12px",
        }}
      >
        {currentIdx > 0 ? (
          <button
            className="btn btn-outline"
            onClick={() => setStep(steps[currentIdx - 1].key)}
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <ArrowLeft size={16} /> Back
          </button>
        ) : (
          <div />
        )}

        {step === "review" ? (
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading}
            style={{ flex: 1, maxWidth: "200px" }}
          >
            {loading ? "Creating..." : "Create Commitment"}
          </button>
        ) : (
          <button
            className="btn btn-primary"
            onClick={() => setStep(steps[currentIdx + 1].key)}
            disabled={!canNext()}
            style={{ opacity: canNext() ? 1 : 0.5, display: "flex", alignItems: "center", gap: "6px" }}
          >
            Continue <ArrowRight size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
