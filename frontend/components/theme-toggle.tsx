"use client";

import { useCallback, useId, useRef, useState, useSyncExternalStore } from "react";
import { THEME_STORAGE_KEY, type Theme } from "../lib/theme";
import { useDismiss } from "./use-dismiss";

const listeners = new Set<() => void>();

function readTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

function applyTheme(theme: Theme) {
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
}

function persistTheme(theme: Theme) {
  try {
    if (theme === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
    else window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Storage can be unavailable (private mode, blocked site data); the choice then lasts for this page only.
  }
}

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

function selectTheme(theme: Theme) {
  persistTheme(theme);
  applyTheme(theme);
  listeners.forEach((listener) => listener());
}

const OPTIONS: Array<{ value: Theme; label: string; short: string; icon: React.ReactNode }> = [
  {
    value: "system",
    label: "Sistem teması",
    short: "Sistem",
    icon: <path d="M4 5h16v11H4zM9 20h6M12 16v4" />,
  },
  {
    value: "light",
    label: "Açık tema",
    short: "Açık",
    icon: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  },
  {
    value: "dark",
    label: "Koyu tema",
    short: "Koyu",
    icon: <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />,
  },
];

function Icon({ children }: { children: React.ReactNode }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{children}</svg>;
}

/**
 * One button that shows the current theme; it opens a small list with the three choices below it (above it
 * when `placement` is "up", for the footer).
 */
export function ThemeToggle({ placement = "down" }: { placement?: "down" | "up" }) {
  const theme = useSyncExternalStore(subscribe, readTheme, () => "system" as Theme);
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const close = useCallback(() => setOpen(false), []);
  useDismiss(open, close, listRef, buttonRef);
  const current = OPTIONS.find((option) => option.value === theme) ?? OPTIONS[0];

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-label={`Tema: ${current.short}`}
        aria-expanded={open}
        aria-controls={listId}
        title="Tema"
        onClick={() => setOpen((value) => !value)}
        className="flex h-9 items-center gap-1.5 rounded-lg border border-slate-300 bg-card px-2.5 text-slate-600 transition hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
      >
        <Icon>{current.icon}</Icon>
        <svg aria-hidden="true" viewBox="0 0 24 24" className={`h-3.5 w-3.5 transition ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <div
          ref={listRef}
          id={listId}
          role="group"
          aria-label="Tema"
          className={`absolute left-0 z-40 w-40 rounded-xl border border-slate-200 bg-card p-1 shadow-raised sm:left-auto sm:right-0 ${placement === "up" ? "bottom-full mb-2" : "top-full mt-2"}`}
        >
          {OPTIONS.map((option) => {
            const pressed = theme === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-label={option.label}
                aria-pressed={pressed}
                onClick={() => {
                  selectTheme(option.value);
                  close();
                  buttonRef.current?.focus();
                }}
                className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${pressed ? "bg-indigo-50 text-indigo-800" : "text-slate-700 hover:bg-slate-100"}`}
              >
                <Icon>{option.icon}</Icon>
                <span className="flex-1 text-left">{option.short}</span>
                {pressed && <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 8.5l3.2 3L13 4.5" /></svg>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
