import Link from "next/link";
import type { ReactNode } from "react";
import { AuthControls } from "./auth-controls";
import { AuthNotice } from "./auth-notice";
import { BrandMark, BrandWordmark } from "./brand-mark";
import { ThemeToggle } from "./theme-toggle";

const NAV_LINKS: Array<{ href: string; label: string }> = [
  { href: "/#nasil-calisir", label: "Nasıl çalışır" },
  { href: "/#puanlama", label: "Puanlama" },
  { href: "/#sss", label: "Sık sorulanlar" },
];

const focusRing = "focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2";

/** Application chrome shared by the landing page and shareable result pages. */
export function SiteShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main-content" className="sr-only rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50">
        Ana içeriğe geç
      </a>
      <header className="sticky top-0 z-30 print:hidden border-b border-slate-200/80 bg-card/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-4 py-2.5 sm:px-6 lg:px-8">
          <div className="flex items-center gap-8">
            <Link href="/" className={`flex items-center gap-2.5 rounded-lg ${focusRing}`}>
              <BrandMark className="h-9 w-9" idPrefix="header" />
              <BrandWordmark className="text-xl" />
            </Link>
            <nav aria-label="Ana gezinme" className="hidden items-center gap-1 md:flex">
              {NAV_LINKS.map((link) => (
                <Link key={link.href} href={link.href} className={`rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-950 ${focusRing}`}>
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center justify-end gap-2 sm:gap-3">
            <div className="hidden sm:block"><ThemeToggle /></div>
            <AuthControls />
          </div>
        </div>
      </header>
      <AuthNotice />

      <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 focus:outline-none print:max-w-none print:p-0 sm:px-6 sm:py-12 lg:px-8">{children}</main>

      <footer className="border-t border-slate-200 bg-card print:hidden">
        <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-10 text-sm sm:px-6 md:grid-cols-[1.4fr_1fr_1fr] lg:px-8">
          <div>
            <div className="flex items-center gap-2.5">
              <BrandMark className="h-8 w-8" idPrefix="footer" />
              <BrandWordmark className="text-lg" />
            </div>
            <div className="mt-4 sm:hidden"><ThemeToggle /></div>
            <p className="mt-3 max-w-sm leading-6 text-slate-600">
              Herkese açık GitHub verilerinden kanıta dayalı portföy analizi. Skorlar deterministik kurallarla hesaplanır; yapay zekâ yalnızca yorumlar.
            </p>
          </div>
          <nav aria-label="Ürün">
            <p className="font-semibold text-slate-950">Ürün</p>
            <ul className="mt-3 space-y-2 text-slate-600">
              {NAV_LINKS.map((link) => (
                <li key={link.href}><Link href={link.href} className={`rounded hover:text-slate-950 hover:underline ${focusRing}`}>{link.label}</Link></li>
              ))}
            </ul>
          </nav>
          <nav aria-label="Kaynaklar">
            <p className="font-semibold text-slate-950">Kaynaklar</p>
            <ul className="mt-3 space-y-2 text-slate-600">
              <li><a href="https://github.com/barissurkit/DevLens" target="_blank" rel="noreferrer" className={`rounded hover:text-slate-950 hover:underline ${focusRing}`}>Kaynak kod (GitHub)</a></li>
              <li><a href="https://github.com/barissurkit/DevLens#readme" target="_blank" rel="noreferrer" className={`rounded hover:text-slate-950 hover:underline ${focusRing}`}>Belgeler</a></li>
            </ul>
          </nav>
        </div>
        <div className="border-t border-slate-200">
          <p className="mx-auto w-full max-w-6xl px-4 py-4 text-xs text-slate-500 sm:px-6 lg:px-8">
            DevLens · Herkese açık GitHub verilerinden kanıta dayalı portföy analizi
          </p>
        </div>
      </footer>
    </div>
  );
}
