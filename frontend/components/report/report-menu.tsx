"use client";

import { useEffect, useId, useRef, useState } from "react";
import { REPORT_MODES } from "../../lib/report";
import { userPath } from "../../lib/share";

export function reportPath(username: string, mode: string): string {
  return `${userPath(username)}/rapor?tur=${mode}`;
}

/**
 * The "Yazdır / PDF" button of the result header. It opens a bar with the two reports (summary, detailed); each
 * is a link to the report page, which prints or saves as PDF from there. The bar opens inline, in the header
 * card, so nothing is clipped by the card's rounded edges. The bar has `w-0 min-w-full`: it fills the row it sits
 * in but adds nothing to the row's natural width. With a width of its own it would widen the whole action column
 * and squeeze the profile name beside it down to nothing.
 */
export function ReportMenu({ username }: { username: string }) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const barRef = useRef<HTMLDivElement>(null);
  const barId = useId();

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (barRef.current?.contains(target) || buttonRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={barId}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex min-h-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 9V4h10v5M7 17H5a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2h-2M7 14h10v6H7z" /></svg>
        Yazdır / PDF
        <svg aria-hidden="true" viewBox="0 0 24 24" className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <div ref={barRef} id={barId} role="group" aria-label="Rapor türü" className="order-last !flex-none basis-full w-0 min-w-full rounded-xl border border-indigo-200 bg-indigo-50/60 p-2">
          <p className="px-2 pb-1.5 pt-1 text-xs font-medium text-slate-600">Hangi raporu oluşturalım? Rapor sayfasında yazdırabilir veya PDF olarak kaydedebilirsiniz.</p>
          <ul className="grid gap-2 sm:grid-cols-2">
            {REPORT_MODES.map((item) => (
              <li key={item.mode}>
                <a
                  href={reportPath(username, item.mode)}
                  className="block h-full rounded-lg border border-slate-200 bg-card px-3 py-2.5 transition hover:border-indigo-400 hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
                >
                  <span className="block text-sm font-semibold text-slate-950">{item.label}</span>
                  <span className="mt-0.5 block text-xs leading-snug text-slate-600">{item.description}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
