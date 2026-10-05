"use client";

import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, getSavedProfiles, removeSavedProfile, saveProfile } from "../lib/api";
import { scoreTone } from "../lib/presentation";
import { comparePath, userPath } from "../lib/share";
import type { SavedProfile } from "../lib/types";
import { parseGitHubUsername } from "../lib/username";
import { useAuth } from "./auth-provider";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; profiles: SavedProfile[]; limit: number };

const dateFormat = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric", timeZone: "Europe/Istanbul" });

const cardClass = "rounded-2xl border border-slate-200 bg-card p-6 shadow-card sm:p-8";
const smallButton = "inline-flex min-h-9 items-center justify-center whitespace-nowrap rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60";

function messageFor(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : dateFormat.format(date);
}

/**
 * The profiles the signed-in person keeps to come back to: each with the score of its latest stored analysis,
 * links to analyse or compare it with their own, and a way to add or remove one.
 */
export function SavedProfiles() {
  const { user } = useAuth();
  const own = user?.github_login ?? null;
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [username, setUsername] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const data = await getSavedProfiles();
      setState({ status: "ready", profiles: data.profiles, limit: data.limit });
    } catch (error) {
      setState({ status: "error", message: messageFor(error, "Kayıtlı profiller yüklenemedi.") });
    }
  }, []);

  useEffect(() => {
    // Started from a timer callback so no state is set synchronously inside the effect.
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = parseGitHubUsername(username);
    if (!parsed.ok) {
      setFormError(parsed.message);
      return;
    }
    setFormError(null);
    setBusy("add");
    try {
      const saved = await saveProfile(parsed.username);
      setState((current) => current.status === "ready"
        ? { ...current, profiles: [saved, ...current.profiles.filter((item) => item.id !== saved.id)] }
        : current);
      setUsername("");
    } catch (error) {
      setFormError(messageFor(error, "Profil kaydedilemedi."));
    } finally {
      setBusy(null);
    }
  }

  async function remove(profile: SavedProfile) {
    setBusy(profile.id);
    try {
      await removeSavedProfile(profile.id);
      setState((current) => current.status === "ready" ? { ...current, profiles: current.profiles.filter((item) => item.id !== profile.id) } : current);
    } catch (error) {
      setFormError(messageFor(error, "Profil kaldırılamadı."));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section aria-labelledby="saved-profiles-heading" className={cardClass}>
      <h3 id="saved-profiles-heading" className="text-xl font-semibold tracking-tight text-slate-950">Kayıtlı profiller</h3>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
        Takip etmek ya da kendi portföyünle karşılaştırmak istediğin GitHub profilleri. Skor, o profilin en son kaydedilmiş analizinden gelir; güncel değeri için profili yeniden analiz et.
      </p>

      <form onSubmit={(event) => void add(event)} noValidate className="mt-5 flex flex-col gap-3 sm:flex-row">
        <label htmlFor="saved-profile-username" className="sr-only">Kaydedilecek GitHub kullanıcı adı</label>
        <input
          id="saved-profile-username"
          value={username}
          onChange={(event) => { setUsername(event.target.value); if (formError) setFormError(null); }}
          placeholder="ör. octocat"
          autoComplete="off"
          aria-invalid={formError !== null}
          aria-describedby={formError ? "saved-profile-error" : undefined}
          className="min-h-11 min-w-0 flex-1 rounded-xl border border-slate-300 px-4 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20"
        />
        <button type="submit" disabled={busy === "add"} className="min-h-11 shrink-0 rounded-xl bg-brand-600 px-5 text-sm font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60">
          {busy === "add" ? "Kaydediliyor…" : "Profili kaydet"}
        </button>
      </form>
      {formError && <p id="saved-profile-error" role="alert" className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{formError}</p>}

      {state.status === "loading" && <p role="status" className="mt-5 text-sm text-slate-500">Kayıtlı profiller yükleniyor…</p>}
      {state.status === "error" && (
        <div role="alert" className="mt-5 text-sm">
          <p className="text-red-700">{state.message}</p>
          <button type="button" onClick={() => void load()} className={`${smallButton} mt-3`}>Yeniden dene</button>
        </div>
      )}
      {state.status === "ready" && (state.profiles.length === 0
        ? <p className="mt-5 text-sm leading-6 text-slate-600">Henüz kayıtlı profil yok. Yukarıdan bir kullanıcı adı ekleyebilir ya da bir sonuç sayfasında “Kaydet”e basabilirsin.</p>
        : (
          <>
            <ul className="mt-5 divide-y divide-slate-100">
              {state.profiles.map((profile) => <ProfileRow key={profile.id} profile={profile} own={own} busy={busy === profile.id} onRemove={() => void remove(profile)} />)}
            </ul>
            <p className="mt-3 text-xs text-slate-500">{state.profiles.length} / {state.limit} profil kayıtlı.</p>
          </>
        ))}
    </section>
  );
}

function ProfileRow({ profile, own, busy, onRemove }: { profile: SavedProfile; own: string | null; busy: boolean; onRemove: () => void }) {
  const tone = profile.latest_score !== null ? scoreTone(profile.latest_score) : null;
  const analyzed = formatDate(profile.latest_analyzed_at);
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 py-4">
      <div className="min-w-0">
        <Link href={userPath(profile.username)} className="break-all rounded text-base font-semibold text-brand-700 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600">@{profile.username}</Link>
        <p className="mt-1 text-xs text-slate-500">
          {analyzed ? `En son analiz: ${analyzed}` : "Henüz analiz edilmedi"}
          <span> · Kaydedildi: {formatDate(profile.saved_at)}</span>
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {tone && profile.latest_score !== null
          ? <span className={`rounded-full px-3 py-1 text-sm font-semibold ${tone.badge}`}>{profile.latest_score} / 100 <span className="font-normal">· {tone.label}</span></span>
          : <span className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600">Skor yok</span>}
        <Link href={userPath(profile.username)} className={smallButton}>Analiz et</Link>
        {own && own.toLowerCase() !== profile.username.toLowerCase() && <Link href={comparePath(own, profile.username)} className={smallButton}>Benimle karşılaştır</Link>}
        <button type="button" onClick={onRemove} disabled={busy} aria-label={`@${profile.username} profilini kaldır`} className={smallButton}>Kaldır</button>
      </div>
    </li>
  );
}
