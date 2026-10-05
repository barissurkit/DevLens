import Link from "next/link";
import type { ReactNode } from "react";
import { SiteShell } from "./site-shell";

/** A standalone content page (how it works, scoring, FAQ) inside the normal site chrome, with a way back to the analysis. */
export function InfoPage({ children }: { children: ReactNode }) {
  return (
    <SiteShell>
      <div className="space-y-12">
        {children}
        <section aria-label="Analize başla" className="flex flex-col items-start gap-4 rounded-2xl border border-slate-200 bg-card p-6 shadow-card sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">Kendi portföyünü dene</h2>
            <p className="mt-1 text-sm text-slate-600">Bir GitHub kullanıcı adı yeterli; giriş yapmana gerek yok.</p>
          </div>
          <Link href="/" className="inline-flex min-h-11 items-center justify-center rounded-lg bg-brand-600 px-5 text-sm font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2">
            Analiz et
          </Link>
        </section>
      </div>
    </SiteShell>
  );
}
