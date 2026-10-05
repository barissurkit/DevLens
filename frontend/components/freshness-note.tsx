"use client";

import { useEffect, useState } from "react";

const TICK_MS = 30_000;

/** Turkish relative age, e.g. "4 dakika önce"; "az önce" below 45 seconds. */
export function formatAge(generatedAtMs: number, nowMs: number): string {
  const seconds = Math.max(0, Math.round((nowMs - generatedAtMs) / 1000));
  if (seconds < 45) return "az önce";
  const formatter = new Intl.RelativeTimeFormat("tr", { numeric: "always" });
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return formatter.format(-minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (hours < 24) return formatter.format(-hours, "hour");
  return formatter.format(-Math.round(hours / 24), "day");
}

interface FreshnessNoteProps {
  /** ISO 8601 time the deterministic analysis was computed. */
  generatedAt: string;
  /** Whether the analysis was served from the server-side snapshot cache. */
  cached: boolean;
  onRefresh: () => void;
}

export function FreshnessNote({ generatedAt, cached, onRefresh }: FreshnessNoteProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

  const generatedMs = Date.parse(generatedAt);
  if (Number.isNaN(generatedMs)) return null;

  return (
    <div className="mt-5 flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t border-slate-100 pt-4 text-sm text-slate-500">
      <p>
        Sonuç <time dateTime={generatedAt} title={new Date(generatedMs).toLocaleString("tr-TR")} className="font-medium text-slate-700">{formatAge(generatedMs, now)}</time> hesaplandı
        {cached && <span> · önbellekten sunuldu</span>}.
      </p>
      <button
        type="button"
        onClick={onRefresh}
        className="print:hidden inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 12a8 8 0 1 1-2.34-5.66M20 4v5h-5" /></svg>
        Yenile
      </button>
    </div>
  );
}
