"use client";

import { useEffect, useRef, useState } from "react";
import { badgeMarkdown, copyText } from "../lib/share";

type CopyState = "idle" | "copied" | "failed";

const RESET_MS = 2500;

/** Copies README markdown for the DevLens score badge of a portfolio. */
export function BadgeButton({ username }: { username: string }) {
  const [state, setState] = useState<CopyState>("idle");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const markdown = badgeMarkdown(username, window.location.origin);
  if (!markdown) return null;

  async function copy() {
    setState(await copyText(markdown as string) ? "copied" : "failed");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setState("idle"), RESET_MS);
  }

  return (
    <button
      type="button"
      onClick={() => void copy()}
      title="Skorunu README dosyanda göstermek için Markdown kodunu kopyalar"
      className="inline-flex min-h-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 8l-4 4 4 4M16 8l4 4-4 4M14 5l-4 14" /></svg>
      {state === "copied" ? "Rozet kodu kopyalandı" : state === "failed" ? "Kopyalanamadı" : "README rozeti"}
      <span role="status" aria-live="polite" className="sr-only">
        {state === "copied" ? "Rozetin Markdown kodu panoya kopyalandı." : state === "failed" ? "Rozet kodu kopyalanamadı." : ""}
      </span>
    </button>
  );
}
