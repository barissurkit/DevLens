"use client";

import { getAuthStartUrl } from "../lib/api";
import { useAuth } from "./auth-provider";

const BENEFITS: Array<{ title: string; text: string }> = [
  { title: "İlerleme geçmişi", text: "Her analizdeki skorun kaydedilir; iyileştirmelerin zamanla nasıl değiştiğini görürsün." },
  { title: "AI önerilen aksiyonlar", text: "Deterministik kanıtlara dayalı, gözden geçirebileceğin somut öneriler alırsın." },
  { title: "Aksiyon planı", text: "Önerileri ve kendi görevlerini tek yerde takip edersin." },
];

const primaryLinkClass =
  "inline-flex min-h-11 items-center rounded-xl bg-brand-600 px-5 text-sm font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";

function signInUrl(): string | null {
  try {
    return getAuthStartUrl();
  } catch {
    return null;
  }
}

/** Shown in place of the actions for anyone who is not looking at their own portfolio. */
export function ActionsLockedPanel() {
  const { status, user } = useAuth();
  const isSignedIn = status === "authenticated" && user !== null;
  const loginUrl = isSignedIn ? null : signInUrl();

  return (
    <section aria-labelledby="actions-locked-heading" className="rounded-2xl border border-slate-200 bg-card p-6 shadow-card sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-700">Kendi portföyün için</p>
      <h3 id="actions-locked-heading" className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {isSignedIn ? "Aksiyonlar yalnızca kendi portföyünde açılır" : "Aksiyonların kilidini aç"}
      </h3>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
        {isSignedIn
          ? "Şu an başka bir kullanıcının herkese açık portföyünü görüntülüyorsun. İlerleme geçmişi, AI önerileri ve aksiyon planı yalnızca hesabına ait portföyde kullanılır."
          : "GitHub ile giriş yaptığında kendi portföyün için aşağıdakilere erişirsin. Giriş yapmadan da herkese açık portföyleri analiz etmeye devam edebilirsin."}
      </p>
      <ul className="mt-5 grid gap-3 sm:grid-cols-3">
        {BENEFITS.map((benefit) => (
          <li key={benefit.title} className="rounded-lg bg-slate-50 p-4">
            <p className="text-sm font-semibold text-slate-950">{benefit.title}</p>
            <p className="mt-1 text-sm leading-6 text-slate-600">{benefit.text}</p>
          </li>
        ))}
      </ul>
      <div className="mt-6">
        {isSignedIn && user ? (
          <a href={`/?workspace=1&username=${encodeURIComponent(user.github_login)}`} className={primaryLinkClass}>
            Kendi portföyünü analiz et
          </a>
        ) : (
          loginUrl && <a href={loginUrl} className={primaryLinkClass}>GitHub ile giriş yap</a>
        )}
      </div>
    </section>
  );
}
