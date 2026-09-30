"use client";

import { type KeyboardEvent, useRef } from "react";

export interface ResultTab {
  id: string;
  label: string;
  badge?: number;
}

interface ResultTabsProps {
  tabs: ResultTab[];
  activeId: string;
  onChange: (id: string) => void;
  idPrefix: string;
}

export function tabElementId(prefix: string, id: string) {
  return `${prefix}-tab-${id}`;
}

export function panelElementId(prefix: string, id: string) {
  return `${prefix}-panel-${id}`;
}

export function ResultTabs({ tabs, activeId, onChange, idPrefix }: ResultTabsProps) {
  const buttonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  function focusTab(index: number) {
    const next = tabs[(index + tabs.length) % tabs.length];
    onChange(next.id);
    buttonRefs.current[next.id]?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key === "ArrowRight") focusTab(index + 1);
    else if (event.key === "ArrowLeft") focusTab(index - 1);
    else if (event.key === "Home") focusTab(0);
    else if (event.key === "End") focusTab(tabs.length - 1);
    else return;
    event.preventDefault();
  }

  return (
    <div className="sticky top-0 z-10 -mx-4 border-b border-slate-200 bg-slate-50/90 px-4 backdrop-blur sm:-mx-0 sm:rounded-t-xl sm:px-0">
      <div role="tablist" aria-label="Analiz sonucu bölümleri" className="flex gap-1 overflow-x-auto overflow-y-hidden [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {tabs.map((tab, index) => {
          const selected = tab.id === activeId;
          return (
            <button
              key={tab.id}
              ref={(node) => { buttonRefs.current[tab.id] = node; }}
              type="button"
              role="tab"
              id={tabElementId(idPrefix, tab.id)}
              aria-selected={selected}
              aria-controls={panelElementId(idPrefix, tab.id)}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(event) => handleKeyDown(event, index)}
              className={`relative inline-flex min-h-12 shrink-0 items-center gap-2 px-4 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-600 ${selected ? "text-indigo-700" : "text-slate-600 hover:text-slate-950"}`}
            >
              {tab.label}
              {tab.badge !== undefined && (
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${selected ? "bg-indigo-50 text-indigo-700" : "bg-slate-200/70 text-slate-600"}`}>{tab.badge}</span>
              )}
              <span aria-hidden="true" className={`absolute inset-x-3 bottom-0 h-0.5 rounded-full transition ${selected ? "bg-indigo-600" : "bg-transparent"}`} />
            </button>
          );
        })}
      </div>
    </div>
  );
}
