/**
 * API client for Vouch FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions {
  method?: string;
  body?: unknown;
  token?: string | null;
}

async function apiFetch<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, token } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// Auth logic is now handled natively via Privy
export async function syncPrivyUser(handle: string, email: string | null, wallet: string | null, token: string) {
  return apiFetch<{ user_id: string; handle: string }>("/auth/sync", {
    method: "POST",
    token,
    body: { handle, email, wallet_address: wallet },
  });
}

export async function searchUsers(query: string) {
  return apiFetch<{ handle: string; id: string }[]>(`/users/search?q=${encodeURIComponent(query)}`);
}
// ─── Commitments ──────────────────────────────────

export interface User {
  id: string;
  handle: string;
  reputation_score: number;
  current_streak: number;
  created_at: string;
}

export interface Commitment {
  id: string;
  author_id: string;
  title: string;
  description: string | null;
  measurable_condition: string;
  deadline: string;
  status: string;
  content_hash: string;
  created_at: string;
  resolved_at: string | null;
  onchain_tx_hash: string | null;
  is_public: boolean;
  jury_pool_size: number | null;

  author?: User;
  juror_count: number;
  evidence_count: number;

  // India PRD §3/§4/§5
  category: "personal" | "civic" | "vendor";
  official_name?: string | null;
  official_role?: string | null;
  ward?: string | null;
  source_type?: "crowd" | "sourced" | null;
  source_citation?: string | null;
  vote_count?: number;
}

export async function createCommitment(
  data: {
    title: string;
    description?: string;
    measurable_condition: string;
    deadline: string;
    juror_handles: string[];
    category?: "personal" | "civic" | "vendor";
    official_name?: string;
    official_role?: string;
    ward?: string;
    source_type?: "crowd" | "sourced";
    source_citation?: string;
  },
  token: string
) {
  return apiFetch<Commitment>("/commitments", {
    method: "POST",
    body: data,
    token,
  });
}

export async function getCommitment(id: string) {
  return apiFetch<Commitment>(`/commitments/${id}`);
}

export async function listCommitments(params?: {
  author?: string;
  status?: string;
  category?: string;
  ward?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.author) searchParams.set("author", params.author);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.ward) searchParams.set("ward", params.ward);
  const query = searchParams.toString();
  return apiFetch<{ commitments: Commitment[]; total: number }>(
    `/commitments${query ? `?${query}` : ""}`
  );
}

// ─── Evidence ─────────────────────────────────────

export interface Evidence {
  id: string;
  commitment_id: string;
  submitter_id: string;
  type: string;
  content: string;
  content_hash: string;
  submitted_at: string;
}

export async function submitEvidence(
  commitmentId: string,
  data: { type: string; content: string },
  token: string
) {
  return apiFetch<Evidence>(`/commitments/${commitmentId}/evidence`, {
    method: "POST",
    body: data,
    token,
  });
}

// ─── Votes ────────────────────────────────────────

export interface Vote {
  id: string;
  commitment_id: string;
  juror_id: string;
  vote: string;
  reason: string | null;
  voted_at: string;
}

export async function castVote(
  commitmentId: string,
  data: { vote: string; reason?: string },
  token: string
) {
  return apiFetch<Vote>(`/commitments/${commitmentId}/vote`, {
    method: "POST",
    body: data,
    token,
  });
}

export async function getVotes(commitmentId: string) {
  return apiFetch<Vote[]>(`/commitments/${commitmentId}/votes`);
}

// ─── Users ────────────────────────────────────────

export interface UserProfile {
  user: {
    id: string;
    handle: string;
    reputation_score: number;
    current_streak: number;
    created_at: string;
  };
  stats: {
    commitments_total: number;
    commitments_met: number;
    completion_rate: number;
    jury_accuracy: number;
    total_votes_cast: number;
    partner_count: number;
  };
}

export interface ReputationEvent {
  id: string;
  user_id: string;
  delta: number;
  reason: string;
  commitment_id: string | null;
  created_at: string;
}

export async function getUserProfile(handle: string) {
  return apiFetch<UserProfile>(`/users/${handle}`);
}

export async function getUserCommitments(handle: string) {
  return apiFetch<Commitment[]>(`/users/${handle}/commitments`);
}

export async function getReputationHistory(handle: string) {
  return apiFetch<{ events: ReputationEvent[]; current_score: number }>(
    `/users/${handle}/reputation-history`
  );
}

// ─── Notifications ────────────────────────────────

export interface Notification {
  id: string;
  type: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export async function getUnreadNotifications(token: string) {
  return apiFetch<Notification[]>("/notifications", { token });
}

export async function markNotificationAsRead(id: string, token: string) {
  return apiFetch<{ status: string }>(`/notifications/${id}/read`, {
    method: "POST",
    token,
  });
}

// ─── Evidence (List) ──────────────────────────────

export async function listEvidence(commitmentId: string) {
  return apiFetch<Evidence[]>(`/commitments/${commitmentId}/evidence`);
}

// ─── Jury Pool ────────────────────────────────────

export interface JuryPoolInfo {
  pool_size: number;
  target_size: number | null;
  user_has_joined: boolean;
}

export async function getJuryPool(commitmentId: string) {
  return apiFetch<JuryPoolInfo>(`/commitments/${commitmentId}/jury-pool`);
}

export async function joinJuryPool(commitmentId: string, token: string) {
  return apiFetch<{ status: string; pool_size: number }>(`/commitments/${commitmentId}/jury-pool`, {
    method: "POST",
    token,
  });
}

