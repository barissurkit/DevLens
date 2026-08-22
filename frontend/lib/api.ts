import type {
  GitHubPortfolioAnalysis,
  OperationalErrorResponse,
  PortfolioAnalysisRequest,
} from "./types";

const ANALYSIS_PATH = "/api/v1/analysis";
const DEFAULT_ERROR_MESSAGE = "Analiz sırasında beklenmeyen bir hata oluştu.";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function getAnalysisUrl(): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (!baseUrl) {
    throw new ApiError("Analiz servisi yapılandırılmamış.", 0, "api_configuration_error");
  }

  return `${baseUrl.replace(/\/+$/, "")}${ANALYSIS_PATH}`;
}

function isOperationalErrorResponse(value: unknown): value is OperationalErrorResponse {
  if (typeof value !== "object" || value === null || !("detail" in value)) return false;
  const detail = value.detail;
  return (
    typeof detail === "object" &&
    detail !== null &&
    "code" in detail &&
    "message" in detail &&
    typeof detail.code === "string" &&
    typeof detail.message === "string"
  );
}

function isGitHubPortfolioAnalysis(value: unknown): value is GitHubPortfolioAnalysis {
  if (typeof value !== "object" || value === null) return false;
  return ["user", "selection", "repository_analysis", "aggregation", "intelligence", "score"].every(
    (key) => key in value,
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function analyzePortfolio(
  username: string,
): Promise<GitHubPortfolioAnalysis> {
  const request: PortfolioAnalysisRequest = { username };
  let response: Response;

  try {
    response = await fetch(getAnalysisUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw new ApiError("Analiz servisine ulaşılamadı.", 0, "network_error");
  }

  const payload = await readJson(response);
  if (response.ok) {
    if (isGitHubPortfolioAnalysis(payload)) return payload;
    throw new ApiError("Analiz servisi geçersiz bir yanıt döndürdü.", response.status, "malformed_response");
  }

  if (isOperationalErrorResponse(payload)) {
    throw new ApiError(payload.detail.message, response.status, payload.detail.code);
  }

  if (response.status === 422) {
    throw new ApiError("Kullanıcı adı geçerli değil.", response.status, "validation_error");
  }

  throw new ApiError(DEFAULT_ERROR_MESSAGE, response.status, "unexpected_api_error");
}
