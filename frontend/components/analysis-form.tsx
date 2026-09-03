"use client";

import { startTransition, type FormEvent, useEffect, useRef, useState } from "react";
import { analyzePortfolioWithInterpretation, ApiError } from "../lib/api";
import type { GitHubPortfolioInterpretationResponse } from "../lib/types";
import { AnalysisErrorState } from "./analysis-error-state";
import { AnalysisLoadingState } from "./analysis-loading-state";
import { AnalysisResultShell } from "./analysis-result-shell";
import { useAuth } from "./auth-provider";

const MAX_USERNAME_LENGTH = 39;

export function AnalysisForm() {
  const { status, user } = useAuth();
  const [username, setUsername] = useState("");
  const [state, setState] = useState<AnalysisState>({ status: "idle" });
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const usernameInputRef = useRef<HTMLInputElement>(null);
  const requestGeneration = useRef(0);
  const targetRef = useRef<string | null>(null);
  const authContextRef = useRef("");
  const authContextKey = `${status}:${user?.github_login ?? "anonymous"}`;
  authContextRef.current = authContextKey;

  useEffect(() => {
    requestGeneration.current += 1;
    if (status !== "authenticated") {
      targetRef.current = null;
      startTransition(() => { setState({ status: "idle" }); setValidationMessage(null); });
    } else {
      startTransition(() => setState({ status: "idle" }));
    }
  }, [authContextKey, status]);

  useEffect(() => {
    if (status !== "authenticated" || !user || typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("workspace") !== "1" || params.get("username") !== user.github_login) return;
    const target = user.github_login;
    window.history.replaceState({}, "", "/");
    void submitUsername(target);
  }, [status, user]);

  async function submitUsername(normalizedUsername: string) {
    const generation = requestGeneration.current + 1;
    const requestAuthContext = authContextRef.current;
    requestGeneration.current = generation;
    targetRef.current = normalizedUsername;
    setValidationMessage(null);
    setState({ status: "loading", username: normalizedUsername });
    try {
      const result = await analyzePortfolioWithInterpretation(normalizedUsername);
      if (generation !== requestGeneration.current || requestAuthContext !== authContextRef.current || targetRef.current !== normalizedUsername) return;
      setState({ status: "success", result });
    } catch (error) {
      if (generation !== requestGeneration.current || requestAuthContext !== authContextRef.current || targetRef.current !== normalizedUsername) return;
      const apiError = error instanceof ApiError
        ? error
        : new ApiError("Analiz tamamlanamadı.", 0, "unexpected_client_error");
      setState({ status: "error", error: apiError, username: normalizedUsername });
    }
  }

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
      setState({ status: "idle" });
      usernameInputRef.current?.focus();
    } else {
      void submitUsername(normalizedUsername);
    }
  }

  function handleRetry() {
    if (state.status === "error") void submitUsername(state.username);
  }

  const isLoading = state.status === "loading";
  const hasValidationError = validationMessage !== null;

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} noValidate aria-busy={isLoading} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
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
            className="min-h-12 min-w-0 flex-1 rounded-xl border border-slate-300 px-4 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-slate-950 focus:ring-2 focus:ring-slate-950/20 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-600"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="min-h-12 shrink-0 rounded-xl bg-slate-950 px-5 font-medium text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-400 disabled:text-slate-100"
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
        {state.status === "error" && <AnalysisErrorState error={state.error} onRetry={handleRetry} />}
      </form>
      {state.status === "success" && <AnalysisResultShell result={state.result} onReanalyze={() => void submitUsername(targetRef.current || state.result.analysis.user.username)} />}
    </div>
  );
}

type AnalysisState =
  | { status: "idle" }
  | { status: "loading"; username: string }
  | { status: "success"; result: GitHubPortfolioInterpretationResponse }
  | { status: "error"; error: ApiError; username: string };
