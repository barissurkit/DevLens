import { categoryLabel, scoreTone, type ScoreTone } from "./presentation";
import { topImprovements, type Improvement } from "./priorities";
import { absenceMayBeIncomplete, repositoryHasSignal, signalLabel } from "./signals";
import type {
  ExclusionReason,
  GitHubPortfolioAnalysis,
  PortfolioInsight,
  PortfolioRepositoryResult,
  PortfolioScoreDimensionResult,
} from "./types";

/** "ozet": the short report; "detay": the short report followed by every repository and the scoring method. */
export type ReportMode = "ozet" | "detay";

export const REPORT_MODES: ReadonlyArray<{ mode: ReportMode; label: string; description: string }> = [
  { mode: "ozet", label: "Özet rapor", description: "Kapak ve 1–2 sayfalık değerlendirme: skor, güçlü yönler, öncelikli iyileştirmeler" },
  { mode: "detay", label: "Ayrıntılı rapor", description: "Özetin yanında her repository için ayrıntılı kontrol listesi ve puanlama yöntemi" },
];

export function parseReportMode(value: string | null | undefined): ReportMode {
  return value === "detay" ? "detay" : "ozet";
}

const DIMENSION_ORDER = ["documentation_consistency", "testing_automation_adoption", "repository_hygiene_consistency", "maintenance_visibility"];

const DIMENSION_DESCRIPTIONS: Record<string, string> = {
  documentation_consistency: "README başlığı, açıklama, kurulum, kullanım, gereksinim ve teknoloji bölümlerinin repository'ler arasındaki tutarlılığı.",
  testing_automation_adoption: "Test dizini yapısı ve GitHub Actions CI iş akışının repository'lerdeki görünümü.",
  repository_hygiene_consistency: ".gitignore, lisans dosyası ve katkı rehberi gibi repository pratikleri.",
  maintenance_visibility: "Repository açıklaması, konu etiketleri ve son 12 ayda yapılan güncellemeler.",
};

export interface ReportDimension {
  key: string;
  label: string;
  description: string;
  earned: number;
  possible: number;
  /** 0-100 within the dimension. */
  percent: number;
}

export interface ReportCheck {
  key: string;
  label: string;
  present: boolean;
  /** The file tree was cut short, so an absent file may exist unseen. */
  uncertain: boolean;
}

export interface ReportCheckGroup {
  title: string;
  checks: ReportCheck[];
}

export interface ReportRepository {
  name: string;
  url: string;
  description: string | null;
  category: string;
  language: string | null;
  score: number;
  tone: ScoreTone;
  isPartial: boolean;
  groups: ReportCheckGroup[];
  technologies: string[];
  /** How many more technologies exist than the report lists. */
  extraTechnologies: number;
}

export interface ReportRule {
  dimension: string;
  label: string;
  weight: number;
}

export interface ReportModel {
  mode: ReportMode;
  username: string;
  displayName: string;
  profileUrl: string;
  avatarUrl: string | null;
  hasScore: boolean;
  score: number | null;
  tone: ScoreTone | null;
  overview: string;
  dimensions: ReportDimension[];
  strengths: PortfolioInsight[];
  priorities: Improvement[];
  /** Points the listed priorities could add, capped at the points that are left to win. */
  potentialGain: number;
  technologies: Array<{ name: string; count: number }>;
  areas: Array<{ name: string; count: number }>;
  scope: Array<{ label: string; value: number; warn?: boolean }>;
  limitations: string[];
  repositories: ReportRepository[];
  excluded: Array<{ name: string; reason: string }>;
  failures: Array<{ name: string; message: string }>;
  rules: ReportRule[];
  analyzedRepositoryCount: number;
}

const GROUPS: Array<{ title: string; keys: string[] }> = [
  { title: "Dokümantasyon", keys: ["readme_exists", "readme_title", "readme_description", "readme_installation", "readme_usage", "readme_requirements", "readme_technologies"] },
  { title: "Yapı ve otomasyon", keys: ["tests_structure", "ci_workflow", "gitignore", "license", "contributing"] },
  { title: "Bakım ve görünürlük", keys: ["repo_description", "repo_topics", "recent_activity"] },
];

const EXCLUSION_REASONS: Record<ExclusionReason, string> = {
  fork_repository: "fork",
  archived_repository: "arşivlenmiş",
};

const MAX_LISTED_TECHNOLOGIES = 6;
const MAX_STRENGTHS = 3;
const MAX_TAGS = 12;

function orderDimensions(dimensions: PortfolioScoreDimensionResult[]): PortfolioScoreDimensionResult[] {
  const rank = (key: string) => (DIMENSION_ORDER.indexOf(key) === -1 ? DIMENSION_ORDER.length : DIMENSION_ORDER.indexOf(key));
  return [...dimensions].sort((a, b) => rank(a.key) - rank(b.key));
}

function repositoryChecks(repository: PortfolioRepositoryResult): ReportCheckGroup[] {
  return GROUPS.map((group) => ({
    title: group.title,
    checks: group.keys.map((key) => {
      const present = repositoryHasSignal(repository, key) === true;
      return { key, label: signalLabel(key), present, uncertain: !present && absenceMayBeIncomplete(repository, key) };
    }),
  }));
}

