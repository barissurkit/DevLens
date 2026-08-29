"use client";

import { useState } from "react";
import { getAuthStartUrl } from "../lib/api";
import { useAuth } from "./auth-provider";

const controlClassName = "min-h-11 rounded-lg px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2";

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
      <div className="flex flex-wrap items-center justify-end gap-2">
        <a
          href={`/?workspace=1&username=${encodeURIComponent(user.github_login)}`}
          className={`${controlClassName} border border-slate-300 bg-white text-slate-700 hover:bg-slate-100`}
        >
          My Workspace
        </a>
        <span className="max-w-36 truncate text-sm font-medium text-slate-700" title={user.display_name ?? user.github_login}>
          {user.display_name ?? `@${user.github_login}`}
        </span>
        <button
          type="button"
          onClick={() => void handleLogout()}
          disabled={isLoggingOut}
          className={`${controlClassName} border border-slate-300 bg-white text-slate-700 hover:bg-slate-100 disabled:cursor-wait disabled:opacity-60`}
        >
          {isLoggingOut ? "Çıkış yapılıyor…" : "Çıkış yap"}
        </button>
        {errorMessage && (
          <p role="alert" className="w-full text-right text-xs text-amber-800">{errorMessage}</p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <a
        href={getAuthStartUrl()}
        className={`${controlClassName} bg-slate-950 text-white hover:bg-slate-800`}
      >
        Sign in with GitHub
      </a>
      {status === "error" && (
        <button
          type="button"
          onClick={() => void refresh()}
          className={`${controlClassName} border border-slate-300 bg-white text-slate-700 hover:bg-slate-100`}
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
