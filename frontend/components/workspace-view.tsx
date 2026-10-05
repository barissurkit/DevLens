"use client";

import Link from "next/link";
import { getAuthStartUrl } from "../lib/api";
import { userPath } from "../lib/share";
import { ActionPlan } from "./action-plan";
import { AISuggestedActions } from "./ai-suggested-actions";
import { AnalysisHistory } from "./analysis-history";
import { useAuth } from "./auth-provider";
import { ownProfileAnalysisHref } from "./user-menu";

const primaryLink = "inline-flex min-h-11 items-center justify-center rounded-lg bg-brand-600 px-5 text-sm font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";
const secondaryLink = "inline-flex min-h-11 items-center justify-center rounded-lg border border-slate-300 bg-card px-5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";

/**
 * The signed-in person's own screen: progress over time, AI suggestions and the action plan. Unlike the profile
 * analysis it does not start an analysis; "Profilimi analiz et" is its own action.
 */
export function WorkspaceView() {
  const { status, user, errorMessage, refresh } = useAuth();

  if (status === "loading") {
    return <p role="status" className="py-16 text-center text-slate-600">Çalışma alanın hazırlanıyor…</p>;
  }

  if (status === "error") {
    return (
      <section role="alert" className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-card p-8 text-center shadow-card">
        <h1 className="text-xl font-semibold text-slate-950">Oturum durumu doğrulanamadı</h1>
        <p className="mt-2 text-sm text-slate-600">{errorMessage ?? "Çalışma alanını açmak için oturum bilgin gerekiyor."}</p>
        <button type="button" onClick={() => void refresh()} className={`${secondaryLink} mt-5`}>Yeniden dene</button>
      </section>
    );
  }

  if (status !== "authenticated" || !user) {
    return (
      <section className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-card p-8 text-center shadow-card">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950">Çalışma alanı</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Skor geçmişini, yapay zekâ önerilerini ve aksiyon planını görmek için GitHub ile giriş yap. Herkese açık portföy analizi giriş gerektirmez.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <a href={getAuthStartUrl()} className={primaryLink}>GitHub ile giriş yap</a>
          <Link href="/" className={secondaryLink}>Ana sayfa</Link>
        </div>
      </section>
    );
  }

  const name = user.display_name ?? `@${user.github_login}`;
  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-500">Çalışma alanı</p>
          <h1 className="mt-1 truncate text-3xl font-semibold tracking-tight text-slate-950">{name}</h1>
        </div>
        <div className="flex flex-wrap gap-3">
          <a href={ownProfileAnalysisHref(user.github_login)} className={primaryLink}>Profilimi analiz et</a>
          <Link href={userPath(user.github_login)} className={secondaryLink}>Herkese açık sayfam</Link>
        </div>
      </header>

      <AnalysisHistory key={`history-${user.github_login}`} visible />
      <AISuggestedActions key={`suggestions-${user.github_login}`} username={user.github_login} />
      <ActionPlan />
    </div>
  );
}
