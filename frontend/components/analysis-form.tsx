"use client";

import { FormEvent, useState } from "react";
import { analyzePortfolio, ApiError } from "../lib/api";
import type { GitHubPortfolioAnalysis } from "../lib/types";
import { AnalysisResultShell } from "./analysis-result-shell";

const MAX_USERNAME_LENGTH = 39;

export function AnalysisForm() {
  const [username, setUsername] = useState("");
  const [result, setResult] = useState<GitHubPortfolioAnalysis | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedUsername = username.trim();
    setErrorMessage(null);
    setResult(null);

    if (!normalizedUsername) {
      setErrorMessage("Bir GitHub kullanıcı adı girin.");
      return;
    }
    if (normalizedUsername.length > MAX_USERNAME_LENGTH) {
      setErrorMessage("GitHub kullanıcı adı 39 karakterden uzun olamaz.");
      return;
    }

    setIsLoading(true);
    try {
      setResult(await analyzePortfolio(normalizedUsername));
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Analiz tamamlanamadı.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} noValidate className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <label htmlFor="github-username" className="block text-sm font-medium text-slate-900">GitHub kullanıcı adı</label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row">
          <input
            id="github-username"
            name="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="ör. barissurkit"
            maxLength={MAX_USERNAME_LENGTH}
            autoComplete="username"
            aria-describedby={errorMessage ? "analysis-error" : "username-hint"}
            className="min-h-12 flex-1 rounded-xl border border-slate-300 px-4 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-slate-950 focus:ring-2 focus:ring-slate-950/10"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="min-h-12 rounded-xl bg-slate-950 px-5 font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {isLoading ? "Analiz ediliyor..." : "Analiz et"}
          </button>
        </div>
        <p id="username-hint" className="mt-3 text-sm text-slate-500">Public repository kanıtlarını incelemek için kullanıcı adını girin.</p>
        {errorMessage && (
          <p id="analysis-error" role="alert" aria-live="polite" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {errorMessage}
          </p>
        )}
        {isLoading && <p role="status" aria-live="polite" className="sr-only">Analiz ediliyor...</p>}
      </form>
      {result && <AnalysisResultShell result={result} />}
    </div>
  );
}
