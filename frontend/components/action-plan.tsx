"use client";

import { startTransition, useEffect, useState } from "react";
import { ApiError, createActionPlanTask, deleteActionPlanTask, getActionPlan, updateActionPlanTask } from "../lib/api";
import type { ActionPlanStatus, ActionPlanTask, AuthenticatedUser } from "../lib/types";
import { useAuth } from "./auth-provider";

export function ActionPlan() {
  const { status, user } = useAuth();
  const [tasks, setTasks] = useState<ActionPlanTask[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadedFor, setLoadedFor] = useState<AuthenticatedUser | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    startTransition(() => { setLoading(true); setTasks([]); setError(null); setLoadedFor(null); });
    void getActionPlan().then((result) => { setTasks(result.tasks); setLoadedFor(user); }).catch((reason) => setError(reason instanceof ApiError ? reason.message : "Action Plan yüklenemedi.")).finally(() => setLoading(false));
  }, [status, user]);

  if (status !== "authenticated") return null;

  async function createTask(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      const task = await createActionPlanTask({ title, description: description || undefined });
      setTasks((current) => [task, ...current]); setTitle(""); setDescription("");
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : "Görev oluşturulamadı."); }
    finally { setBusy(false); }
  }

  async function changeTask(task: ActionPlanTask, changes: { title?: string; description?: string | null; status?: ActionPlanStatus }) {
    setBusy(true); setError(null);
    try { const updated = await updateActionPlanTask(task.id, changes); setTasks((current) => current.map((item) => item.id === updated.id ? updated : item)); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "Görev güncellenemedi."); }
    finally { setBusy(false); }
  }

  async function removeTask(id: string) {
    setBusy(true); setError(null);
    try { await deleteActionPlanTask(id); setTasks((current) => current.filter((task) => task.id !== id)); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "Görev silinemedi."); }
    finally { setBusy(false); }
  }

  return <section aria-labelledby="action-plan-heading" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
    <h3 id="action-plan-heading" className="text-xl font-semibold tracking-tight text-slate-950">Action Plan</h3>
    <p className="mt-2 text-sm text-slate-500">Portföyünü geliştirmek için manuel görevlerini takip et.</p>
    <form onSubmit={createTask} className="mt-5 grid gap-3">
      <label htmlFor="action-plan-title" className="text-sm font-medium text-slate-900">Yeni görev</label>
      <input id="action-plan-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} placeholder="ör. README kullanım bölümünü geliştir" required className="min-h-11 rounded-xl border border-slate-300 px-3 outline-none focus:border-slate-950 focus:ring-2 focus:ring-slate-950/20" />
      <textarea aria-label="Görev açıklaması" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} placeholder="Açıklama (isteğe bağlı)" className="min-h-20 rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-slate-950 focus:ring-2 focus:ring-slate-950/20" />
      <button type="submit" disabled={busy || !title.trim()} className="min-h-11 w-fit rounded-xl bg-slate-950 px-4 font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400">Görev ekle</button>
    </form>
    {error && <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
    {loading || loadedFor !== user ? <p className="mt-6 text-sm text-slate-500">Görevler yükleniyor...</p> : tasks.length === 0 ? <p className="mt-6 text-sm text-slate-500">Henüz görev yok.</p> : <ul className="mt-6 space-y-3">{tasks.map((task) => <li key={task.id} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1"><input aria-label="Görev başlığı" value={task.title} disabled={busy} onChange={(event) => setTasks((current) => current.map((item) => item.id === task.id ? { ...item, title: event.target.value } : item))} onBlur={(event) => { if (event.target.value.trim() && event.target.value !== task.title) void changeTask(task, { title: event.target.value }); }} className="w-full border-0 p-0 font-medium text-slate-950 outline-none" /><textarea aria-label="Görev açıklaması" value={task.description || ""} disabled={busy} placeholder="Açıklama eklenmedi." onChange={(event) => setTasks((current) => current.map((item) => item.id === task.id ? { ...item, description: event.target.value } : item))} onBlur={(event) => { if (event.target.value !== (task.description || "")) void changeTask(task, { description: event.target.value || null }); }} className="mt-1 min-h-12 w-full resize-y border-0 p-0 text-sm text-slate-600 outline-none" /></div><select aria-label="Görev durumu" value={task.status} disabled={busy} onChange={(event) => void changeTask(task, { status: event.target.value as ActionPlanStatus })} className="rounded-lg border border-slate-300 px-2 py-1 text-sm"><option value="todo">Yapılacak</option><option value="in_progress">Devam ediyor</option><option value="done">Tamamlandı</option></select><button type="button" disabled={busy} onClick={() => void removeTask(task.id)} className="text-sm font-medium text-red-700 underline">Sil</button></div></li>)}</ul>}
  </section>;
}
