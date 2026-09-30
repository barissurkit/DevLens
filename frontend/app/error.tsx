"use client";

import { useEffect } from "react";
import { SiteShell } from "../components/site-shell";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <SiteShell>
      <section aria-labelledby="error-heading" className="mx-auto max-w-xl py-16 text-center">
        <h1 id="error-heading" className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Bir şeyler ters gitti</h1>
        <p className="mt-4 leading-7 text-slate-600">Sayfa beklenmedik bir hatayla karşılaştı. Tekrar deneyebilirsin; sorun sürerse biraz sonra yeniden dene.</p>
        <button
          type="button"
          onClick={reset}
          className="mt-8 inline-flex min-h-11 items-center rounded-xl bg-indigo-600 px-5 font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
        >
          Tekrar dene
        </button>
      </section>
    </SiteShell>
  );
}
