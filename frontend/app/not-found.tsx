import Link from "next/link";
import { SiteShell } from "../components/site-shell";

export default function NotFound() {
  return (
    <SiteShell>
      <section aria-labelledby="not-found-heading" className="mx-auto max-w-xl py-16 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.14em] text-brand-700">404</p>
        <h1 id="not-found-heading" className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Aradığın sayfa bulunamadı</h1>
        <p className="mt-4 leading-7 text-slate-600">Bağlantı hatalı veya sayfa taşınmış olabilir. Bir GitHub kullanıcı adıyla yeni bir analiz başlatabilirsin.</p>
        <Link href="/" className="mt-8 inline-flex min-h-11 items-center rounded-xl bg-brand-600 px-5 font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2">
          Ana sayfaya dön
        </Link>
      </section>
    </SiteShell>
  );
}