function buildRepository(result: PortfolioRepositoryResult): ReportRepository {
  const technologies = result.analysis.technologies.technologies.map((technology) => technology.name);
  const unique = [...new Set(technologies)];
  return {
    name: result.repository.name,
    url: result.repository.html_url,
    description: result.repository.description?.trim() || null,
    category: categoryLabel(result.analysis.classification.primary_category),
    language: result.repository.primary_language,
    score: result.score.overall_score,
    tone: scoreTone(result.score.overall_score),
    isPartial: result.score.is_partial,
    groups: repositoryChecks(result),
    technologies: unique.slice(0, MAX_LISTED_TECHNOLOGIES),
    extraTechnologies: Math.max(0, unique.length - MAX_LISTED_TECHNOLOGIES),
  };
}

/** A short, plain-language summary built only from the numbers of the analysis. */
export function overviewSentence(analysis: GitHubPortfolioAnalysis): string {
  const { user, score, aggregation } = analysis;
  const analyzed = aggregation.successful_repository_count;
  const scope = `@${user.username} hesabının ${user.public_repos} herkese açık repository'sinden ${analyzed} tanesi analiz edildi`;
  if (!score.is_available || score.overall_score === null) {
    return `${scope}. Skor hesaplanabilmesi için en az iki repository'nin başarıyla analiz edilmesi gerekir.`;
  }
  const tone = scoreTone(score.overall_score);
  const dimensions = orderDimensions(score.dimensions);
  const strongest = [...dimensions].sort((a, b) => b.score - a.score)[0];
  const weakest = [...dimensions].sort((a, b) => a.score - b.score)[0];
  const spread = strongest && weakest && strongest.key !== weakest.key
    ? ` En güçlü boyut %${strongest.score} ile "${strongest.label}", en zayıf boyut %${weakest.score} ile "${weakest.label}" oldu.`
    : "";
  return `${scope}. Portföy kanıt skoru ${score.overall_score} / 100 (${tone.label}).${spread}`;
}

export function buildReportModel(analysis: GitHubPortfolioAnalysis, mode: ReportMode): ReportModel {
  const { user, score, aggregation, intelligence, selection } = analysis;
  const hasScore = score.is_available && score.overall_score !== null;
  const dimensions = orderDimensions(score.dimensions);
  const priorities = hasScore ? topImprovements(score.dimensions) : [];
  const rawGain = priorities.reduce((sum, item) => sum + item.points, 0);
  const potentialGain = Math.round(hasScore ? Math.min(rawGain, 100 - (score.overall_score as number)) : rawGain);
  const limitations = [...new Set([...score.limitations, ...intelligence.limitations])];

  return {
    mode,
    username: user.username,
    displayName: user.name || `@${user.username}`,
    profileUrl: user.html_url,
    avatarUrl: user.avatar_url || null,
    hasScore,
    score: hasScore ? score.overall_score : null,
    tone: hasScore ? scoreTone(score.overall_score as number) : null,
    overview: overviewSentence(analysis),
    dimensions: dimensions.map((dimension) => ({
      key: dimension.key,
      label: dimension.label,
      description: DIMENSION_DESCRIPTIONS[dimension.key] ?? "",
      earned: dimension.points_earned,
      possible: dimension.points_possible,
      percent: dimension.score,
    })),
    strengths: intelligence.strength_signals.slice(0, MAX_STRENGTHS),
    priorities,
    potentialGain,
    technologies: intelligence.recurring_technologies.slice(0, MAX_TAGS).map((item) => ({ name: item.technology, count: item.repository_count })),
    areas: intelligence.dominant_areas.slice(0, MAX_TAGS).map((item) => ({ name: categoryLabel(item.category), count: item.repository_count })),
    scope: [
      { label: "Herkese açık repository", value: user.public_repos },
      { label: "Analiz için seçilen", value: aggregation.selected_repository_count },
      { label: "Hariç tutulan", value: selection.excluded.length },
      { label: "Başarılı analiz", value: aggregation.successful_repository_count },
      { label: "Başarısız analiz", value: aggregation.failed_repository_count, warn: aggregation.failed_repository_count > 0 },
      { label: "Kısmi kanıt", value: aggregation.partial_evidence_repository_count, warn: aggregation.partial_evidence_repository_count > 0 },
    ],
    limitations,
    repositories: mode === "detay"
      ? [...analysis.repository_analysis.repositories].sort((a, b) => b.score.overall_score - a.score.overall_score || a.repository.name.localeCompare(b.repository.name, "tr")).map(buildRepository)
      : [],
    excluded: selection.excluded.map((item) => ({ name: item.repository.name, reason: item.reasons.map((reason) => EXCLUSION_REASONS[reason] ?? reason).join(", ") })),
    failures: analysis.repository_analysis.failures.map((item) => ({ name: item.repository.name, message: item.message })),
    rules: orderDimensions(score.dimensions).flatMap((dimension) => dimension.rules.map((rule) => ({ dimension: dimension.label, label: rule.label, weight: rule.weight }))),
    analyzedRepositoryCount: aggregation.successful_repository_count,
  };
}
