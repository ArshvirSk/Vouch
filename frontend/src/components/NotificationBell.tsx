"use client";

import { useState, useEffect } from "react";
import { getUnreadNotifications, markNotificationAsRead, type Notification } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDate } from "@/lib/utils";
import { Bell } from "lucide-react";

export function NotificationBell() {
  const { isAuthenticated } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      setNotifications([]);
      setLoading(false);
      return;
    }

    async function loadNotifications() {
      try {
        const data = await getUnreadNotifications();
        setNotifications(data);
      } catch (err) {
        console.error("Failed to load notifications", err);
      } finally {
        setLoading(false);
      }
    }

    loadNotifications();
    // Poll every 30 seconds
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleMarkAsRead = async (id: string) => {
    try {
      await markNotificationAsRead(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch (err) {
      console.error("Failed to mark as read", err);
    }
  };

  if (loading) return null;

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: "none",
          border: "none",
          color: "var(--text-primary)",
          fontSize: "1.2rem",
          cursor: "pointer",
          position: "relative",
          padding: "8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Bell size={20} />
        {notifications.length > 0 && (
          <span
            style={{
              position: "absolute",
              top: "0px",
              right: "0px",
              background: "var(--accent-primary)",
              color: "#fff",
              borderRadius: "50%",
              width: "18px",
              height: "18px",
              fontSize: "0.7rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
            }}
          >
            {notifications.length}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            right: 0,
            width: "300px",
            background: "var(--bg-surface-raised)",
            border: "1px solid var(--bg-surface-border)",
            borderRadius: "8px",
            marginTop: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
            zIndex: 100,
            maxHeight: "400px",
            overflowY: "auto",
          }}
        >
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--bg-surface-border)", fontWeight: 600 }}>
            Notifications
          </div>
          {notifications.length === 0 ? (
            <div style={{ padding: "24px", textAlign: "center", color: "var(--text-secondary)", fontSize: "var(--font-caption)" }}>
              No new notifications
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid var(--bg-surface-border)",
                  fontSize: "var(--font-caption)",
                }}
              >
                <div style={{ marginBottom: "8px" }}>{n.message}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "var(--text-secondary)" }}>{formatDate(n.created_at)}</span>
                  <button
                    onClick={() => handleMarkAsRead(n.id)}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--accent-primary)",
                      cursor: "pointer",
                      fontSize: "0.7rem",
                    }}
                  >
                    Mark read
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
