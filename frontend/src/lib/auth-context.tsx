"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface AuthUser {
  handle: string;
  token: string;
}

interface AuthContextType {
  user: AuthUser | null;
  setAuth: (handle: string, token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  setAuth: () => {},
  logout: () => {},
  isAuthenticated: false,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    // Restore from localStorage on mount
    const stored = localStorage.getItem("vouch_auth");
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch {
        localStorage.removeItem("vouch_auth");
      }
    }
  }, []);

  const setAuth = (handle: string, token: string) => {
    const authUser = { handle, token };
    setUser(authUser);
    localStorage.setItem("vouch_auth", JSON.stringify(authUser));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("vouch_auth");
  };

  return (
    <AuthContext.Provider
      value={{ user, setAuth, logout, isAuthenticated: !!user }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
