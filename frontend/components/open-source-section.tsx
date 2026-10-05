"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, getOpenSourceContributions } from "../lib/api";
import type { OpenSourceContribution, OpenSourceContributions } from "../lib/types";

type LoadState =
  | { status: "idle" | "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: OpenSourceContributions };

const number = new Intl.NumberFormat("tr-TR");
const monthFormat = new Intl.DateTimeFormat("tr-TR", { month: "long", year: "numeric", timeZone: "Europe/Istanbul" });

const cardClass = "rounded-2xl border border-slate-200 bg-card p-5 shadow-card sm:p-6";

function mergedDate(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : monthFormat.format(date);
}

/**
 * Merged pull requests the person made to other people's public repositories. This is evidence the portfolio
 * score does not use (it only looks at their own repositories), so it is a separate view. It is fetched the first
 * time the tab is opened, because it costs GitHub search requests.
 */
export function OpenSourceSection({ username, active }: { username: string; active: boolean }) {
  const [state, setState] = useState<LoadState>({ status: "idle" });
  const requested = useRef<string | null>(null);

  async function load() {
    requested.current = username;
    setState({ status: "loading" });
    try {
      const data = await getOpenSourceContributions(username);
      if (requested.current === username) setState({ status: "ready", data });
    } catch (error) {
      if (requested.current !== username) return;
      setState({ status: "error", message: error instanceof ApiError ? error.message : "Açık kaynak katkıları yüklenemedi." });
    }
  }

  useEffect(() => {
    if (!active || requested.current === username) return;
    // Started from a timer callback so no state is set synchronously inside the effect.
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load only reads the username that is already a dependency
  }, [active, username]);

  return (
    <section aria-labelledby="open-source-heading" className="space-y-4">
      <div className={cardClass}>
        <h3 id="open-source-heading" className="text-xl font-semibold tracking-tight text-slate-950">Açık kaynak katkıları</h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          @{username} adlı kullanıcının, başkalarına ait herkese açık repository&apos;lere yaptığı ve <strong className="font-semibold text-slate-900">birleştirilen</strong> pull request&apos;ler. Portföy skoru yalnızca kişinin kendi repository&apos;lerine bakar; bu bölüm skora katılmaz.
        </p>
      </div>

      {(state.status === "idle" || state.status === "loading") && (
        <p role="status" className={`${cardClass} text-sm text-slate-600`}>Katkılar GitHub&apos;dan alınıyor…</p>
      )}

      {state.status === "error" && (
        <div role="alert" className={`${cardClass} text-sm`}>
          <p className="text-red-700">{state.message}</p>
          <button type="button" onClick={() => void load()} className="mt-3 inline-flex min-h-10 items-center rounded-lg border border-slate-300 bg-card px-3 font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600">
            Yeniden dene
          </button>
        </div>
      )}

      {state.status === "ready" && <Contributions data={state.data} />}
    </section>
  );
}

function Contributions({ data }: { data: OpenSourceContributions }) {
  if (data.contributions.length === 0) {
    return (
      <p className={`${cardClass} text-sm leading-6 text-slate-600`}>
        Başkalarının herkese açık repository&apos;lerinde birleştirilmiş bir pull request bulunamadı.
      </p>
    );
  }
  return (
    <>
      <dl className="grid gap-3 sm:grid-cols-2">
        <Stat label="Birleştirilen pull request" value={`${number.format(data.total_merged)}${data.is_truncated ? "+" : ""}`} />
        <Stat label="Katkı yapılan repository" value={number.format(data.repository_count)} />
      </dl>
      <ul className="space-y-3">
        {data.contributions.map((item) => <ContributionRow key={item.repository} item={item} />)}
      </ul>
      {data.is_truncated && (
        <p className="text-xs leading-5 text-slate-500">
          GitHub aramasının kapsadığı en son birleştirilmiş pull request&apos;ler gösteriliyor; daha eskileri varsa burada yer almıyor.
        </p>
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className={cardClass}>
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">{value}</dd>
    </div>
  );
}

function ContributionRow({ item }: { item: OpenSourceContribution }) {
  const date = mergedDate(item.latest_merged_at);
  return (
    <li className={cardClass}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <a href={item.html_url} target="_blank" rel="noreferrer" className="break-all rounded text-base font-semibold text-brand-700 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600">
          {item.repository}
        </a>
        <p className="flex items-center gap-3 text-sm text-slate-600">
          {item.stars !== null && (
            <span><span aria-hidden="true">★</span> {number.format(item.stars)}<span className="sr-only"> yıldız</span></span>
          )}
          <span className="font-medium text-slate-900">{item.merged_count} birleşen PR</span>
        </p>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        Son: <a href={item.latest_url} target="_blank" rel="noreferrer" className="rounded text-slate-900 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600">{item.latest_title}</a>
        {date && <span className="text-slate-500"> · {date}</span>}
      </p>
    </li>
  );
}
