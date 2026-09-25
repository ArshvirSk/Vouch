"use client";

/**
 * Profile / Reputation — Design Doc §5.5.
 * Stats row, History/As Juror tabs, waveform trend bars, jury accuracy gauge.
 */

import { useState, useEffect, use } from "react";
import { getUserProfile, getReputationHistory, getUserCommitments, type UserProfile, type ReputationEvent, type Commitment } from "@/lib/api";
import { ReputationGauge } from "@/components/ReputationGauge";
import { WaveformBars } from "@/components/WaveformBars";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";
import { Flame, Wallet, Key, Loader2 } from "lucide-react";
import { usePrivy, useWallets } from "@privy-io/react-auth";
import { EAS, SchemaEncoder } from "@ethereum-attestation-service/eas-sdk";
import { BrowserProvider } from "ethers";
import { EAS_CONTRACT_ADDRESS, VOUCH_SCHEMA_UID, isSchemaRegistered } from "@/lib/eas";

export default function ProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = use(params);
  const { user: authUser } = useAuth();
  const { user: privyUser, exportWallet, createWallet, ready } = usePrivy();
  const { wallets } = useWallets();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [events, setEvents] = useState<ReputationEvent[]>([]);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [activeTab, setActiveTab] = useState<"commitments" | "history" | "juror">("commitments");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [profileData, historyData, commitmentsData] = await Promise.all([
          getUserProfile(handle),
          getReputationHistory(handle),
          getUserCommitments(handle),
        ]);
        setProfile(profileData);
        setEvents(historyData.events);
        setCommitments(commitmentsData);
      } catch {
        // Demo data
        setProfile(getDemoProfile(handle));
        setEvents(getDemoEvents());
        setCommitments([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [handle]);

  const [isMinting, setIsMinting] = useState(false);
  const [mintTxUid, setMintTxUid] = useState<string | null>(null);

  const handleMintReputation = async () => {
    try {
      setIsMinting(true);
      setMintTxUid(null);

      // Find the embedded wallet
      const embeddedWallet = wallets.find((w) => w.walletClientType === "privy");
      if (!embeddedWallet) {
        throw new Error("No embedded wallet found. Please create one first.");
      }

      // Ensure we are on Base Sepolia
      if (embeddedWallet.chainId !== "eip155:84532") {
        await embeddedWallet.switchChain(84532);
      }

      // Guard against the unregistered dev placeholder UID
      if (!isSchemaRegistered) {
        throw new Error(
          "Reputation schema is not registered yet. Set NEXT_PUBLIC_VOUCH_SCHEMA_UID in .env.local (see frontend/scripts/registerSchema.js)."
        );
      }

      // Get an ethers signer from the embedded wallet's EIP-1193 provider
      const ethereumProvider = await embeddedWallet.getEthereumProvider();
      const ethersProvider = new BrowserProvider(ethereumProvider);
      const signer = await ethersProvider.getSigner();

      // Initialize EAS
      const eas = new EAS(EAS_CONTRACT_ADDRESS);
      eas.connect(signer as any);

      // Initialize SchemaEncoder
      const schemaEncoder = new SchemaEncoder("uint256 reputationScore, string handle");
      const encodedData = schemaEncoder.encodeData([
        { name: "reputationScore", value: Math.floor(profile?.user.reputation_score || 0), type: "uint256" },
        { name: "handle", value: profile?.user.handle || "", type: "string" },
      ]);

      // Mint Attestation
      const transaction = await eas.attest({
        schema: VOUCH_SCHEMA_UID,
        data: {
          recipient: embeddedWallet.address,
          expirationTime: BigInt(0),
          revocable: true,
          data: encodedData,
        },
      });

      const newAttestationUID = await transaction.wait();
      setMintTxUid(newAttestationUID);
    } catch (err: any) {
      console.error(err);
      if (err.message?.includes("insufficient funds") || err.message?.includes("gas")) {
        alert("Transaction failed: Your wallet needs Base Sepolia ETH to pay for gas.");
      } else {
        alert(err.message || "Failed to mint reputation");
      }
    } finally {
      setIsMinting(false);
    }
  };

  if (loading) {
    return (
      <div
        className="container"
        style={{ paddingTop: "60px", textAlign: "center", color: "var(--text-secondary)" }}
      >
        Loading profile...
      </div>
    );
  }

  if (!profile) return null;

  const commitmentEvents = events.filter(
    (e) => e.reason === "commitment_kept" || e.reason === "commitment_broken"
  );
  const jurorEvents = events.filter(
    (e) => e.reason === "jury_accurate" || e.reason === "jury_inaccurate"
  );

  return (
    <div className="container" style={{ paddingTop: "24px", paddingBottom: "40px" }}>
      {/* Profile header */}
      <div style={{ textAlign: "center", marginBottom: "32px" }}>
        <div
          style={{
            width: "72px",
            height: "72px",
            borderRadius: "50%",
            background: "var(--bg-surface-raised)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 12px",
            fontSize: "var(--font-title)",
            fontWeight: 700,
            color: "var(--accent-primary)",
          }}
        >
          {handle.slice(0, 2).toUpperCase()}
        </div>
        <h1 style={{ fontSize: "var(--font-title)", fontWeight: 700 }}>
          @{handle}
        </h1>
        <p
          style={{
            color: "var(--text-secondary)",
            fontSize: "var(--font-caption)",
            marginTop: "4px",
          }}
        >
          Member since {formatDate(profile.user.created_at)}
        </p>
      </div>

      {/* Stats row — Design Doc §5.5 (Ref B pattern) */}
      <div className="stats-row" style={{ marginBottom: "32px" }}>
        <div className="stat-item">
          <div className="stat-value" style={{ color: "var(--accent-primary)" }}>
            {profile.user.reputation_score.toFixed(1)}
          </div>
          <div className="stat-label">Reputation</div>
        </div>
        <div className="stat-item">
          <div className="stat-value" style={{ color: "var(--accent-primary)", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
            <Flame size={28} style={{ marginTop: "-2px" }} /> {profile.user.current_streak}
          </div>
          <div className="stat-label">Streak</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">
            {profile.stats.commitments_met}/{profile.stats.commitments_total}
          </div>
          <div className="stat-label">Kept</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{profile.stats.jury_accuracy.toFixed(0)}%</div>
          <div className="stat-label">Accuracy</div>
        </div>
      </div>

      {/* Jury accuracy gauge + Waveform bars side by side */}
      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "space-around",
          alignItems: "center",
          padding: "24px",
          marginBottom: "24px",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "var(--font-caption)",
              color: "var(--text-secondary)",
              marginBottom: "12px",
              textAlign: "center",
            }}
          >
            Jury Accuracy
          </div>
          <ReputationGauge
            value={profile.stats.jury_accuracy}
            label="Accuracy"
            color="var(--accent-verified)"
          />
        </div>
        <div>
          <div
            style={{
              fontSize: "var(--font-caption)",
              color: "var(--text-secondary)",
              marginBottom: "12px",
              textAlign: "center",
            }}
          >
            Reputation Trend
          </div>
          <WaveformBars events={events} />
        </div>
      </div>

      {/* Tabs: Commitments / History / As Juror */}
      <div className="status-strip" style={{ marginBottom: "20px" }}>
        <button
          className={`status-tab ${activeTab === "commitments" ? "active" : ""}`}
          onClick={() => setActiveTab("commitments")}
        >
          Commitments
        </button>
        <button
          className={`status-tab ${activeTab === "history" ? "active" : ""}`}
          onClick={() => setActiveTab("history")}
        >
          History
        </button>
        <button
          className={`status-tab ${activeTab === "juror" ? "active" : ""}`}
          onClick={() => setActiveTab("juror")}
        >
          As Juror
        </button>
      </div>

      {/* Event list */}
      <div>
        {activeTab === "commitments" ? (
          commitments.length === 0 ? (
            <div style={{ textAlign: "center", padding: "32px", color: "var(--text-secondary)" }}>
              No commitments yet
            </div>
          ) : (
            commitments.map((commitment) => (
              <Link key={commitment.id} href={`/commitment/${commitment.id}`} style={{ textDecoration: "none" }}>
                <div className="card animate-in" style={{ marginBottom: "8px", padding: "14px 16px" }}>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
                    {commitment.title}
                  </div>
                  <div style={{ fontSize: "var(--font-caption)", color: "var(--text-secondary)", display: "flex", justifyContent: "space-between" }}>
                    <span style={{ 
                      color: commitment.status === "met" ? "var(--accent-verified)" : 
                             commitment.status === "broken" ? "var(--accent-broken)" : 
                             "var(--text-secondary)" 
                    }}>
                      {commitment.status.replace(/_/g, " ").toUpperCase()}
                    </span>
                    <span>{formatDate(commitment.created_at)}</span>
                  </div>
                </div>
              </Link>
            ))
          )
        ) : (activeTab === "history" ? commitmentEvents : jurorEvents).length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "32px",
              color: "var(--text-secondary)",
            }}
          >
            No {activeTab === "history" ? "commitment" : "juror"} events yet
          </div>
        ) : (
          (activeTab === "history" ? commitmentEvents : jurorEvents).map((event) => (
            <div
              key={event.id}
              className="card animate-in"
              style={{
                marginBottom: "8px",
                padding: "14px 16px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <span
                  style={{
                    color:
                      event.delta > 0
                        ? "var(--accent-verified)"
                        : "var(--accent-broken)",
                    fontWeight: 600,
                    marginRight: "8px",
                  }}
                >
                  {event.delta > 0 ? "+" : ""}
                  {event.delta}
                </span>
                <span style={{ color: "var(--text-secondary)" }}>
                  {event.reason.replace(/_/g, " ")}
                </span>
              </div>
              <span
                style={{
                  fontSize: "var(--font-caption)",
                  color: "var(--text-secondary)",
                }}
              >
                {formatDate(event.created_at)}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Link to partners */}
      <Link
        href={`/partners/${handle}`}
        className="btn btn-outline"
        style={{
          width: "100%",
          marginTop: "24px",
          textDecoration: "none",
          display: "block",
          textAlign: "center",
        }}
      >
        View Partners & Jurors ({profile.stats.partner_count})
      </Link>

      {/* Web3 Export & Wallet Section */}
      {authUser?.handle === profile.user.handle && (
        <div style={{ marginTop: "32px", padding: "20px", background: "var(--bg-surface)", borderRadius: "12px", border: "1px solid var(--border-color)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
            <Wallet size={20} color="var(--accent-primary)" />
            <h3 style={{ fontSize: "var(--font-body)", fontWeight: 600, margin: 0 }}>Embedded Wallet</h3>
          </div>
          <p style={{ fontSize: "var(--font-caption)", color: "var(--text-secondary)", marginBottom: "16px" }}>
            This wallet was automatically created for you by Privy. You can use it to hold stakes and attest to your reputation.
          </p>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {(() => {
              const embeddedWallet = wallets.find((w) => w.walletClientType === "privy");
              return (
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <span style={{ fontSize: "var(--font-caption)", fontWeight: 600, color: "var(--text-secondary)" }}>
                    Wallet Address
                  </span>
                  <div style={{ 
                    fontFamily: "monospace", 
                    background: "var(--bg-surface-raised)", 
                    padding: "8px 12px", 
                    borderRadius: "6px",
                    wordBreak: "break-all",
                    fontSize: "var(--font-caption)"
                  }}>
                    {embeddedWallet ? (
                      embeddedWallet.address
                    ) : ready ? (
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span>No embedded wallet found.</span>
                        <button 
                          className="btn btn-outline" 
                          style={{ padding: "4px 8px", fontSize: "12px" }}
                          onClick={() => createWallet()}
                        >
                          Create Wallet
                        </button>
                      </div>
                    ) : (
                      "Loading wallet..."
                    )}
                  </div>
                </div>
              );
            })()}

            <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
              {mintTxUid ? (
                <div style={{ flex: 1, padding: "8px", borderRadius: "8px", border: "1px solid var(--accent-verified)", color: "var(--accent-verified)", textAlign: "center", fontSize: "14px" }}>
                  <span style={{ display: "block", marginBottom: "4px" }}>Minted!</span>
                  <a href={`https://sepolia.basescan.org/tx/${mintTxUid}`} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "underline" }}>
                    View on BaseScan
                  </a>
                </div>
              ) : (
                <button 
                  className="btn btn-primary" 
                  onClick={handleMintReputation}
                  disabled={isMinting}
                  style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", opacity: isMinting ? 0.7 : 1 }}
                >
                  {isMinting ? <Loader2 size={16} className="animate-spin" /> : null}
                  {isMinting ? "Minting..." : "Mint Reputation"}
                </button>
              )}
              <button 
                className="btn btn-outline" 
                onClick={() => exportWallet()}
                style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
              >
                <Key size={16} /> Export Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getDemoProfile(handle: string): UserProfile {
  return {
    user: {
      id: "demo",
      handle,
      reputation_score: 72.5,
      current_streak: 2,
      created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
    },
    stats: {
      commitments_total: 8,
      commitments_met: 6,
      completion_rate: 75.0,
      jury_accuracy: 85.7,
      total_votes_cast: 14,
      partner_count: 5,
    },
  };
}

function getDemoEvents(): ReputationEvent[] {
  const now = Date.now();
  return [
    { id: "1", user_id: "demo", delta: 5.0, reason: "commitment_kept", commitment_id: "c1", created_at: new Date(now - 1 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "2", user_id: "demo", delta: 2.0, reason: "jury_accurate", commitment_id: "c2", created_at: new Date(now - 2 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "3", user_id: "demo", delta: -5.0, reason: "commitment_broken", commitment_id: "c3", created_at: new Date(now - 5 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "4", user_id: "demo", delta: 5.0, reason: "commitment_kept", commitment_id: "c4", created_at: new Date(now - 8 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "5", user_id: "demo", delta: -2.0, reason: "jury_inaccurate", commitment_id: "c5", created_at: new Date(now - 10 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "6", user_id: "demo", delta: 5.0, reason: "commitment_kept", commitment_id: "c6", created_at: new Date(now - 12 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "7", user_id: "demo", delta: 2.0, reason: "jury_accurate", commitment_id: "c7", created_at: new Date(now - 15 * 24 * 60 * 60 * 1000).toISOString() },
    { id: "8", user_id: "demo", delta: 5.0, reason: "commitment_kept", commitment_id: "c8", created_at: new Date(now - 20 * 24 * 60 * 60 * 1000).toISOString() },
  ];
}
