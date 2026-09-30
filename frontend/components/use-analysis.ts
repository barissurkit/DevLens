"use client";

import { startTransition, useEffect, useRef, useState } from "react";
import { analyzePortfolioWithInterpretation, ApiError } from "../lib/api";
import type { AnalysisProgress, GitHubPortfolioInterpretationResponse } from "../lib/types";
import { useAuth } from "./auth-provider";

export type AnalysisState =
  | { status: "idle" }
  | { status: "loading"; username: string; progress: AnalysisProgress | null }
  | { status: "success"; result: GitHubPortfolioInterpretationResponse }
  | { status: "error"; error: ApiError; username: string };

export interface SubmitOptions {
  /** Bypass the server-side snapshot cache and recompute the analysis. */
  refresh?: boolean;
  /** Retry only the AI interpretation, bypassing the server's cooldown after a failed attempt. */
  retryInterpretation?: boolean;
}

/**
 * Owns the analysis request lifecycle: it ignores stale responses (superseded requests or
 * auth context changes), aborts superseded requests, reports streamed progress and resumes a
 * pending workspace analysis after sign-in.
 */
export function useAnalysis(clearValidation: () => void) {
  const { status, user } = useAuth();
  const [state, setState] = useState<AnalysisState>({ status: "idle" });
  const requestGeneration = useRef(0);
  const targetRef = useRef<string | null>(null);
  const authContextRef = useRef("");
  const abortRef = useRef<AbortController | null>(null);
  const authContextKey = `${status}:${user?.github_login ?? "anonymous"}`;
  const clearValidationRef = useRef(clearValidation);
  const submitRef = useRef<(username: string, options?: SubmitOptions) => Promise<void>>(async () => undefined);

  // Keep the latest values readable from async callbacks and the effects below.
  useEffect(() => {
    authContextRef.current = authContextKey;
    clearValidationRef.current = clearValidation;
    submitRef.current = submit;
  });

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    requestGeneration.current += 1;
    abortRef.current?.abort();
    if (status !== "authenticated") {
      targetRef.current = null;
      startTransition(() => { setState({ status: "idle" }); clearValidationRef.current(); });
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
    void submitRef.current(target);
  }, [status, user]);

  async function submit(normalizedUsername: string, options: SubmitOptions = {}) {
    const generation = requestGeneration.current + 1;
    const requestAuthContext = authContextRef.current;
    requestGeneration.current = generation;
    targetRef.current = normalizedUsername;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    clearValidationRef.current();
    setState({ status: "loading", username: normalizedUsername, progress: null });
    const isStale = () =>
      generation !== requestGeneration.current
      || requestAuthContext !== authContextRef.current
      || targetRef.current !== normalizedUsername;
    try {
      const result = await analyzePortfolioWithInterpretation(normalizedUsername, {
        refresh: options.refresh,
        retryInterpretation: options.retryInterpretation,
        signal: controller.signal,
        onProgress: (progress) => {
          if (isStale()) return;
          setState((current) => current.status === "loading" ? { ...current, progress } : current);
        },
      });
      if (isStale()) return;
      setState({ status: "success", result });
    } catch (error) {
      if (isStale()) return;
      const apiError = error instanceof ApiError
        ? error
        : new ApiError("Analiz tamamlanamadı.", 0, "unexpected_client_error");
      setState({ status: "error", error: apiError, username: normalizedUsername });
    }
  }

  function retry() {
    if (state.status === "error") void submit(state.username);
  }

  /** Recompute the analysis (skipping the cache); used by "Yenile" and after applying improvements. */
  function reanalyze() {
    if (state.status !== "success") return;
    void submit(targetRef.current || state.result.analysis.user.username, { refresh: true });
  }

  /** Ask again without bypassing the cache: the analysis is reused and only the AI interpretation is retried (now, not after the cooldown). */
  function retryInterpretation() {
    if (state.status !== "success") return;
    void submit(targetRef.current || state.result.analysis.user.username, { retryInterpretation: true });
  }

  function resetToIdle() {
    setState({ status: "idle" });
  }

  return { state, submit, retry, reanalyze, retryInterpretation, resetToIdle };
}
