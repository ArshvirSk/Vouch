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

// ─── Auth ─────────────────────────────────────────

export async function signup(handle: string, email: string, password: string) {
  return apiFetch<{ access_token: string }>("/auth/signup", {
    method: "POST",
    body: { handle, email, password },
  });
}

export async function login(email: string, password: string) {
  return apiFetch<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

// ─── Commitments ──────────────────────────────────

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
  juror_count: number;
  evidence_count: number;
}

export async function createCommitment(
  data: {
    title: string;
    description?: string;
    measurable_condition: string;
    deadline: string;
    juror_handles: string[];
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
}) {
  const searchParams = new URLSearchParams();
  if (params?.author) searchParams.set("author", params.author);
  if (params?.status) searchParams.set("status", params.status);
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

export async function getReputationHistory(handle: string) {
  return apiFetch<{ events: ReputationEvent[]; current_score: number }>(
    `/users/${handle}/reputation-history`
  );
}
