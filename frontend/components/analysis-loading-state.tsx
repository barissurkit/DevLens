"use client";

import { useEffect, useState } from "react";

const LONG_REQUEST_THRESHOLD_MS = 8_000;

export function AnalysisLoadingState() {
  const [isLongRunning, setIsLongRunning] = useState(false);

  useEffect(() => {
    const timeout = window.setTimeout(() => setIsLongRunning(true), LONG_REQUEST_THRESHOLD_MS);

    return () => window.clearTimeout(timeout);
  }, []);

  return (
    <div
      role="status"
      aria-live="polite"
      className="mt-4 flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600"
    >
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-950 motion-reduce:animate-none"
      />
      <span>
        <strong className="font-medium text-slate-900">GitHub portföyü analiz ediliyor...</strong>{" "}
        Bu işlem repository sayısına göre birkaç saniye sürebilir.
        {isLongRunning && (
          <span className="mt-1 block text-slate-600">
            Analiz beklenenden uzun sürüyor. İşlem devam ediyor; bu sırada sayfayı açık tutabilirsiniz.
          </span>
        )}
      </span>
    </div>
  );
}
