import type {
  AnalysisProgress,
  GitHubPortfolioInterpretationResponse,
  GitHubPortfolioAnalysis,
  GitHubPortfolioAnalysisResponse,
  InterpretationUnavailableReason,
  OperationalErrorResponse,
  PortfolioAnalysisRequest,
  AuthMeResponse,
  ActionPlanResponse,
  ActionPlanTask,
  ActionPlanStatus,
  AISuggestionsResponse,
  HistoryResponse,
  OpenSourceContributions,
  GuidedImprovement,
} from "./types";

const ANALYSIS_PATH = "/api/v1/analysis";
const INTERPRETATION_PATH = "/api/v1/interpretation";
const AUTH_START_PATH = "/api/v1/auth/github";
const AUTH_ME_PATH = "/api/v1/auth/me";
const AUTH_LOGOUT_PATH = "/api/v1/auth/logout";
const ACTION_PLAN_PATH = "/api/v1/workspace/action-plan";
const AI_SUGGESTIONS_PATH = "/api/v1/workspace/ai-suggestions";
const HISTORY_PATH = "/api/v1/workspace/analysis-history";
const DEFAULT_ERROR_MESSAGE = "Analiz sırasında beklenmeyen bir hata oluştu.";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;
  /** Seconds the server asked the client to wait (from the Retry-After header), when known. */
  readonly retryAfterSeconds: number | undefined;

  constructor(message: string, status: number, code?: string, retryAfterSeconds?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

function parseRetryAfter(response: Response): number | undefined {
  const seconds = Number(response.headers.get("Retry-After"));
  return Number.isFinite(seconds) && seconds > 0 ? Math.ceil(seconds) : undefined;
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

function isViewerContext(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const context = value as Record<string, unknown>;
  return typeof context.is_owner === "boolean" && (context.mode === "my_workspace" || context.mode === "explore");
}

function isGuidedImprovement(value: unknown): value is GuidedImprovement {
  if (typeof value !== "object" || value === null) return false;
  const item = value as Record<string, unknown>;
  const verification = item.verification;
  if (typeof item.rule_key !== "string" || item.rule_key.trim().length === 0 ||
      typeof item.title !== "string" || item.title.trim().length === 0 ||
      typeof item.why !== "string" || item.why.trim().length === 0 ||
      !Array.isArray(item.steps) || item.steps.length === 0 ||
      !item.steps.every((step) => typeof step === "string" && step.trim().length > 0)) return false;
  if (typeof verification !== "object" || verification === null) return false;
  const details = verification as Record<string, unknown>;
  const detectedCount = details.detected_repository_count;
  const analyzedCount = details.analyzed_repository_count;
  return typeof detectedCount === "number" && Number.isInteger(detectedCount) && detectedCount >= 0 &&
    typeof analyzedCount === "number" && Number.isInteger(analyzedCount) && analyzedCount >= 0 &&
    (details.current_state === "needs_improvement" || details.current_state === "criteria_met") &&
    typeof details.analysis_available === "boolean" && typeof details.analysis_partial === "boolean" &&
    typeof details.reanalysis_required === "boolean";
}

function normalizeGuidedImprovements(value: unknown): GuidedImprovement[] | null {
  if (value === undefined) return [];
  return Array.isArray(value) && value.every(isGuidedImprovement) ? value : null;
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
  if (typeof value !== "object" || value === null || !("analysis" in value) || !("interpretation" in value) || !("viewer_context" in value)) return false;
  if (!isViewerContext(value.viewer_context)) return false;
  if (!isGitHubPortfolioAnalysis(value.analysis)) return false;
  const guidedImprovements = normalizeGuidedImprovements((value as Record<string, unknown>).guided_improvements);
  if (guidedImprovements === null) return false;
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

function isActionPlanResponse(value: unknown): value is ActionPlanResponse {
  return typeof value === "object" && value !== null && Array.isArray((value as { tasks?: unknown }).tasks);
}

function isHistoryRecord(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return typeof record.id === "string" && typeof record.github_user_id === "number" && typeof record.github_username === "string" &&
    typeof record.captured_at === "string" && typeof record.analysis_version === "string" && typeof record.analysis_schema_version === "string" &&
    (record.portfolio_score === null || typeof record.portfolio_score === "number") && Array.isArray(record.category_scores) &&
    record.category_scores.every((item) => typeof item === "object" && item !== null && typeof (item as Record<string, unknown>).key === "string" && typeof (item as Record<string, unknown>).label === "string" && typeof (item as Record<string, unknown>).score === "number") &&
    Array.isArray(record.passed_checks) && record.passed_checks.every((item) => typeof item === "string") &&
    Array.isArray(record.failed_checks) && record.failed_checks.every((item) => typeof item === "string");
}

function isHistoryComparison(value: unknown): boolean {
  if (value === null) return true;
  if (typeof value !== "object") return false;
  const comparison = value as Record<string, unknown>;
  return (comparison.portfolio_score === null || typeof comparison.portfolio_score === "number") &&
    Array.isArray(comparison.category_scores) && comparison.category_scores.every((item) => typeof item === "object" && item !== null && typeof (item as Record<string, unknown>).key === "string" && typeof (item as Record<string, unknown>).label === "string" && typeof (item as Record<string, unknown>).delta === "number") &&
    Array.isArray(comparison.newly_passing_checks) && comparison.newly_passing_checks.every((item) => typeof item === "string") &&
    Array.isArray(comparison.newly_failing_checks) && comparison.newly_failing_checks.every((item) => typeof item === "string") &&
    typeof comparison.comparable === "boolean" && (comparison.note === null || typeof comparison.note === "string");
}

function isHistoryResponse(value: unknown): value is HistoryResponse {
  if (typeof value !== "object" || value === null) return false;
  const response = value as Record<string, unknown>;
  return (response.latest === null || isHistoryRecord(response.latest)) &&
    (response.previous === null || isHistoryRecord(response.previous)) && isHistoryComparison(response.comparison) &&
    Array.isArray(response.history) && response.history.every(isHistoryRecord);
}

async function actionPlanRequest(path: string, init: RequestInit = {}): Promise<unknown> {
  let response: Response;
  const isMutation = Boolean(init.method && init.method !== "GET");
  const request: RequestInit = { ...init, credentials: "include" };
  if (isMutation) {
    request.headers = { "Content-Type": "application/json", ...(init.headers || {}) };
  }
  try {
    response = await fetch(getApiUrl(path), request);
  } catch {
    throw new ApiError("Aksiyon planı servisine ulaşılamadı.", 0, "network_error");
  }
  const payload = await readJson(response);
  if (!response.ok) {
    if (isOperationalErrorResponse(payload)) {
      throw new ApiError(payload.detail.message, response.status, payload.detail.code);
    }
    throw new ApiError("Aksiyon planı işlemi tamamlanamadı.", response.status, "action_plan_error");
  }
  return payload;
}

export async function getActionPlan(): Promise<ActionPlanResponse> {
  const payload = await actionPlanRequest(ACTION_PLAN_PATH);
  if (isActionPlanResponse(payload)) return payload;
  throw new ApiError("Aksiyon planı geçersiz bir yanıt döndürdü.", 200, "malformed_response");
}

function isOpenSourceContributions(value: unknown): value is OpenSourceContributions {
  if (typeof value !== "object" || value === null) return false;
  const body = value as Partial<OpenSourceContributions>;
  return typeof body.username === "string"
    && typeof body.total_merged === "number"
    && typeof body.repository_count === "number"
    && typeof body.is_truncated === "boolean"
    && Array.isArray(body.contributions)
    && body.contributions.every((item) => typeof item?.repository === "string" && typeof item.html_url === "string" && typeof item.merged_count === "number" && typeof item.latest_title === "string" && typeof item.latest_url === "string");
}

/** Merged pull requests the person made to other people's public repositories (public data, no sign-in). */
export async function getOpenSourceContributions(username: string): Promise<OpenSourceContributions> {
  let response: Response;
  try { response = await fetch(getApiUrl(`/api/v1/github/users/${encodeURIComponent(username)}/open-source`)); }
  catch { throw new ApiError("Açık kaynak katkılarına ulaşılamadı.", 0, "network_error"); }
  const payload = await readJson(response);
  if (!response.ok) {
    if (isOperationalErrorResponse(payload)) throw new ApiError(payload.detail.message, response.status, payload.detail.code);
    throw new ApiError("Açık kaynak katkıları yüklenemedi.", response.status, "open_source_error");
  }
  if (isOpenSourceContributions(payload)) return payload;
  throw new ApiError("Açık kaynak servisi geçersiz bir yanıt döndürdü.", response.status, "malformed_response");
}

export async function getAnalysisHistory(): Promise<HistoryResponse> {
  let response: Response;
  try { response = await fetch(getApiUrl(HISTORY_PATH), { credentials: "include" }); }
  catch { throw new ApiError("Geçmiş analizlere ulaşılamadı.", 0, "network_error"); }
  const payload = await readJson(response);
  if (!response.ok) throw new ApiError("Geçmiş analizler yüklenemedi.", response.status, "history_error");
  if (isHistoryResponse(payload)) return payload;
  throw new ApiError("Geçmiş analiz servisi geçersiz bir yanıt döndürdü.", response.status, "malformed_response");
}

export async function createActionPlanTask(input: { title: string; description?: string }): Promise<ActionPlanTask> {
  const payload = await actionPlanRequest(ACTION_PLAN_PATH, { method: "POST", body: JSON.stringify(input) });
  if (typeof payload === "object" && payload !== null && "id" in payload) return payload as ActionPlanTask;
  throw new ApiError("Aksiyon planı geçersiz bir yanıt döndürdü.", 201, "malformed_response");
}

export async function updateActionPlanTask(id: string, input: { title?: string; description?: string | null; status?: ActionPlanStatus }): Promise<ActionPlanTask> {
  const payload = await actionPlanRequest(`${ACTION_PLAN_PATH}/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(input) });
  if (typeof payload === "object" && payload !== null && "id" in payload) return payload as ActionPlanTask;
  throw new ApiError("Aksiyon planı geçersiz bir yanıt döndürdü.", 200, "malformed_response");
}

export async function deleteActionPlanTask(id: string): Promise<void> {
  await actionPlanRequest(`${ACTION_PLAN_PATH}/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function generateAISuggestions(username: string): Promise<AISuggestionsResponse> {
  let response: Response;
  try {
    response = await fetch(getApiUrl(AI_SUGGESTIONS_PATH), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
    });
  } catch {
    throw new ApiError("AI öneri servisine ulaşılamadı.", 0, "network_error");
  }
  const payload = await readJson(response);
  if (!response.ok) {
    if (isOperationalErrorResponse(payload)) throw new ApiError(payload.detail.message, response.status, payload.detail.code);
    throw new ApiError("AI önerileri oluşturulamadı.", response.status, "ai_suggestions_error");
  }
  if (typeof payload === "object" && payload !== null && (payload as { status?: unknown }).status === "available" && Array.isArray((payload as { suggestions?: unknown }).suggestions)) return payload as AISuggestionsResponse;
  if (typeof payload === "object" && payload !== null && (payload as { status?: unknown }).status === "unavailable" && typeof (payload as { reason?: unknown }).reason === "string") return payload as AISuggestionsResponse;
  throw new ApiError("AI öneri servisi geçersiz bir yanıt döndürdü.", response.status, "malformed_response");
}

export async function analyzePortfolio(
  username: string,
): Promise<GitHubPortfolioAnalysisResponse> {
  const request: PortfolioAnalysisRequest = { username };
  let response: Response;

  try {
    response = await fetch(getAnalysisUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(request),
    });
  } catch {
    throw new ApiError("Analiz servisine ulaşılamadı.", 0, "network_error");
  }

  const payload = await readJson(response);
  if (response.ok) {
    if (isGitHubPortfolioAnalysis(payload) && "viewer_context" in payload && isViewerContext(payload.viewer_context)) {
      const guidedImprovements = normalizeGuidedImprovements((payload as Record<string, unknown>).guided_improvements);
      if (guidedImprovements !== null) return { ...payload, guided_improvements: guidedImprovements } as GitHubPortfolioAnalysisResponse;
    }
    throw new ApiError("Analiz servisi geçersiz bir yanıt döndürdü.", response.status, "malformed_response");
  }

  if (isOperationalErrorResponse(payload)) {
    throw new ApiError(payload.detail.message, response.status, payload.detail.code, parseRetryAfter(response));
  }

  if (response.status === 422) {
    throw new ApiError("Kullanıcı adı geçerli değil.", response.status, "validation_error");
  }

  throw new ApiError(DEFAULT_ERROR_MESSAGE, response.status, "unexpected_api_error");
}

export interface AnalyzeOptions {
  /** When set, the analysis runs through the streaming endpoint and reports progress. */
  onProgress?: (progress: AnalysisProgress) => void;
  /** Skip the server-side snapshot cache. */
  refresh?: boolean;
  /** Retry the AI interpretation now, bypassing the server's short cooldown after a failed attempt. */
  retryInterpretation?: boolean;
  signal?: AbortSignal;
}

export async function analyzePortfolioWithInterpretation(
  username: string,
  options: AnalyzeOptions = {},
): Promise<GitHubPortfolioInterpretationResponse> {
  if (options.onProgress) {
    const streamed = await streamInterpretation(username, options);
    if (streamed !== null) return streamed;
  }
  return requestInterpretation(username, options);
}

const PROGRESS_STAGES: readonly string[] = ["profile", "repositories", "interpretation"];

function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && (error as { name?: unknown }).name === "AbortError";
}

function buildInterpretationRequest(username: string, options: AnalyzeOptions): PortfolioAnalysisRequest {
  const request: PortfolioAnalysisRequest = { username };
  if (options.refresh) request.refresh = true;
  if (options.retryInterpretation) request.retry_interpretation = true;
  return request;
}

function errorFromPayload(status: number, payload: unknown, retryAfterSeconds?: number): ApiError {
  if (isOperationalErrorResponse(payload)) return new ApiError(payload.detail.message, status, payload.detail.code, retryAfterSeconds);
  if (status === 422) return new ApiError("Kullanıcı adı geçerli değil.", status, "validation_error");
  return new ApiError(DEFAULT_ERROR_MESSAGE, status, "unexpected_api_error");
}

/** Returns null when the streaming endpoint is unavailable so the caller can use the plain endpoint. */
async function streamInterpretation(
  username: string,
  options: AnalyzeOptions,
): Promise<GitHubPortfolioInterpretationResponse | null> {
  let response: Response;
  try {
    response = await fetch(getApiUrl(`${INTERPRETATION_PATH}/stream`), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildInterpretationRequest(username, options)),
      signal: options.signal,
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    return null;
  }

  if (!response.ok) {
    if (response.status === 404 || response.status === 405) return null;
    // Failures before streaming starts (rate limit, validation) use the regular JSON error contract.
    throw errorFromPayload(response.status, await readJson(response), parseRetryAfter(response));
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/x-ndjson") || !response.body) return null;
  return readEventStream(response.body, options.onProgress);
}

function handleStreamLine(
  line: string,
  onProgress: ((progress: AnalysisProgress) => void) | undefined,
): GitHubPortfolioInterpretationResponse | null {
  if (!line.trim()) return null;
  let event: unknown;
  try {
    event = JSON.parse(line);
  } catch {
    throw new ApiError("Analiz servisi geçersiz bir yanıt döndürdü.", 200, "malformed_response");
  }
  if (typeof event !== "object" || event === null) return null;
  const record = event as Record<string, unknown>;

  if (record.event === "progress") {
    if (typeof record.stage === "string" && PROGRESS_STAGES.includes(record.stage) && typeof record.completed === "number" && typeof record.total === "number") {
      onProgress?.({ stage: record.stage as AnalysisProgress["stage"], completed: record.completed, total: record.total });
    }
    return null;
  }
  if (record.event === "result") {
    if (isGitHubPortfolioInterpretationResponse(record.data)) {
      return { ...record.data, guided_improvements: normalizeGuidedImprovements((record.data as unknown as Record<string, unknown>).guided_improvements) || [] };
    }
    throw new ApiError("Analiz servisi geçersiz bir yanıt döndürdü.", 200, "malformed_response");
  }
  if (record.event === "error") {
    const status = typeof record.status === "number" ? record.status : 500;
    throw errorFromPayload(status, { detail: record.detail });
  }
  return null;
}

async function readEventStream(
  body: ReadableStream<Uint8Array>,
  onProgress: ((progress: AnalysisProgress) => void) | undefined,
): Promise<GitHubPortfolioInterpretationResponse> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newline = buffer.indexOf("\n");
      while (newline >= 0) {
        const result = handleStreamLine(buffer.slice(0, newline), onProgress);
        if (result) return result;
        buffer = buffer.slice(newline + 1);
        newline = buffer.indexOf("\n");
      }
    }
    const last = handleStreamLine(buffer + decoder.decode(), onProgress);
    if (last) return last;
  } catch (error) {
    if (error instanceof ApiError || isAbortError(error)) throw error;
    throw new ApiError("Analiz bağlantısı kesildi.", 0, "network_error");
  } finally {
    void reader.cancel().catch(() => undefined);
  }
  throw new ApiError("Analiz bağlantısı beklenmedik şekilde kapandı.", 0, "network_error");
}

async function requestInterpretation(
  username: string,
  options: AnalyzeOptions,
): Promise<GitHubPortfolioInterpretationResponse> {
  const request = buildInterpretationRequest(username, options);
  let response: Response;

  try {
    response = await fetch(getApiUrl(INTERPRETATION_PATH), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: options.signal,
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new ApiError("Analiz servisine ulaşılamadı.", 0, "network_error");
  }

  const payload = await readJson(response);
  if (response.ok) {
    if (isGitHubPortfolioInterpretationResponse(payload)) {
      return { ...payload, guided_improvements: normalizeGuidedImprovements((payload as unknown as Record<string, unknown>).guided_improvements) || [] };
    }
    throw new ApiError("Analiz servisi geçersiz bir yanıt döndürdü.", response.status, "malformed_response");
  }

  if (isOperationalErrorResponse(payload)) {
    throw new ApiError(payload.detail.message, response.status, payload.detail.code, parseRetryAfter(response));
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
