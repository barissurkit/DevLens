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

function getErrorPresentation(error: ApiError): ErrorPresentation {
  switch (error.code) {
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

  return (
    <div role="alert" aria-live="assertive" className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-950">
      <p className="font-semibold">{presentation.title}</p>
      <p className="mt-1 text-amber-900">{presentation.message}</p>
      {presentation.canRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg border border-amber-300 bg-white px-3 py-2 font-medium text-amber-950 transition hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-amber-700/30"
        >
          Tekrar dene
        </button>
      )}
    </div>
  );
}
