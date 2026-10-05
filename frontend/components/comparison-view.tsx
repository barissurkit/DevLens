"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { analyzePortfolio, ApiError } from "../lib/api";
import { biggestGaps, comparePortfolios, type PortfolioComparison, type RuleComparison } from "../lib/compare";
import { scoreTone } from "../lib/presentation";
import { comparePath, userPath } from "../lib/share";
import type { GitHubPortfolioAnalysis } from "../lib/types";
import { parseGitHubUsername } from "../lib/username";

interface ComparisonViewProps {
  a?: string;
  b?: string;
}

type LoadState =
  | { status: "idle" }
  | { status: "loading"; step: "a" | "b" }
  | { status: "error"; message: string; which: "a" | "b" }
  | { status: "ready"; analysisA: GitHubPortfolioAnalysis; analysisB: GitHubPortfolioAnalysis };

const card = "rounded-2xl border border-slate-200 bg-card p-5 shadow-card sm:p-6";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "github_user_not_found") return "GitHub kullanıcısı bulunamadı.";
    if (error.code === "rate_limited") return "Çok fazla istek gönderildi. Biraz bekleyip tekrar deneyin.";
    return error.message;
  }
  return "Analiz tamamlanamadı.";
}

/** Side-by-side comparison of two public portfolios, scored by the same deterministic rules. */
export function ComparisonView({ a, b }: ComparisonViewProps) {
  const router = useRouter();
  const [first, setFirst] = useState(a ?? "");
  const [second, setSecond] = useState(b ?? "");
  const [formError, setFormError] = useState<string | null>(null);
  const [state, setState] = useState<LoadState>({ status: "idle" });
  const generation = useRef(0);

  useEffect(() => {
    if (!a || !b) return;
    const current = ++generation.current;
    // Both lookups are queued from a timer callback so the state change is not made synchronously in the effect.
    const timer = window.setTimeout(async () => {
      setState({ status: "loading", step: "a" });
      let analysisA: GitHubPortfolioAnalysis;
      try {
        analysisA = await analyzePortfolio(a);
      } catch (error) {
        if (current === generation.current) setState({ status: "error", message: errorMessage(error), which: "a" });
        return;
      }
      if (current !== generation.current) return;
      setState({ status: "loading", step: "b" });
      try {
        const analysisB = await analyzePortfolio(b);
        if (current === generation.current) setState({ status: "ready", analysisA, analysisB });
      } catch (error) {
        if (current === generation.current) setState({ status: "error", message: errorMessage(error), which: "b" });
      }
    }, 0);
    return () => {
      window.clearTimeout(timer);
      generation.current += 1;
    };
  }, [a, b]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsedFirst = parseGitHubUsername(first);
    const parsedSecond = parseGitHubUsername(second);
    if (!parsedFirst.ok) return setFormError(`Birinci kullanıcı: ${parsedFirst.message}`);
    if (!parsedSecond.ok) return setFormError(`İkinci kullanıcı: ${parsedSecond.message}`);
    if (parsedFirst.username.toLowerCase() === parsedSecond.username.toLowerCase()) return setFormError("Karşılaştırmak için iki farklı kullanıcı girin.");
    setFormError(null);
    router.push(comparePath(parsedFirst.username, parsedSecond.username));
  }

  const loading = state.status === "loading";

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-700">Karşılaştırma</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">İki portföyü yan yana gör</h1>
        <p className="mt-3 max-w-2xl leading-7 text-slate-600">Aynı deterministik kurallarla puanlanan iki herkese açık GitHub portföyünü karşılaştır; hangisi hangi alanda önde, neyi diğerinden öğrenebilir gör.</p>
      </header>

      <form onSubmit={handleSubmit} noValidate aria-busy={loading} className={card}>
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <label className="block text-sm font-medium text-slate-900">
            Birinci kullanıcı
            <input value={first} onChange={(event) => setFirst(event.target.value)} placeholder="ör. octocat" disabled={loading} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-4 text-slate-950 outline-none placeholder:text-slate-400 focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20 disabled:bg-slate-100" />
          </label>
          <label className="block text-sm font-medium text-slate-900">
            İkinci kullanıcı
            <input value={second} onChange={(event) => setSecond(event.target.value)} placeholder="ör. torvalds" disabled={loading} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 px-4 text-slate-950 outline-none placeholder:text-slate-400 focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20 disabled:bg-slate-100" />
          </label>
          <button type="submit" disabled={loading} className="min-h-12 rounded-xl bg-brand-600 px-5 font-medium text-white transition hover:bg-primary-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400">
            {loading ? "Karşılaştırılıyor..." : "Karşılaştır"}
          </button>
        </div>
        {formError && <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{formError}</p>}
      </form>

      {state.status === "loading" && (
        <p role="status" className={`${card} text-sm text-slate-600`}>
          {state.step === "a" ? `@${a} analiz ediliyor…` : `@${b} analiz ediliyor…`} <span className="text-slate-500">({state.step === "a" ? 1 : 2} / 2)</span>
        </p>
      )}
      {state.status === "error" && (
        <p role="alert" className="rounded-2xl border border-amber-300 bg-amber-50 px-5 py-4 text-sm text-amber-950">
          <strong className="font-semibold">@{state.which === "a" ? a : b}:</strong> {state.message}
        </p>
      )}
      {state.status === "ready" && <ComparisonResult a={state.analysisA} b={state.analysisB} />}
    </div>
  );
}

