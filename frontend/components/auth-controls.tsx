"use client";

import { useState } from "react";
import { getAuthStartUrl } from "../lib/api";
import { useAuth } from "./auth-provider";
import { UserMenu } from "./user-menu";

const controlClassName = "min-h-11 rounded-lg px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2";

export function AuthControls() {
  const { status, user, errorMessage, refresh, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  if (status === "loading") {
    return <span aria-label="Oturum durumu yükleniyor" className="h-11 w-28 animate-pulse rounded-lg bg-slate-200" />;
  }

  if (status === "authenticated" && user) {
    async function handleLogout() {
      setIsLoggingOut(true);
      await logout();
      setIsLoggingOut(false);
    }

    return (
      <div className="flex flex-col items-end gap-1">
        <UserMenu user={user} onLogout={() => void handleLogout()} busy={isLoggingOut} />
        {errorMessage && (
          <p role="alert" className="max-w-56 text-right text-xs text-amber-800">{errorMessage}</p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <a
        href={getAuthStartUrl()}
        aria-label="GitHub ile giriş yap"
        className={`${controlClassName} whitespace-nowrap bg-indigo-600 text-white hover:bg-primary-hover`}
      >
        <span className="sm:hidden" aria-hidden="true">Giriş yap</span>
        <span className="hidden sm:inline" aria-hidden="true">GitHub ile giriş yap</span>
      </a>
      {status === "error" && (
        <button
          type="button"
          onClick={() => void refresh()}
          className={`${controlClassName} border border-slate-300 bg-card text-slate-700 hover:bg-slate-100`}
        >
          Durumu yenile
        </button>
      )}
      {status === "error" && errorMessage && (
        <p role="status" className="w-full text-right text-xs text-slate-500">Oturum durumu şu anda doğrulanamadı.</p>
      )}
    </div>
  );
}
