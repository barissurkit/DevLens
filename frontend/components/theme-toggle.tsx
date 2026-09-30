"use client";

import { useSyncExternalStore } from "react";
import { THEME_STORAGE_KEY, type Theme } from "../lib/theme";

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

const OPTIONS: Array<{ value: Theme; label: string; icon: React.ReactNode }> = [
  {
    value: "system",
    label: "Sistem teması",
    icon: <path d="M4 5h16v11H4zM9 20h6M12 16v4" />,
  },
  {
    value: "light",
    label: "Açık tema",
    icon: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  },
  {
    value: "dark",
    label: "Koyu tema",
    icon: <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />,
  },
];

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, readTheme, () => "system" as Theme);

  return (
    <div role="group" aria-label="Tema" className="inline-flex rounded-lg border border-slate-300 bg-card p-0.5">
      {OPTIONS.map((option) => {
        const pressed = theme === option.value;
        return (
          <button
            key={option.value}
            type="button"
            aria-label={option.label}
            aria-pressed={pressed}
            title={option.label}
            onClick={() => selectTheme(option.value)}
            className={`flex h-9 w-9 items-center justify-center rounded-md transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${pressed ? "bg-indigo-600 text-white" : "text-slate-500 hover:bg-slate-100 hover:text-slate-950"}`}
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{option.icon}</svg>
          </button>
        );
      })}
    </div>
  );
}
