"use client";

import { useMemo } from "react";
import { buildFixPrompt } from "../lib/fix-prompt";
import type { GitHubPortfolioAnalysis } from "../lib/types";
import { PromptBox } from "./prompt-box";

/**
 * "Yapay zekâ ile düzelt": a ready prompt for the person's own AI assistant or coding agent that lists every gap
 * of the portfolio in the order of the points it would add. It is built in the browser from the analysis, so it
 * costs nothing and never leaves the page until it is copied.
 */
export function FixPromptSection({ analysis }: { analysis: GitHubPortfolioAnalysis }) {
  const prompt = useMemo(() => buildFixPrompt(analysis), [analysis]);
  if (!prompt) return null;

  return (
    <section aria-labelledby="fix-prompt-heading" className="rounded-2xl border border-slate-200 bg-card p-5 shadow-card sm:p-6 print:hidden">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-2xl">
          <h3 id="fix-prompt-heading" className="text-base font-semibold tracking-tight text-slate-950">Yapay zekâ ile düzelt</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Bu portföydeki bütün eksikleri, skora katkısına göre sıralı ve hangi repository&apos;lerde olduklarıyla birlikte tek bir istem olarak hazırladık. İstemi kendi yapay zekâ asistanına ya da kod ajanına ver; eksikleri senin adına pull request olarak kapatsın. Tek bir repository için istemi, Repository&apos;ler sekmesindeki kartında bulabilirsin.
          </p>
        </div>
      </div>
      <div className="mt-4">
        <PromptBox
          prompt={prompt}
          textLabel="Yapay zekâ için düzeltme istemi"
          note="İstem yalnızca bu sayfadaki analizden üretildi; gizli bilgi içermez. Göndermeden önce okuyup istediğin gibi düzenleyebilirsin."
        />
      </div>
    </section>
  );
}
