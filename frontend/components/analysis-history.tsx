"use client";

import { useEffect, useState } from "react";
import { ApiError, getAnalysisHistory } from "../lib/api";
import type { HistoryResponse } from "../lib/types";
import { useAuth } from "./auth-provider";

export function AnalysisHistory({ visible }: { visible: boolean }) {
  const { user } = useAuth();
  const [state, setState] = useState<{ status: "loading" | "ready" | "error"; data: HistoryResponse | null; message: string | null }>({ status: "loading", data: null, message: null });
  const identity = user?.github_login ?? null;

  useEffect(() => {
    let active = true;
    if (!visible || !identity) return () => { active = false; };
    void getAnalysisHistory().then((data) => {
      if (active) setState({ status: "ready", data, message: null });
    }).catch((error: unknown) => {
      if (active) setState({ status: "error", data: null, message: error instanceof ApiError ? error.message : "Geçmiş analizler yüklenemedi." });
    });
    return () => { active = false; };
  }, [identity, visible]);

  if (!visible || !identity) return null;
  if (state.status === "loading") return <section aria-labelledby="history-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h3 id="history-heading" className="text-xl font-semibold">İlerleme</h3><p className="mt-3 text-sm text-slate-500">Geçmiş analizler yükleniyor...</p></section>;
  if (state.status === "error") return <section aria-labelledby="history-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h3 id="history-heading" className="text-xl font-semibold">İlerleme</h3><p role="alert" className="mt-3 text-sm text-red-700">{state.message}</p></section>;
  const data = state.data;
  if (!data || !data.latest) return <HistoryCard title="İlerleme"><p className="text-sm leading-6 text-slate-600">Henüz bir geçmiş analiz kaydı yok. Bu analiz başlangıç noktası olarak kullanılacak.</p></HistoryCard>;
  const delta = data.comparison;
  return <HistoryCard title="İlerleme">
    <div className="grid gap-3 sm:grid-cols-3">
      <Metric label="Güncel skor" value={data.latest.portfolio_score === null ? "—" : String(data.latest.portfolio_score)} />
      <Metric label="Önceki skor" value={data.previous?.portfolio_score === null || data.previous?.portfolio_score === undefined ? "—" : String(data.previous.portfolio_score)} />
      <Metric label="Değişim" value={!delta || !delta.comparable || delta.portfolio_score === null ? "—" : formatDelta(delta.portfolio_score)} />
    </div>
    {!data.previous && <p className="mt-4 text-sm text-slate-600">Bu analiz mevcut baseline&apos;ınız. Değişimi görmek için daha sonra yeniden analiz edin.</p>}
    {delta?.note && <p className="mt-4 text-sm text-amber-800">{delta.note}</p>}
    {delta?.comparable && delta.category_scores.length > 0 && <ul className="mt-4 flex flex-wrap gap-2">{delta.category_scores.map((item) => <li key={item.key} className="rounded-full bg-slate-50 px-3 py-1.5 text-sm text-slate-700">{item.label}: {formatDelta(item.delta)}</li>)}</ul>}
    <h4 className="mt-6 text-sm font-medium text-slate-900">Geçmiş</h4>
    <ol className="mt-3 space-y-2">{data.history.map((item) => <li key={item.id} className="flex justify-between gap-4 border-b border-slate-100 py-2 text-sm"><time dateTime={item.captured_at} className="text-slate-600">{formatDate(item.captured_at)}</time><span className="font-medium text-slate-900">{item.portfolio_score === null ? "—" : item.portfolio_score}</span></li>)}</ol>
    <p className="mt-4 text-xs text-slate-500">Değişimler, DevLens deterministik portföy kriterlerine göredir.</p>
  </HistoryCard>;
}

function HistoryCard({ title, children }: { title: string; children: React.ReactNode }) { return <section aria-labelledby="history-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"><h3 id="history-heading" className="text-xl font-semibold tracking-tight text-slate-950">{title}</h3><div className="mt-5">{children}</div></section>; }
function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p></div>; }
function formatDelta(value: number) { return value > 0 ? `+${value}` : String(value); }
function formatDate(value: string) { return new Intl.DateTimeFormat("tr-TR", { dateStyle: "medium", timeZone: "Europe/Istanbul" }).format(new Date(value)); }
