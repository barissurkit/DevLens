"use client";

import { useEffect, useState } from "react";

const MESSAGES: Record<string, string> = {
  authentication_failed: "GitHub ile giriş tamamlanamadı. Giriş iptal edilmiş veya süresi dolmuş olabilir; lütfen tekrar deneyin.",
};
const FALLBACK_MESSAGE = "Giriş sırasında bir sorun oluştu. Lütfen tekrar deneyin.";

/** Explains a failed sign-in: the backend sends the user back with `?auth_error=...` and nothing else. */
export function AuthNotice() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const url = new URL(window.location.href);
    const code = url.searchParams.get("auth_error");
    if (!code) return;
    // Keep the address clean so a reload or a copied link does not show the notice again.
    url.searchParams.delete("auth_error");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
    setMessage(MESSAGES[code] ?? FALLBACK_MESSAGE);
  }, []);

  if (!message) return null;
  return (
    <div role="alert" className="border-b border-amber-300 bg-amber-50 text-amber-950">
      <div className="mx-auto flex w-full max-w-6xl items-start justify-between gap-4 px-4 py-3 text-sm sm:px-6 lg:px-8">
        <p>{message}</p>
        <button
          type="button"
          onClick={() => setMessage(null)}
          className="shrink-0 rounded-lg px-2 py-1 font-medium underline focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-800"
        >
          Kapat
        </button>
      </div>
    </div>
  );
}
