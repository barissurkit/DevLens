export interface PortfolioAnalysisRequest {
  username: string;
}

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
  excluded: Array<{
    repository: GitHubRepository;
    reasons: string[];
  }>;
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

export interface OperationalErrorDetail {
  code: string;
  message: string;
}

export interface OperationalErrorResponse {
  detail: OperationalErrorDetail;
}
