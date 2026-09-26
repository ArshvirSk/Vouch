"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { usePrivy } from "@privy-io/react-auth";
import { syncPrivyUser, setApiTokenProvider } from "./api";

interface AuthUser {
  id: string; // The database UUID
  handle: string; // The user's handle
  token: string; // The Privy JWT
}

interface AuthContextType {
  user: AuthUser | null;
  login: () => void;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: () => {},
  logout: () => {},
  isAuthenticated: false,
  loading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const { ready, authenticated, user: privyUser, getAccessToken, login: privyLogin, logout: privyLogout } = usePrivy();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Resolve the JWT at request time via Privy (which refreshes expired tokens
  // on demand) instead of caching one in localStorage. Also clears any legacy
  // cached token from before this change.
  useEffect(() => {
    setApiTokenProvider(async () => {
      try {
        return await getAccessToken();
      } catch {
        return null;
      }
    });
    localStorage.removeItem("vouch_token");
  }, [getAccessToken]);

  useEffect(() => {
    async function sync() {
      if (!ready) return;

      if (authenticated && privyUser && !syncing) {
        setSyncing(true);
        try {
          const token = await getAccessToken();
          if (!token) throw new Error("No token");

          // Check if we already synced this session
          const cachedHandle = localStorage.getItem("vouch_handle");
          const cachedUserId = localStorage.getItem("vouch_user_id");

          if (cachedHandle && cachedUserId) {
            setUser({ id: cachedUserId, handle: cachedHandle, token });
          } else {
            // Need to sync with backend to get the UUID and handle
            // If the user doesn't exist yet, we can't create them without a handle.
            // But we will try to sync first (the backend might have a default handle or fail).
            // Actually, we should redirect to an onboarding flow if it fails.
            // For now, let's just attempt a sync with a fallback handle based on ID.
            const fallbackHandle = privyUser.id.replace("did:privy:", "").substring(0, 10);
            const email = privyUser.email?.address || null;
            const wallet = privyUser.wallet?.address || null;
            
            const response = await syncPrivyUser(fallbackHandle, email, wallet, token);
            
            setUser({ id: response.user_id, handle: response.handle, token });
            localStorage.setItem("vouch_handle", response.handle);
            localStorage.setItem("vouch_user_id", response.user_id);
          }
        } catch (error) {
          console.error("Auth sync error", error);
          setUser(null);
        } finally {
          setLoading(false);
          setSyncing(false);
        }
      } else if (!authenticated) {
        setUser(null);
        localStorage.removeItem("vouch_handle");
        localStorage.removeItem("vouch_user_id");
        setLoading(false);
      }
    }

    sync();
  }, [ready, authenticated, privyUser]);

  const logout = async () => {
    await privyLogout();
  };

  return (
    <AuthContext.Provider
      value={{ user, login: privyLogin, logout, isAuthenticated: !!user, loading: loading || (!ready) }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
