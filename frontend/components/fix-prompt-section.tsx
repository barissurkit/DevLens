"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { buildFixPrompt } from "../lib/fix-prompt";
import { copyText } from "../lib/share";
import type { GitHubPortfolioAnalysis } from "../lib/types";

type CopyState = "idle" | "copied" | "failed";

const RESET_MS = 2500;

/**
 * "Yapay zekâ ile düzelt": a ready prompt for the person's own AI assistant or coding agent that lists every gap
 * of the portfolio in the order of the points it would add. It is built in the browser from the analysis, so it
 * costs nothing and never leaves the page until it is copied.
 */
export function FixPromptSection({ analysis }: { analysis: GitHubPortfolioAnalysis }) {
  const prompt = useMemo(() => buildFixPrompt(analysis), [analysis]);
  const [open, setOpen] = useState(false);
  const [copy, setCopy] = useState<CopyState>("idle");
  const timer = useRef<number | undefined>(undefined);
  const panelId = useId();

  useEffect(() => () => window.clearTimeout(timer.current), []);
  if (!prompt) return null;

  async function copyPrompt() {
    setCopy(await copyText(prompt as string) ? "copied" : "failed");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopy("idle"), RESET_MS);
  }

  return (
    <section aria-labelledby="fix-prompt-heading" className="rounded-2xl border border-slate-200 bg-card p-5 shadow-card sm:p-6 print:hidden">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-2xl">
          <h3 id="fix-prompt-heading" className="text-base font-semibold tracking-tight text-slate-950">Yapay zekâ ile düzelt</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Bu portföydeki bütün eksikleri, skora katkısına göre sıralı ve hangi repository&apos;lerde olduklarıyla birlikte tek bir istem olarak hazırladık. İstemi kendi yapay zekâ asistanına ya da kod ajanına ver; eksikleri senin adına pull request olarak kapatsın.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((value) => !value)}
            className="inline-flex min-h-10 items-center rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
          >
            {open ? "İstemi gizle" : "İstemi göster"}
          </button>
          <button
            type="button"
            onClick={() => void copyPrompt()}
            className="inline-flex min-h-10 items-center rounded-lg bg-brand-600 px-4 text-sm font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
          >
            {copy === "copied" ? "Kopyalandı" : copy === "failed" ? "Kopyalanamadı" : "İstemi kopyala"}
          </button>
          <span role="status" aria-live="polite" className="sr-only">
            {copy === "copied" ? "İstem panoya kopyalandı." : copy === "failed" ? "İstem kopyalanamadı; metni açıp elle seçebilirsiniz." : ""}
          </span>
        </div>
      </div>
      {open && (
        <div id={panelId} className="mt-4">
          <label htmlFor={`${panelId}-text`} className="sr-only">Yapay zekâ için düzeltme istemi</label>
          <textarea
            id={`${panelId}-text`}
            readOnly
            value={prompt}
            rows={16}
            onFocus={(event) => event.currentTarget.select()}
            className="w-full resize-y rounded-xl border border-slate-300 bg-slate-50 p-3 font-mono text-xs leading-5 text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          />
          <p className="mt-2 text-xs text-slate-500">
            İstem yalnızca bu sayfadaki analizden üretildi; gizli bilgi içermez. Göndermeden önce okuyup istediğin gibi düzenleyebilirsin.
          </p>
        </div>
      )}
    </section>
  );
}
