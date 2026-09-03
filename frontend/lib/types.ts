export interface PortfolioAnalysisRequest {
  username: string;
}

export interface ViewerContext {
  is_owner: boolean;
  mode: "my_workspace" | "explore";
}

export type GuidedImprovementState = "needs_improvement" | "criteria_met";

export interface GuidedImprovementVerification {
  detected_repository_count: number;
  analyzed_repository_count: number;
  current_state: GuidedImprovementState;
  analysis_available: boolean;
  analysis_partial: boolean;
  reanalysis_required: boolean;
}

export interface GuidedImprovement {
  rule_key: string;
  title: string;
  why: string;
  steps: string[];
  verification: GuidedImprovementVerification;
}

export interface AuthenticatedUser {
  github_login: string;
  display_name: string | null;
  avatar_url: string | null;
  github_html_url: string | null;
}

export interface AuthMeResponse {
  authenticated: boolean;
  user: AuthenticatedUser | null;
}

export interface HistoryCategoryScore { key: string; label: string; score: number; }
export interface HistoryRecord {
  id: string;
  github_user_id: number;
  github_username: string;
  captured_at: string;
  analysis_version: string;
  analysis_schema_version: string;
  portfolio_score: number | null;
  category_scores: HistoryCategoryScore[];
  passed_checks: string[];
  failed_checks: string[];
}
export interface HistoryComparison {
  portfolio_score: number | null;
  category_scores: Array<{ key: string; label: string; delta: number }>;
  newly_passing_checks: string[];
  newly_failing_checks: string[];
  comparable: boolean;
  note: string | null;
}
export interface HistoryResponse {
  latest: HistoryRecord | null;
  previous: HistoryRecord | null;
  comparison: HistoryComparison | null;
  history: HistoryRecord[];
}

export type ActionPlanStatus = "todo" | "in_progress" | "done";

