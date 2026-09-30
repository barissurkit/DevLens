"use client";

import { useEffect, useRef, useState } from "react";
import { userPath } from "../lib/share";

type CopyState = "idle" | "copied" | "failed";

const RESET_MS = 2500;

/** Copies the shareable link of a portfolio result and confirms it for sighted and screen reader users. */
export function CopyLinkButton({ username }: { username: string }) {
  const [state, setState] = useState<CopyState>("idle");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copy() {
    const url = `${window.location.origin}${userPath(username)}`;
    try {
      await navigator.clipboard.writeText(url);
      setState("copied");
    } catch {
      // Clipboard access can be denied or unavailable (insecure context); the address bar already holds the link.
      setState("failed");
    }
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setState("idle"), RESET_MS);
  }

  return (
    <button
      type="button"
      onClick={() => void copy()}
      className="inline-flex min-h-10 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {state === "copied"
          ? <path d="M5 12.5l4.2 4.2L19 7" />
          : <><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" /><path d="M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1-1" /></>}
      </svg>
      {state === "copied" ? "Kopyalandı" : state === "failed" ? "Kopyalanamadı" : "Bağlantıyı kopyala"}
      <span role="status" aria-live="polite" className="sr-only">
        {state === "copied" ? "Bağlantı panoya kopyalandı." : state === "failed" ? "Bağlantı kopyalanamadı; adres çubuğundaki bağlantıyı kullanabilirsiniz." : ""}
      </span>
    </button>
  );
}
