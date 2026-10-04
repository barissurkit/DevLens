export type ClientErrorKind = "render" | "script" | "promise";

const MAX_REPORTS_PER_PAGE = 5;
let sent = 0;

/**
 * Sends an unexpected browser error to the API log. Best effort: it never throws, reports at most a few
 * per page view and is a no-op when the API address is not configured.
 */
export function reportClientError(kind: ClientErrorKind, error: unknown): void {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!baseUrl || typeof window === "undefined" || sent >= MAX_REPORTS_PER_PAGE) return;
  sent += 1;
  const source = error instanceof Error ? error : new Error(typeof error === "string" ? error : "Bilinmeyen hata");
  try {
    void fetch(`${baseUrl.replace(/\/+$/, "")}/api/v1/client-errors`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        kind,
        message: (source.message || source.name).slice(0, 500),
        stack: source.stack?.slice(0, 2000),
        path: window.location.pathname.slice(0, 200),
      }),
      keepalive: true,
    }).catch(() => undefined);
  } catch {
    // Reporting must never cause another error.
  }
}

/** Test helper: lets each test start with a fresh per-page budget. */
export function resetClientErrorBudget(): void {
  sent = 0;
}
