"use client";

import { startTransition, useEffect, useRef, useState } from "react";
import { analyzePortfolioWithInterpretation, ApiError } from "../lib/api";
import type { GitHubPortfolioInterpretationResponse } from "../lib/types";
import { useAuth } from "./auth-provider";

export type AnalysisState =
  | { status: "idle" }
  | { status: "loading"; username: string }
  | { status: "success"; result: GitHubPortfolioInterpretationResponse }
  | { status: "error"; error: ApiError; username: string };

/**
 * Owns the analysis request lifecycle: it ignores stale responses (superseded requests or
 * auth context changes) and resumes a pending workspace analysis after sign-in.
 */
export function useAnalysis(clearValidation: () => void) {
  const { status, user } = useAuth();
  const [state, setState] = useState<AnalysisState>({ status: "idle" });
  const requestGeneration = useRef(0);
  const targetRef = useRef<string | null>(null);
  const authContextRef = useRef("");
  const authContextKey = `${status}:${user?.github_login ?? "anonymous"}`;
  const clearValidationRef = useRef(clearValidation);
  const submitRef = useRef<(username: string) => Promise<void>>(async () => undefined);

  // Keep the latest values readable from async callbacks and the effects below.
  useEffect(() => {
    authContextRef.current = authContextKey;
    clearValidationRef.current = clearValidation;
    submitRef.current = submit;
  });

  useEffect(() => {
    requestGeneration.current += 1;
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

  async function submit(normalizedUsername: string) {
    const generation = requestGeneration.current + 1;
    const requestAuthContext = authContextRef.current;
    requestGeneration.current = generation;
    targetRef.current = normalizedUsername;
    clearValidationRef.current();
    setState({ status: "loading", username: normalizedUsername });
    const isStale = () =>
      generation !== requestGeneration.current
      || requestAuthContext !== authContextRef.current
      || targetRef.current !== normalizedUsername;
    try {
      const result = await analyzePortfolioWithInterpretation(normalizedUsername);
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

  function reanalyze() {
    if (state.status !== "success") return;
    void submit(targetRef.current || state.result.analysis.user.username);
  }

  function resetToIdle() {
    setState({ status: "idle" });
  }

  return { state, submit, retry, reanalyze, resetToIdle };
}
