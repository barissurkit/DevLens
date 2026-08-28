"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, getAuthMe, logout as logoutSession } from "../lib/api";
import type { AuthenticatedUser } from "../lib/types";

type AuthStatus = "loading" | "anonymous" | "authenticated" | "error";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthenticatedUser | null;
  errorMessage: string | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const applyAuthResponse = useCallback((response: Awaited<ReturnType<typeof getAuthMe>>) => {
    setUser(response.authenticated ? response.user : null);
    setStatus(response.authenticated ? "authenticated" : "anonymous");
  }, []);

  const applyAuthError = useCallback((error: unknown) => {
    setUser(null);
    setStatus("error");
    setErrorMessage(error instanceof ApiError ? error.message : "Oturum durumu doğrulanamadı.");
  }, []);

  const refresh = useCallback(async () => {
    setErrorMessage(null);
    await getAuthMe().then(applyAuthResponse).catch(applyAuthError);
  }, [applyAuthError, applyAuthResponse]);

  useEffect(() => {
    void getAuthMe().then(applyAuthResponse).catch(applyAuthError);
  }, [applyAuthError, applyAuthResponse]);

  const logout = useCallback(async () => {
    setErrorMessage(null);
    try {
      await logoutSession();
      setUser(null);
      setStatus("anonymous");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Oturum kapatılamadı.");
    }
  }, []);

  const value = useMemo(
    () => ({ status, user, errorMessage, refresh, logout }),
    [status, user, errorMessage, refresh, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
