"use client";

import { useEffect, useState } from "react";
import { ApiError, getSavedProfiles, removeSavedProfile, saveProfile } from "../lib/api";
import { useAuth } from "./auth-provider";

type State =
  | { status: "loading" }
  | { status: "unsaved" }
  | { status: "saved"; id: string }
  | { status: "unavailable" };

const buttonClass = "inline-flex min-h-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60";

/**
 * "Kaydet" on a result page: keeps the profile in the signed-in person's workspace (and takes it out again).
 * It is not shown to visitors or on the person's own portfolio.
 */
export function SaveProfileButton({ username }: { username: string }) {
  const { status, user } = useAuth();
  const [state, setState] = useState<State>({ status: "loading" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const signedIn = status === "authenticated" && user !== null;
  const isOwn = signedIn && user.github_login.toLowerCase() === username.toLowerCase();

  useEffect(() => {
    if (!signedIn || isOwn) return;
    let active = true;
    // Started from a timer callback so no state is set synchronously inside the effect.
    const timer = window.setTimeout(async () => {
      try {
        const { profiles } = await getSavedProfiles();
        const found = profiles.find((item) => item.username.toLowerCase() === username.toLowerCase());
        if (active) setState(found ? { status: "saved", id: found.id } : { status: "unsaved" });
      } catch {
        if (active) setState({ status: "unavailable" });
      }
    }, 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [signedIn, isOwn, username]);

  if (!signedIn || isOwn || state.status === "unavailable") return null;

  async function toggle() {
    if (state.status === "loading") return;
    setBusy(true);
    setMessage(null);
    try {
      if (state.status === "saved") {
        await removeSavedProfile(state.id);
        setState({ status: "unsaved" });
      } else {
        const saved = await saveProfile(username);
        setState({ status: "saved", id: saved.id });
      }
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "İşlem tamamlanamadı.");
    } finally {
      setBusy(false);
    }
  }

  const saved = state.status === "saved";
  return (
    <>
      <button type="button" onClick={() => void toggle()} disabled={busy || state.status === "loading"} aria-pressed={saved} className={buttonClass}>
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill={saved ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 4h12v17l-6-4-6 4z" /></svg>
        {saved ? "Kayıtlı" : "Kaydet"}
      </button>
      {message && <span role="alert" className="basis-full text-xs text-red-700">{message}</span>}
    </>
  );
}