export interface ActionPlanTask {
  id: string;
  title: string;
  description: string | null;
  status: ActionPlanStatus;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface ActionPlanResponse {
  tasks: ActionPlanTask[];
}

export interface AISuggestion {
  title: string;
  description: string;
  reason: string;
  evidence_refs: string[];
}

export interface AISuggestionsAvailable {
  status: "available";
  suggestions: AISuggestion[];
}

export interface AISuggestionsUnavailable {
  status: "unavailable";
  reason: "not_configured" | "insufficient_evidence" | "timeout" | "unavailable" | "rate_limit" | "upstream_error" | "invalid_response";
}

export type AISuggestionsResponse = AISuggestionsAvailable | AISuggestionsUnavailable;

export interface GitHubUser {
  username: string;
  name: string | null;
  avatar_url: string;
  bio: string | null;
  public_repos: number;
  followers: number;
  following: number;
  html_url: string;
  created_at: string;
}

export interface GitHubRepository {
  name: string;
  description: string | null;
  html_url: string;
  primary_language: string | null;
  stars: number;
  forks: number;
  topics: string[];
  created_at: string;
  updated_at: string;
  archived: boolean;
  fork: boolean;
  default_branch: string;
}

export interface RepositoryStructureSignals {
  has_tests: boolean;
  has_ci: boolean;
  has_dockerfile: boolean;
  has_compose: boolean;
  has_env_example: boolean;
  has_license: boolean;
  has_gitignore: boolean;
  has_contributing: boolean;
}

export interface ReadmeAnalysis {
  exists: boolean;
  content_length: number;
  has_title: boolean;
  has_description: boolean;
  has_installation: boolean;
  has_usage: boolean;
  has_technologies: boolean;
  has_requirements: boolean;
  has_images: boolean;
  has_demo_link: boolean;
}

export type TechnologyCategory = "Data & ML" | "Backend" | "Frontend" | "Testing" | "Database";

export interface DetectedTechnology {
  name: string;
  category: TechnologyCategory;
  source_dependency: string;
}

export interface TechnologyAnalysis {
  dependencies: string[];
  technologies: DetectedTechnology[];
}

export interface RepositoryCategoryMatch {
  category: string;
  evidence_score: number;
  evidence: string[];
}

export interface RepositoryClassification {
  categories: RepositoryCategoryMatch[];
  primary_category: string;
}

export interface RepositoryAnalysis {
  repository: GitHubRepository;
  readme: ReadmeAnalysis;
  structure: RepositoryStructureSignals;
  tree_truncated: boolean;
  technologies: TechnologyAnalysis;
  classification: RepositoryClassification;
}

export interface ScoreRuleResult {
  key: string;
  label: string;
  passed: boolean;
  points_earned: number;
  points_possible: number;
  evidence: string;
}

export interface ScoreDimensionResult {
  key: string;
  label: string;
  points_earned: number;
  points_possible: number;
  score: number;
  rules: ScoreRuleResult[];
}

export interface RepositoryScore {
  version: string;
  overall_score: number;
  dimensions: ScoreDimensionResult[];
  is_partial: boolean;
  limitations: string[];
}

export interface PortfolioRepositorySelection {
  version: string;
  selected: GitHubRepository[];
  excluded: ExcludedPortfolioRepository[];
}

export type ExclusionReason = "fork_repository" | "archived_repository";

export interface ExcludedPortfolioRepository {
  repository: GitHubRepository;
  reasons: ExclusionReason[];
}

export interface PortfolioRepositoryResult {
  repository: GitHubRepository;
  analysis: RepositoryAnalysis;
  score: RepositoryScore;
}

export interface PortfolioRepositoryFailure {
  repository: GitHubRepository;
  code: string;
  message: string;
}

export interface PortfolioRepositoryAnalysis {
  selection_version: string;
  repositories: PortfolioRepositoryResult[];
  failures: PortfolioRepositoryFailure[];
  has_failures: boolean;
}

export interface PortfolioTechnologyUsage {
  technology: string;
  repository_count: number;
}

export interface PortfolioCategoryUsage {
  category: string;
  repository_count: number;
}

export interface PortfolioSignalCount {
  key: string;
  label: string;
  detected_repository_count: number;
}

export interface RepositoryScoreBucket {
  min_score: number;
  max_score: number;
  repository_count: number;
}

export interface PortfolioAggregation {
  selection_version: string;
  selected_repository_count: number;
  successful_repository_count: number;
  failed_repository_count: number;
  has_failures: boolean;
  partial_evidence_repository_count: number;
  technology_distribution: PortfolioTechnologyUsage[];
  category_distribution: PortfolioCategoryUsage[];
  primary_category_distribution: PortfolioCategoryUsage[];
  portfolio_signals: PortfolioSignalCount[];
  repository_score_distribution: RepositoryScoreBucket[];
}

export interface PortfolioInsight {
  key: string;
  message: string;
  detected_repository_count: number;
  analyzed_repository_count: number;
}

export interface PortfolioIntelligence {
  version: string;
  strength_signals: PortfolioInsight[];
  improvement_signals: PortfolioInsight[];
  recurring_technologies: Array<{ technology: string; repository_count: number }>;
  dominant_areas: Array<{ category: string; repository_count: number }>;
  limitations: string[];
}

export interface PortfolioScoreRuleResult {
  key: string;
  label: string;
  weight: number;
  detected_repository_count: number;
  analyzed_repository_count: number;
}

export interface PortfolioScoreDimensionResult {
  key: string;
  label: string;
  points_earned: number;
  points_possible: number;
  score: number;
  rules: PortfolioScoreRuleResult[];
}

export interface PortfolioScore {
  version: string;
  is_available: boolean;
  overall_score: number | null;
  scored_repository_count: number;
  dimensions: PortfolioScoreDimensionResult[];
  is_partial: boolean;
  limitations: string[];
}

export interface GitHubPortfolioAnalysis {
  user: GitHubUser;
  selection: PortfolioRepositorySelection;
  repository_analysis: PortfolioRepositoryAnalysis;
  aggregation: PortfolioAggregation;
  intelligence: PortfolioIntelligence;
  score: PortfolioScore;
}

export interface GitHubPortfolioAnalysisResponse extends GitHubPortfolioAnalysis {
  viewer_context: ViewerContext;
  guided_improvements: GuidedImprovement[];
}

export interface OperationalErrorDetail {
  code: string;
  message: string;
}

export interface OperationalErrorResponse {
  detail: OperationalErrorDetail;
}

export type InterpretationUnavailableReason =
  | "not_configured"
  | "insufficient_evidence"
  | "timeout"
  | "unavailable"
  | "rate_limit"
  | "upstream_error"
  | "invalid_response";

export interface InterpretationExplanation {
  signal_key: string;
  explanation: string;
}

export interface NextProjectRecommendation {
  title: string;
  goal: string;
  rationale: string;
  focus_signal_keys: string[];
  suggested_deliverables: string[];
}

export interface PortfolioInterpretation {
  summary: string;
  strength_explanations: InterpretationExplanation[];
  improvement_explanations: InterpretationExplanation[];
  technology_context: string | null;
  project_area_context: string | null;
  limitations_note: string | null;
  next_project_recommendation: NextProjectRecommendation | null;
}

export interface PortfolioInterpretationAvailable {
  status: "available";
  interpretation: PortfolioInterpretation;
}

export interface PortfolioInterpretationUnavailable {
  status: "unavailable";
  reason: InterpretationUnavailableReason;
}

export type PublicPortfolioInterpretationResult =
  | PortfolioInterpretationAvailable
  | PortfolioInterpretationUnavailable;

export interface GitHubPortfolioInterpretationResponse {
  analysis: GitHubPortfolioAnalysis;
  interpretation: PublicPortfolioInterpretationResult;
  viewer_context: ViewerContext;
  guided_improvements: GuidedImprovement[];
}
