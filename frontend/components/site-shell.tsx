import Link from "next/link";
import type { ReactNode } from "react";
import { AuthControls } from "./auth-controls";
import { ThemeToggle } from "./theme-toggle";

/** Application chrome shared by the landing page and shareable result pages. */
export function SiteShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-card">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2">
            <div
              aria-hidden="true"
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-sm font-semibold text-white"
            >
              D
            </div>
            <span className="text-lg font-semibold tracking-tight text-slate-950">DevLens</span>
            <span className="hidden rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 sm:inline">Herkese Açık Portföy Analizi</span>
          </Link>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <ThemeToggle />
            <AuthControls />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14 lg:px-8">{children}</main>

      <footer className="border-t border-slate-200 bg-card">
        <div className="mx-auto w-full max-w-6xl px-4 py-5 text-sm text-slate-500 sm:px-6 lg:px-8">
          DevLens · Herkese açık GitHub verilerinden kanıta dayalı portföy analizi
        </div>
      </footer>
    </div>
  );
}
