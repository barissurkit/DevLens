"use client";

import { useEffect, useState } from "react";
import type { AnalysisProgress, AnalysisProgressStage } from "../lib/types";

const LONG_REQUEST_THRESHOLD_MS = 8_000;

const STAGE_ORDER: readonly AnalysisProgressStage[] = ["profile", "repositories", "interpretation"];

const GENERIC_STEPS = [
  "GitHub profili ve repository listesi alınır",
  "Her repository için deterministik kanıtlar hesaplanır",
  "Portföy skoru ve AI yorumu hazırlanır",
];

interface AnalysisLoadingStateProps {
  /** Streamed progress; when absent (older backend) a generic list of typical steps is shown. */
  progress?: AnalysisProgress | null;
}

export function AnalysisLoadingState({ progress = null }: AnalysisLoadingStateProps) {
  const [isLongRunning, setIsLongRunning] = useState(false);

  useEffect(() => {
    const timeout = window.setTimeout(() => setIsLongRunning(true), LONG_REQUEST_THRESHOLD_MS);

    return () => window.clearTimeout(timeout);
  }, []);

  return (
    <div
      role="status"
      aria-live="polite"
      className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600"
    >
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600 motion-reduce:animate-none"
        />
        <span>
          <strong className="font-medium text-slate-900">GitHub portföyü analiz ediliyor...</strong>{" "}
          Bu işlem repository sayısına göre birkaç saniye sürebilir.
        </span>
      </div>
      {progress ? <ProgressSteps progress={progress} /> : (
        <ol className="mt-3 list-decimal space-y-1 pl-9 text-slate-500">
          {GENERIC_STEPS.map((step) => <li key={step}>{step}</li>)}
        </ol>
      )}
      {isLongRunning && (
        <p className="mt-3 border-t border-slate-200 pt-3 text-slate-600">
          Analiz beklenenden uzun sürüyor. Ücretsiz sunucu uyanıyor olabilir; işlem devam ediyor, sayfayı açık tutabilirsiniz.
        </p>
      )}
    </div>
  );
}

type StepState = "done" | "active" | "pending";

function stepState(step: AnalysisProgressStage, current: AnalysisProgressStage): StepState {
  const stepIndex = STAGE_ORDER.indexOf(step);
  const currentIndex = STAGE_ORDER.indexOf(current);
  if (stepIndex < currentIndex) return "done";
  return stepIndex === currentIndex ? "active" : "pending";
}

function ProgressSteps({ progress }: { progress: AnalysisProgress }) {
  const repositoriesDone = progress.total > 0 ? progress.completed : 0;
  const repositoryPercent = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;
  const showRepositoryBar = progress.stage === "repositories" && progress.total > 0;

  return (
    <ol className="mt-3 space-y-2">
      <Step state={stepState("profile", progress.stage)} label="GitHub profili ve repository listesi alınıyor" />
      <Step
        state={stepState("repositories", progress.stage)}
        label={progress.total > 0 && progress.stage !== "profile"
          ? `Repository'ler analiz ediliyor (${repositoriesDone} / ${progress.total})`
          : "Repository'ler analiz ediliyor"}
      >
        {showRepositoryBar && (
          <div
            role="progressbar"
            aria-label="Repository analizi ilerlemesi"
            aria-valuemin={0}
            aria-valuemax={progress.total}
            aria-valuenow={progress.completed}
            aria-valuetext={`${progress.completed} / ${progress.total} repository`}
            className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-200"
          >
            <div className="h-full rounded-full bg-indigo-600 transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${repositoryPercent}%` }} />
          </div>
        )}
      </Step>
      {progress.stage === "interpretation" && (
        <Step state="active" label="AI yorumu hazırlanıyor" />
      )}
    </ol>
  );
}

function Step({ state, label, children }: { state: StepState; label: string; children?: React.ReactNode }) {
  const tone = state === "done" ? "text-slate-500" : state === "active" ? "font-medium text-slate-900" : "text-slate-400";
  return (
    <li className="flex items-start gap-2.5">
      <span aria-hidden="true" className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
        {state === "done"
          ? <svg viewBox="0 0 16 16" className="h-4 w-4 text-emerald-600" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 8.5l3.2 3L13 4.5" /></svg>
          : <span className={`h-2 w-2 rounded-full ${state === "active" ? "bg-indigo-600" : "bg-slate-300"}`} />}
      </span>
      <div className={`min-w-0 flex-1 ${tone}`}>
        <span>{label}</span>
        {state === "done" && <span className="sr-only"> (tamamlandı)</span>}
        {children}
      </div>
    </li>
  );
}
