import type {
  GitHubPortfolioInterpretationResponse,
  GitHubPortfolioAnalysis,
  InterpretationUnavailableReason,
  OperationalErrorResponse,
  PortfolioAnalysisRequest,
} from "./types";

const ANALYSIS_PATH = "/api/v1/analysis";
const INTERPRETATION_PATH = "/api/v1/interpretation";
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

function getApiUrl(path: string): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (!baseUrl) {
    throw new ApiError("Analiz servisi yapılandırılmamış.", 0, "api_configuration_error");
  }

  return `${baseUrl.replace(/\/+$/, "")}${path}`;
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

function isInterpretationUnavailableReason(value: unknown): value is InterpretationUnavailableReason {
  return typeof value === "string" && [
    "not_configured",
    "insufficient_evidence",
    "timeout",
    "unavailable",
    "rate_limit",
    "upstream_error",
    "invalid_response",
  ].includes(value);
}

function isGitHubPortfolioInterpretationResponse(value: unknown): value is GitHubPortfolioInterpretationResponse {
  if (typeof value !== "object" || value === null || !("analysis" in value) || !("interpretation" in value)) return false;
  if (!isGitHubPortfolioAnalysis(value.analysis)) return false;
  const interpretation = value.interpretation;
  if (typeof interpretation !== "object" || interpretation === null || !("status" in interpretation)) return false;
  if (interpretation.status === "unavailable") return "reason" in interpretation && isInterpretationUnavailableReason(interpretation.reason);
  if (interpretation.status !== "available" || !("interpretation" in interpretation)) return false;
  const content = interpretation.interpretation;
  if (typeof content !== "object" || content === null) return false;
  return (
    "summary" in content && typeof content.summary === "string" &&
    "strength_explanations" in content && Array.isArray(content.strength_explanations) &&
    "improvement_explanations" in content && Array.isArray(content.improvement_explanations) &&
    "technology_context" in content && (typeof content.technology_context === "string" || content.technology_context === null) &&
    "project_area_context" in content && (typeof content.project_area_context === "string" || content.project_area_context === null) &&
    "limitations_note" in content && (typeof content.limitations_note === "string" || content.limitations_note === null) &&
    [...content.strength_explanations, ...content.improvement_explanations].every((item) => (
      typeof item === "object" && item !== null && "signal_key" in item && typeof item.signal_key === "string" && "explanation" in item && typeof item.explanation === "string"
    ))
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

export async function analyzePortfolioWithInterpretation(
  username: string,
): Promise<GitHubPortfolioInterpretationResponse> {
  const request: PortfolioAnalysisRequest = { username };
  let response: Response;

  try {
    response = await fetch(getApiUrl(INTERPRETATION_PATH), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw new ApiError("Analiz servisine ulaşılamadı.", 0, "network_error");
  }

  const payload = await readJson(response);
  if (response.ok) {
    if (isGitHubPortfolioInterpretationResponse(payload)) return payload;
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
