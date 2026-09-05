/**
 * Utility functions for Vouch frontend.
 */

/** Format a date as relative time (e.g., "in 3 days", "2 hours ago") */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const absDiffMs = Math.abs(diffMs);
  const isFuture = diffMs > 0;

  const minutes = Math.floor(absDiffMs / (1000 * 60));
  const hours = Math.floor(absDiffMs / (1000 * 60 * 60));
  const days = Math.floor(absDiffMs / (1000 * 60 * 60 * 24));

  let timeStr: string;
  if (days > 0) timeStr = `${days}d ${hours % 24}h`;
  else if (hours > 0) timeStr = `${hours}h ${minutes % 60}m`;
  else timeStr = `${minutes}m`;

  return isFuture ? `in ${timeStr}` : `${timeStr} ago`;
}

/** Calculate time-based progress (0-100) */
export function calcTimeProgress(createdAt: string, deadline: string): number {
  const start = new Date(createdAt).getTime();
  const end = new Date(deadline).getTime();
  const now = Date.now();
  const total = end - start;
  const elapsed = now - start;
  return Math.min(100, Math.max(0, (elapsed / total) * 100));
}

/** Get status display label */
export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    open: "Open",
    evidence_submitted: "Evidence Submitted",
    in_verification: "In Verification",
    met: "Met",
    broken: "Broken",
    disputed: "Disputed",
    expired: "Expired",
  };
  return labels[status] || status;
}

/** Get initials from a handle */
export function getInitials(handle: string): string {
  return handle.slice(0, 2).toUpperCase();
}

/** Format a date nicely */
export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
