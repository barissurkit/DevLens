import { useEffect, useRef } from "react";
import type { ApiError } from "../lib/api";

interface ErrorPresentation {
  title: string;
  message: string;
  canRetry: boolean;
}

interface AnalysisErrorStateProps {
  error: ApiError;
  onRetry: () => void;
}

/** Turns the server's Retry-After hint into a short, human wait suggestion. */
export function rateLimitMessage(retryAfterSeconds: number | undefined): string {
  if (!retryAfterSeconds) return "Kısa bir süre bekleyip tekrar deneyin.";
  if (retryAfterSeconds < 60) return `Yaklaşık ${retryAfterSeconds} saniye bekleyip tekrar deneyebilirsiniz.`;
  return `Yaklaşık ${Math.ceil(retryAfterSeconds / 60)} dakika bekleyip tekrar deneyebilirsiniz.`;
}

function getErrorPresentation(error: ApiError): ErrorPresentation {
  switch (error.code) {
    case "rate_limited":
      return { title: "Çok fazla istek gönderildi", message: rateLimitMessage(error.retryAfterSeconds), canRetry: true };
    case "github_user_not_found":
      return { title: "GitHub kullanıcısı bulunamadı", message: "Kullanıcı adını kontrol edip tekrar deneyin.", canRetry: false };
    case "github_rate_limit":
      return { title: "GitHub istek sınırına ulaşıldı", message: "Bir süre sonra tekrar deneyin.", canRetry: false };
    case "github_timeout":
    case "github_unavailable":
    case "network_error":
      return { title: "Analiz servisine şu anda ulaşılamıyor", message: "Bağlantınızı kontrol edip tekrar deneyebilirsiniz.", canRetry: true };
    case "github_upstream_error":
      return { title: "GitHub verileri şu anda alınamadı", message: "Bir süre sonra tekrar deneyin.", canRetry: true };
    case "validation_error":
      return { title: "Kullanıcı adı geçerli değil", message: "GitHub kullanıcı adını kontrol edip tekrar deneyin.", canRetry: false };
    default:
      return { title: "Analiz tamamlanamadı", message: "Beklenmeyen bir sorun oluştu. Bir süre sonra tekrar deneyin.", canRetry: false };
  }
}

export function AnalysisErrorState({ error, onRetry }: AnalysisErrorStateProps) {
  const presentation = getErrorPresentation(error);
  const errorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    errorRef.current?.focus();
  }, []);

  return (
    <div ref={errorRef} tabIndex={-1} role="alert" aria-live="assertive" aria-atomic="true" className="mt-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-4 text-sm text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-800 focus:ring-offset-2">
      <p className="font-semibold">{presentation.title}</p>
      <p className="mt-1 text-amber-900">{presentation.message}</p>
      {presentation.canRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 min-h-11 rounded-lg border border-amber-300 bg-card px-3 py-2 font-medium text-amber-950 transition hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-800 focus:ring-offset-2"
        >
          Tekrar dene
        </button>
      )}
    </div>
  );
}
