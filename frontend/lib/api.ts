import type {
  GitHubPortfolioInterpretationResponse,
  GitHubPortfolioAnalysis,
  InterpretationUnavailableReason,
  OperationalErrorResponse,
  PortfolioAnalysisRequest,
  AuthMeResponse,
} from "./types";

const ANALYSIS_PATH = "/api/v1/analysis";
const INTERPRETATION_PATH = "/api/v1/interpretation";
const AUTH_START_PATH = "/api/v1/auth/github";
const AUTH_ME_PATH = "/api/v1/auth/me";
const AUTH_LOGOUT_PATH = "/api/v1/auth/logout";
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

function isAuthMeResponse(value: unknown): value is AuthMeResponse {
  if (typeof value !== "object" || value === null || !("authenticated" in value) || !("user" in value)) {
    return false;
  }

  if (typeof value.authenticated !== "boolean") return false;
  if (value.user === null) return !value.authenticated;
  if (typeof value.user !== "object" || value.user === null) return false;

  const user = value.user as Record<string, unknown>;
  return (
    value.authenticated &&
    typeof user.github_login === "string" &&
    (typeof user.display_name === "string" || user.display_name === null) &&
    (typeof user.avatar_url === "string" || user.avatar_url === null) &&
    (typeof user.github_html_url === "string" || user.github_html_url === null)
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
  const contentRecord = content as Record<string, unknown>;
  const recommendation = contentRecord.next_project_recommendation;
  const hasValidRecommendation = recommendation === null || (
    typeof recommendation === "object" && recommendation !== null &&
    ["title", "goal", "rationale", "focus_signal_keys", "suggested_deliverables"].every((key) => key in recommendation) &&
    typeof (recommendation as Record<string, unknown>).title === "string" &&
    typeof (recommendation as Record<string, unknown>).goal === "string" &&
    typeof (recommendation as Record<string, unknown>).rationale === "string" &&
    Array.isArray((recommendation as Record<string, unknown>).focus_signal_keys) &&
    Array.isArray((recommendation as Record<string, unknown>).suggested_deliverables) &&
    ((recommendation as Record<string, unknown>).focus_signal_keys as unknown[]).every((key: unknown) => typeof key === "string") &&
    ((recommendation as Record<string, unknown>).suggested_deliverables as unknown[]).every((item: unknown) => typeof item === "string")
  );
  return (
    "summary" in content && typeof content.summary === "string" &&
    "strength_explanations" in content && Array.isArray(content.strength_explanations) &&
    "improvement_explanations" in content && Array.isArray(content.improvement_explanations) &&
    "technology_context" in content && (typeof content.technology_context === "string" || content.technology_context === null) &&
    "project_area_context" in content && (typeof content.project_area_context === "string" || content.project_area_context === null) &&
    "limitations_note" in content && (typeof content.limitations_note === "string" || content.limitations_note === null) &&
    "next_project_recommendation" in content && hasValidRecommendation &&
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

export function getAuthStartUrl(): string {
  return getApiUrl(AUTH_START_PATH);
}

export async function getAuthMe(): Promise<AuthMeResponse> {
  let response: Response;

  try {
    response = await fetch(getApiUrl(AUTH_ME_PATH), { credentials: "include" });
  } catch {
    throw new ApiError("Oturum durumu doğrulanamadı.", 0, "auth_bootstrap_network_error");
  }

  const payload = await readJson(response);
  if (response.ok && isAuthMeResponse(payload)) return payload;
  throw new ApiError("Oturum durumu doğrulanamadı.", response.status, "auth_bootstrap_error");
}

export async function logout(): Promise<void> {
  let response: Response;

  try {
    response = await fetch(getApiUrl(AUTH_LOGOUT_PATH), {
      method: "POST",
      credentials: "include",
    });
  } catch {
    throw new ApiError("Oturum kapatılamadı.", 0, "logout_network_error");
  }

  if (response.status === 204) return;
  throw new ApiError("Oturum kapatılamadı.", response.status, "logout_error");
}
