"use client";

import { type FormEvent, type ReactNode, useRef, useState } from "react";
import { AnalysisErrorState } from "./analysis-error-state";
import { AnalysisLoadingState } from "./analysis-loading-state";
import { AnalysisResultShell } from "./analysis-result-shell";
import { useAnalysis } from "./use-analysis";

const MAX_USERNAME_LENGTH = 39;

interface AnalysisFormProps {
  /** Landing-only content: shown until a result is available. */
  hero?: ReactNode;
  preview?: ReactNode;
  features?: ReactNode;
}

export function AnalysisForm({ hero, preview, features }: AnalysisFormProps) {
  const [username, setUsername] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const usernameInputRef = useRef<HTMLInputElement>(null);
  const { state, submit, retry, reanalyze, resetToIdle } = useAnalysis(() => setValidationMessage(null));

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedUsername = username.trim();
    const message = !normalizedUsername
      ? "Bir GitHub kullanıcı adı girin."
      : normalizedUsername.length > MAX_USERNAME_LENGTH
        ? "GitHub kullanıcı adı 39 karakterden uzun olamaz."
        : null;
    setValidationMessage(message);
    if (message) {
      resetToIdle();
      usernameInputRef.current?.focus();
    } else {
      void submit(normalizedUsername);
    }
  }

  const isLoading = state.status === "loading";
  const hasValidationError = validationMessage !== null;

  const showResult = state.status === "success";

  return (
    <div className="space-y-10">
      <div className={showResult ? "" : "grid items-center gap-10 lg:grid-cols-2 lg:gap-16"}>
        <div className="min-w-0">
          {!showResult && hero}
          <form onSubmit={handleSubmit} noValidate aria-busy={isLoading} className={`rounded-xl border border-slate-200 bg-white p-5 sm:p-6 ${showResult ? "shadow-card" : "shadow-raised"}`}>
        <label htmlFor="github-username" className="block text-sm font-medium text-slate-900">GitHub kullanıcı adı</label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row">
          <input
            ref={usernameInputRef}
            id="github-username"
            name="username"
            value={username}
            onChange={(event) => {
              setUsername(event.target.value);
              if (validationMessage) setValidationMessage(null);
            }}
            placeholder="ör. barissurkit"
            autoComplete="username"
            required
            disabled={isLoading}
            aria-invalid={hasValidationError}
            aria-describedby={hasValidationError ? "analysis-validation-error" : "username-hint"}
            className="min-h-12 min-w-0 flex-1 rounded-xl border border-slate-300 px-4 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-600"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="min-h-12 shrink-0 rounded-xl bg-indigo-600 px-5 font-medium text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:text-slate-100"
          >
            {isLoading ? "Analiz ediliyor..." : "Analiz et"}
          </button>
        </div>
        <p id="username-hint" className="mt-3 text-sm text-slate-500">Herkese açık repository kanıtlarını incelemek için kullanıcı adını girin.</p>
        {validationMessage && (
          <p id="analysis-validation-error" role="alert" aria-live="assertive" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {validationMessage}
          </p>
        )}
        {isLoading && <AnalysisLoadingState />}
        {state.status === "error" && <AnalysisErrorState error={state.error} onRetry={retry} />}
          </form>
        </div>
        {!showResult && preview}
      </div>
      {!showResult && features}
      {state.status === "success" && <AnalysisResultShell result={state.result} onReanalyze={reanalyze} />}
    </div>
  );
}
