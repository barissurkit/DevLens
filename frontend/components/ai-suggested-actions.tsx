"use client";

import { useState } from "react";
import { ApiError, createActionPlanTask, generateAISuggestions } from "../lib/api";
import type { AISuggestion, ActionPlanTask } from "../lib/types";

interface Props {
  username: string;
}

export function AISuggestedActions({ username }: Props) {
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [state, setState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [adding, setAdding] = useState<number | null>(null);

  async function generate() {
    setState("loading"); setError(null);
    try {
      const result = await generateAISuggestions(username);
      if (result.status === "available") { setSuggestions(result.suggestions); setState("success"); }
      else { setSuggestions([]); setState(result.reason === "insufficient_evidence" ? "success" : "error"); setError(result.reason === "insufficient_evidence" ? null : "AI önerileri şu anda kullanılamıyor."); }
    } catch (cause) {
      setState("error"); setError(cause instanceof ApiError ? cause.message : "AI önerileri oluşturulamadı.");
    }
  }

  async function addSuggestion(index: number) {
    const suggestion = suggestions[index];
    if (!suggestion || adding !== null) return;
    setAdding(index); setError(null);
    try {
      const task = await createActionPlanTask({ title: suggestion.title, description: suggestion.description });
      window.dispatchEvent(new CustomEvent<ActionPlanTask>("devlens:suggested-task-added", { detail: task }));
      setSuggestions((items) => items.filter((_, itemIndex) => itemIndex !== index));
    } catch { setError("Öneri Action Plan'a eklenemedi."); }
    finally { setAdding(null); }
  }

  function updateSuggestion(index: number, changes: Partial<AISuggestion>) {
    setSuggestions((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, ...changes } : item));
  }

  return <section aria-labelledby="ai-suggestions-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div><h3 id="ai-suggestions-heading" className="text-xl font-semibold tracking-tight text-slate-950">AI Suggested Actions</h3><p className="mt-2 text-sm text-slate-600">Yalnızca bu analizdeki deterministik kanıtlara dayalı, gözden geçirilebilir öneriler.</p></div>
      <button type="button" onClick={() => void generate()} disabled={state === "loading"} className="min-h-10 rounded-xl bg-slate-950 px-4 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400">{state === "loading" ? "Öneriler oluşturuluyor..." : state === "success" ? "Yeniden oluştur" : "Generate suggestions"}</button>
    </div>
    {state === "loading" && <p className="mt-5 text-sm text-slate-500" role="status">Deterministik kanıtlar yorumlanıyor...</p>}
    {error && <div className="mt-5 flex flex-wrap items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert"><span>{error}</span><button type="button" onClick={() => void generate()} className="font-medium underline">Tekrar dene</button></div>}
    {state === "success" && suggestions.length === 0 && <p className="mt-5 text-sm text-slate-500">Bu analiz için temellendirilebilir öneri bulunamadı.</p>}
    <div className="mt-5 space-y-3">{suggestions.map((suggestion, index) => <article key={`${suggestion.title}-${index}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1">{editing === index ? <><label className="sr-only" htmlFor={`suggestion-title-${index}`}>Öneri başlığı</label><input id={`suggestion-title-${index}`} value={suggestion.title} onChange={(event) => updateSuggestion(index, { title: event.target.value })} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-medium text-slate-950" /><label className="sr-only" htmlFor={`suggestion-description-${index}`}>Öneri açıklaması</label><textarea id={`suggestion-description-${index}`} value={suggestion.description} onChange={(event) => updateSuggestion(index, { description: event.target.value })} className="mt-2 min-h-20 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700" /></> : <><h4 className="font-medium text-slate-950">{suggestion.title}</h4><p className="mt-2 text-sm leading-6 text-slate-700">{suggestion.description}</p></>}</div></div><p className="mt-3 text-sm text-slate-600"><span className="font-medium text-slate-800">Neden:</span> {suggestion.reason}</p><p className="mt-2 text-xs text-slate-500">Temel kanıt: {suggestion.evidence_refs.join(", ")}</p><div className="mt-4 flex flex-wrap gap-2"><button type="button" disabled={adding !== null} onClick={() => setEditing(editing === index ? null : index)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700">{editing === index ? "Düzenlemeyi bitir" : "Edit"}</button><button type="button" disabled={adding !== null || !suggestion.title.trim() || !suggestion.description.trim()} onClick={() => void addSuggestion(index)} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400">{adding === index ? "Ekleniyor..." : "Add"}</button><button type="button" disabled={adding !== null} onClick={() => setSuggestions((items) => items.filter((_, itemIndex) => itemIndex !== index))} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700">Dismiss</button></div></article>)}</div>
  </section>;
}
