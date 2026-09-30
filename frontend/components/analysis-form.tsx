"use client";

import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";
import { AnalysisErrorState } from "./analysis-error-state";
import { AnalysisLoadingState } from "./analysis-loading-state";
import { AnalysisResultShell } from "./analysis-result-shell";
import { useAuth } from "./auth-provider";
import { useAnalysis } from "./use-analysis";
import { userPath } from "../lib/share";
import { EXAMPLE_USERNAMES, liveUsernameHint, parseGitHubUsername } from "../lib/username";

interface AnalysisFormProps {
  /** Landing-only content: shown until a result is available. */
  hero?: ReactNode;
  preview?: ReactNode;
  features?: ReactNode;
  /** A login to analyze as soon as the page has loaded (shareable /u/[username] pages). */
  initialUsername?: string;
}

export function AnalysisForm({ hero, preview, features, initialUsername }: AnalysisFormProps) {
  const { status: authStatus } = useAuth();
  const [username, setUsername] = useState(initialUsername ?? "");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const usernameInputRef = useRef<HTMLInputElement>(null);
  const { state, submit, retry, reanalyze, retryInterpretation, resetToIdle } = useAnalysis(() => setValidationMessage(null));

  // Start the linked analysis once the session state is known: the analysis lifecycle resets itself
  // whenever the signed-in identity changes, so starting earlier would be cancelled by that reset.
  const startedInitial = useRef(false);
  useEffect(() => {
    if (!initialUsername || startedInitial.current || authStatus === "loading") return;
    startedInitial.current = true;
    void submit(initialUsername);
  }, [initialUsername, authStatus, submit]);

  // Keep the address bar on the shareable link of the result being shown.
  const shownUsername = state.status === "success" ? state.result.analysis.user.username : null;
  useEffect(() => {
    if (!shownUsername) return;
    const path = userPath(shownUsername);
    if (window.location.pathname !== path) window.history.replaceState(window.history.state, "", path);
  }, [shownUsername]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = parseGitHubUsername(username);
    setValidationMessage(parsed.ok ? null : parsed.message);
    if (!parsed.ok) {
      resetToIdle();
      usernameInputRef.current?.focus();
      return;
    }
    // A pasted profile link or "@name" is shown back as the plain username that is analyzed.
    setUsername(parsed.username);
    void submit(parsed.username);
  }

  function handleExample(example: string) {
    setUsername(example);
    setValidationMessage(null);
    void submit(example);
  }

  const isLoading = state.status === "loading";
  const hasValidationError = validationMessage !== null;
  const liveHint = hasValidationError ? null : liveUsernameHint(username);

  const showResult = state.status === "success";

  return (
    <div className="space-y-10">
      <div className={showResult ? "" : "grid items-center gap-10 lg:grid-cols-2 lg:gap-16"}>
        <div className="min-w-0">
          {!showResult && hero}
          <form onSubmit={handleSubmit} noValidate aria-busy={isLoading} className={`rounded-xl border border-slate-200 bg-card p-5 sm:p-6 ${showResult ? "shadow-card" : "shadow-raised"}`}>
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
            className="min-h-12 shrink-0 rounded-xl bg-indigo-600 px-5 font-medium text-white transition hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:text-slate-100"
          >
            {isLoading ? "Analiz ediliyor..." : "Analiz et"}
          </button>
        </div>
        <p id="username-hint" aria-live="polite" className={`mt-3 text-sm ${liveHint ? "text-amber-700" : "text-slate-500"}`}>
          {liveHint ?? "Kullanıcı adını, @kullanici veya bir github.com/kullanici bağlantısını girebilirsiniz."}
        </p>
        {validationMessage && (
          <p id="analysis-validation-error" role="alert" aria-live="assertive" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {validationMessage}
          </p>
        )}
        {!showResult && !isLoading && (
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
            <span className="text-sm text-slate-500">Örnek dene:</span>
            {EXAMPLE_USERNAMES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => handleExample(example)}
                className="inline-flex min-h-9 items-center rounded-full border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:border-indigo-600 hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
              >
                {example}
              </button>
            ))}
          </div>
        )}
        {isLoading && <AnalysisLoadingState progress={state.status === "loading" ? state.progress : null} />}
        {state.status === "error" && <AnalysisErrorState error={state.error} onRetry={retry} />}
          </form>
        </div>
        {!showResult && preview}
      </div>
      {!showResult && features}
      {state.status === "success" && <AnalysisResultShell result={state.result} onReanalyze={reanalyze} onRetryInterpretation={retryInterpretation} />}
    </div>
  );
}
