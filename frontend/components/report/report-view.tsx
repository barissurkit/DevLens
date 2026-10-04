"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { analyzePortfolio, ApiError } from "../../lib/api";
import { buildReportModel, REPORT_MODES, type ReportMode } from "../../lib/report";
import { userPath } from "../../lib/share";
import type { GitHubPortfolioAnalysis } from "../../lib/types";
import { BrandMark, BrandWordmark } from "../brand-mark";
import { ReportDocument } from "./report-document";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; analysis: GitHubPortfolioAnalysis; createdAt: Date };

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "github_user_not_found") return "GitHub kullanıcısı bulunamadı.";
    if (error.code === "rate_limited") return "Çok fazla istek gönderildi. Biraz bekleyip tekrar deneyin.";
    return error.message;
  }
  return "Rapor hazırlanamadı.";
}

const buttonClass = "inline-flex min-h-10 items-center justify-center whitespace-nowrap rounded-lg border px-3.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2";

/** The printable report page: a toolbar (screen only) above the A4 sheets filled from the analysis. */
export function ReportView({ username, mode }: { username: string; mode: ReportMode }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  // A report is always printed in the light palette, so it is also shown in it.
  useEffect(() => {
    const root = document.documentElement;
    const previous = root.getAttribute("data-theme");
    root.setAttribute("data-theme", "light");
    return () => {
      if (previous === null) root.removeAttribute("data-theme");
      else root.setAttribute("data-theme", previous);
    };
  }, []);

  useEffect(() => {
    let active = true;
    // Started from a timer callback so no state is set synchronously inside the effect.
    const timer = window.setTimeout(async () => {
      try {
        const analysis = await analyzePortfolio(username);
        if (active) setState({ status: "ready", analysis, createdAt: new Date() });
      } catch (error) {
        if (active) setState({ status: "error", message: errorMessage(error) });
      }
    }, 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [username]);

  useEffect(() => {
    if (state.status === "ready") document.title = `@${username} portföy raporu | DevLens`;
  }, [state.status, username]);

  const model = useMemo(() => (state.status === "ready" ? buildReportModel(state.analysis, mode) : null), [state, mode]);
  const url = typeof window === "undefined" ? userPath(username) : `${window.location.origin}${userPath(username)}`;

  return (
    <div className="min-h-screen bg-slate-100">
      <div className="report-toolbar sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-2.5">
          <div className="flex items-center gap-3">
            <Link href={userPath(username)} className={`${buttonClass} border-slate-300 bg-white text-slate-700 hover:bg-slate-50`}>← Sonuca dön</Link>
            <span className="hidden items-center gap-2 sm:flex"><BrandMark className="h-7 w-7" idPrefix="toolbar" /><BrandWordmark className="text-base" /></span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <nav aria-label="Rapor türü" className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5">
              {REPORT_MODES.map((item) => (
                <Link
                  key={item.mode}
                  href={`${userPath(username)}/rapor?tur=${item.mode}`}
                  aria-current={item.mode === mode ? "page" : undefined}
                  title={item.description}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${item.mode === mode ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <button type="button" onClick={() => window.print()} disabled={state.status !== "ready"} className={`${buttonClass} border-indigo-600 bg-indigo-600 text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300`}>
              Yazdır / PDF olarak kaydet
            </button>
          </div>
        </div>
      </div>

      {state.status === "loading" && <p role="status" className="report-toolbar mx-auto max-w-xl px-4 py-16 text-center text-slate-600">Rapor hazırlanıyor…</p>}
      {state.status === "error" && (
        <div role="alert" className="report-toolbar mx-auto max-w-xl px-4 py-16 text-center">
          <p className="font-semibold text-slate-900">Rapor oluşturulamadı</p>
          <p className="mt-1 text-slate-600">{state.message}</p>
          <Link href={userPath(username)} className={`${buttonClass} mt-5 border-slate-300 bg-white text-slate-700 hover:bg-slate-50`}>Sonuç sayfasına dön</Link>
        </div>
      )}
      {model && state.status === "ready" && <ReportDocument model={model} createdAt={state.createdAt} url={url} />}
    </div>
  );
}
