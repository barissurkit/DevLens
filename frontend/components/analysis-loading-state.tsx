"use client";

import { useEffect, useState } from "react";

const LONG_REQUEST_THRESHOLD_MS = 8_000;

const TYPICAL_STEPS = [
  "GitHub profili ve repository listesi alınır",
  "Her repository için deterministik kanıtlar hesaplanır",
  "Portföy skoru ve AI yorumu hazırlanır",
];

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
      className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600"
    >
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-slate-300 border-t-slate-950 motion-reduce:animate-none"
        />
        <span>
          <strong className="font-medium text-slate-900">GitHub portföyü analiz ediliyor...</strong>{" "}
          Bu işlem repository sayısına göre birkaç saniye sürebilir.
        </span>
      </div>
      <ol className="mt-3 list-decimal space-y-1 pl-9 text-slate-500">
        {TYPICAL_STEPS.map((step) => <li key={step}>{step}</li>)}
      </ol>
      {isLongRunning && (
        <p className="mt-3 border-t border-slate-200 pt-3 text-slate-600">
          Analiz beklenenden uzun sürüyor. Ücretsiz sunucu uyanıyor olabilir; işlem devam ediyor, sayfayı açık tutabilirsiniz.
        </p>
      )}
    </div>
  );
}
