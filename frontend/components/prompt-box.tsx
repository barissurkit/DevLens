"use client";

import { useEffect, useId, useRef, useState } from "react";
import { copyText } from "../lib/share";

type CopyState = "idle" | "copied" | "failed";

const RESET_MS = 2500;

interface PromptBoxProps {
  prompt: string;
  /** Accessible name of the text area. */
  textLabel: string;
  /** Names what the prompt is for when several boxes are on one page ("İstemi kopyala: repo-adı"). */
  subject?: string;
  note?: string;
}

const buttonClass = "inline-flex min-h-10 items-center rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";

/** The buttons and the read-only text of a ready prompt: show or hide it, read it, copy it. */
export function PromptBox({ prompt, textLabel, subject, note }: PromptBoxProps) {
  const [open, setOpen] = useState(false);
  const [copy, setCopy] = useState<CopyState>("idle");
  const timer = useRef<number | undefined>(undefined);
  const panelId = useId();
  const suffix = subject ? `: ${subject}` : "";

  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copyPrompt() {
    setCopy(await copyText(prompt) ? "copied" : "failed");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopy("idle"), RESET_MS);
  }

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <button type="button" aria-expanded={open} aria-controls={panelId} aria-label={`${open ? "İstemi gizle" : "İstemi göster"}${suffix}`} onClick={() => setOpen((value) => !value)} className={buttonClass}>
          {open ? "İstemi gizle" : "İstemi göster"}
        </button>
        <button
          type="button"
          aria-label={copy === "idle" ? `İstemi kopyala${suffix}` : undefined}
          onClick={() => void copyPrompt()}
          className="inline-flex min-h-10 items-center rounded-lg bg-brand-600 px-4 text-sm font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
        >
          {copy === "copied" ? "Kopyalandı" : copy === "failed" ? "Kopyalanamadı" : "İstemi kopyala"}
        </button>
        <span role="status" aria-live="polite" className="sr-only">
          {copy === "copied" ? "İstem panoya kopyalandı." : copy === "failed" ? "İstem kopyalanamadı; metni açıp elle seçebilirsiniz." : ""}
        </span>
      </div>
      {open && (
        <div id={panelId} className="mt-4 w-full">
          <label htmlFor={`${panelId}-text`} className="sr-only">{textLabel}</label>
          <textarea
            id={`${panelId}-text`}
            readOnly
            value={prompt}
            rows={16}
            onFocus={(event) => event.currentTarget.select()}
            className="w-full resize-y rounded-xl border border-slate-300 bg-slate-50 p-3 font-mono text-xs leading-5 text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          />
          {note && <p className="mt-2 text-xs text-slate-500">{note}</p>}
        </div>
      )}
    </>
  );
}