function ComparisonResult({ a, b }: { a: GitHubPortfolioAnalysis; b: GitHubPortfolioAnalysis }) {
  const comparison = comparePortfolios(a, b);
  return (
    <div className="space-y-6">
      <section aria-labelledby="compare-scores" className="grid gap-4 md:grid-cols-2">
        <h2 id="compare-scores" className="sr-only">Toplam skorlar</h2>
        <ScoreCard analysis={a} side="a" comparison={comparison} />
        <ScoreCard analysis={b} side="b" comparison={comparison} />
      </section>
      <p role="status" className={`${card} text-sm leading-6 text-slate-700`}>{verdict(a, b, comparison)}</p>

      <section aria-labelledby="compare-dimensions" className={card}>
        <h2 id="compare-dimensions" className="text-lg font-semibold tracking-tight text-slate-950">Boyut boyut</h2>
        <ul className="mt-4 space-y-5">
          {comparison.dimensions.map((dimension) => (
            <li key={dimension.key}>
              <p className="text-sm font-medium text-slate-900">{dimension.label}</p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <Bar name={`@${a.user.username}`} value={dimension.a?.score ?? null} winner={dimension.leader === "a"} />
                <Bar name={`@${b.user.username}`} value={dimension.b?.score ?? null} winner={dimension.leader === "b"} />
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="compare-rules" className={card}>
        <h2 id="compare-rules" className="text-lg font-semibold tracking-tight text-slate-950">Kriter kriter</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <caption className="sr-only">Her kriterin iki portföyde kaç repository&apos;de bulunduğu</caption>
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="pb-2 pr-3 font-semibold">Kriter</th>
                <th scope="col" className="pb-2 pr-3 font-semibold">@{a.user.username}</th>
                <th scope="col" className="pb-2 font-semibold">@{b.user.username}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {comparison.rules.map((rule) => (
                <tr key={rule.key}>
                  <th scope="row" className="py-2.5 pr-3 font-medium text-slate-800">{rule.label}</th>
                  <RuleCell detected={rule.detectedA} analyzed={rule.analyzedA} ahead={rule.leader === "a"} />
                  <RuleCell detected={rule.detectedB} analyzed={rule.analyzedB} ahead={rule.leader === "b"} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="compare-learn" className="grid gap-4 md:grid-cols-2">
        <h2 id="compare-learn" className="sr-only">Birbirinden öğrenebilecekleri</h2>
        <LearnCard name={a.user.username} gaps={biggestGaps(comparison, "a")} from={b.user.username} />
        <LearnCard name={b.user.username} gaps={biggestGaps(comparison, "b")} from={a.user.username} />
      </section>
    </div>
  );
}

function verdict(a: GitHubPortfolioAnalysis, b: GitHubPortfolioAnalysis, comparison: PortfolioComparison): string {
  if (comparison.scoreA === null || comparison.scoreB === null) return "Bir portföy için skor hesaplanamadığından toplam skorlar karşılaştırılamıyor; aşağıdaki kriter bazlı tablo yine de kullanılabilir.";
  if (comparison.leader === "tie") return `@${a.user.username} ve @${b.user.username} aynı skoru aldı (${comparison.scoreA} / 100).`;
  const winner = comparison.leader === "a" ? a : b;
  const loser = comparison.leader === "a" ? b : a;
  return `@${winner.user.username}, @${loser.user.username} portföyünden ${comparison.gap} puan önde (${Math.max(comparison.scoreA, comparison.scoreB)} / ${Math.min(comparison.scoreA, comparison.scoreB)}). Skor, herkese açık repository'lerdeki ölçülebilir sinyallere dayanır; yetkinliğin tamamını ölçmez.`;
}

function ScoreCard({ analysis, side, comparison }: { analysis: GitHubPortfolioAnalysis; side: "a" | "b"; comparison: PortfolioComparison }) {
  const score = side === "a" ? comparison.scoreA : comparison.scoreB;
  const tone = score !== null ? scoreTone(score) : null;
  const leads = comparison.leader === side;
  return (
    <article className={`${card} ${leads ? "ring-2 ring-emerald-500/60" : ""}`}>
      <div className="flex items-center justify-between gap-3">
        <a href={userPath(analysis.user.username)} className="min-w-0 truncate text-lg font-semibold tracking-tight text-slate-950 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600">
          {analysis.user.name || `@${analysis.user.username}`}
        </a>
        {leads && <span className="shrink-0 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">Önde</span>}
      </div>
      <p className="text-sm text-slate-500">@{analysis.user.username} · {analysis.score.scored_repository_count} repository analiz edildi</p>
      <p className={`mt-4 text-5xl font-semibold tracking-tight ${tone?.text ?? "text-slate-950"}`}>{score !== null ? `${score} / 100` : "—"}</p>
      {tone && <span className={`mt-2 inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${tone.badge}`}>{tone.label}</span>}
    </article>
  );
}

function Bar({ name, value, winner }: { name: string; value: number | null; winner: boolean }) {
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="font-medium text-slate-700">{name}</span>
        <span className={winner ? "font-semibold text-emerald-700" : "text-slate-500"}>{value === null ? "—" : `${value}%`}{winner && <span className="sr-only"> (önde)</span>}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100" role="presentation">
        <div className={`h-full rounded-full ${winner ? "bg-emerald-500" : "bg-brand-400"}`} style={{ width: `${value ?? 0}%` }} />
      </div>
    </div>
  );
}

function RuleCell({ detected, analyzed, ahead }: { detected: number; analyzed: number; ahead: boolean }) {
  return (
    <td className={`py-2.5 pr-3 ${ahead ? "font-semibold text-emerald-700" : "text-slate-600"}`}>
      {analyzed > 0 ? `${detected} / ${analyzed}` : "—"}
      {ahead && <span className="sr-only"> (önde)</span>}
    </td>
  );
}

function LearnCard({ name, gaps, from }: { name: string; gaps: RuleComparison[]; from: string }) {
  return (
    <article className={card}>
      <h3 className="text-base font-semibold tracking-tight text-slate-950">@{name} için fırsatlar</h3>
      {gaps.length === 0
        ? <p className="mt-2 text-sm text-slate-600">@{from} portföyünün belirgin biçimde önde olduğu bir kriter yok.</p>
        : (
          <>
            <p className="mt-1 text-sm text-slate-600">@{from} portföyünün daha tutarlı olduğu kriterler:</p>
            <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-slate-700">
              {gaps.map((rule) => <li key={rule.key}>{rule.label}</li>)}
            </ul>
          </>
        )}
    </article>
  );
}

