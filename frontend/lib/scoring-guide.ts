import { SCORE_MODERATE_MIN, SCORE_STRONG_MIN } from "./presentation";

/**
 * The scoring policy in plain language, for the scoring guide page. The weights mirror the backend policy
 * (`portfolio_scoring.py`, version v3); a test compares them with a recorded analysis so a change on one side
 * cannot go unnoticed on the other.
 */
export interface GuideRule {
  key: string;
  label: string;
  weight: number;
  /** What exactly is looked for in a repository. */
  check: string;
}

export interface GuideDimension {
  key: string;
  label: string;
  summary: string;
  rules: GuideRule[];
}

export const SCORING_GUIDE: GuideDimension[] = [
  {
    key: "documentation_consistency",
    label: "Dokümantasyon",
    summary: "Repository'lerin README dosyalarının ne kadar tutarlı ve eksiksiz olduğu.",
    rules: [
      { key: "readme_exists", label: "README mevcut", weight: 6, check: "Repository'de bir README dosyası var." },
      { key: "readme_title", label: "README başlığı", weight: 4, check: "README'de bir Markdown başlığı (#) var." },
      { key: "readme_description", label: "README açıklaması", weight: 6, check: "Başlığın altında en az 40 karakterlik bir açıklama paragrafı var. Görsel, liste, tablo ve kod bloğu açıklama sayılmaz." },
      { key: "readme_installation", label: "README kurulumu", weight: 7, check: "“Installation”, “Setup”, “Getting started” ya da “Kurulum” başlıklı bir bölüm var." },
      { key: "readme_usage", label: "README kullanımı", weight: 7, check: "“Usage”, “Examples” ya da “Kullanım” başlıklı bir bölüm var." },
      { key: "readme_technologies", label: "README teknolojileri", weight: 5, check: "“Technologies”, “Tech stack”, “Built with” ya da “Teknolojiler” başlıklı bir bölüm var." },
      { key: "readme_requirements", label: "README gereksinimleri", weight: 5, check: "“Requirements”, “Prerequisites”, “Dependencies” ya da “Gereksinimler” başlıklı bir bölüm var." },
    ],
  },
  {
    key: "testing_automation_adoption",
    label: "Test ve Otomasyon",
    summary: "Kodun otomatik olarak doğrulanıp doğrulanmadığı.",
    rules: [
      { key: "tests_structure", label: "Test yapısı", weight: 15, check: "Yolunda “test” ya da “tests” adlı bir dizin bulunan en az bir dosya var." },
      { key: "ci_workflow", label: "CI iş akışı", weight: 10, check: ".github/workflows klasöründe en az bir .yml ya da .yaml iş akışı dosyası var." },
    ],
  },
  {
    key: "repository_hygiene_consistency",
    label: "Repository Hijyeni",
    summary: "Bir repository'nin başkaları için kullanılabilir ve düzenli olması.",
    rules: [
      { key: "gitignore", label: ".gitignore", weight: 6, check: "Repository'de bir .gitignore dosyası var." },
      { key: "license", label: "LICENSE", weight: 5, check: "Repository'de bir LICENSE dosyası (LICENSE, LICENSE.md ya da LICENSE.txt) var." },
      { key: "contributing", label: "CONTRIBUTING", weight: 4, check: "Repository'de bir CONTRIBUTING.md dosyası var." },
    ],
  },
  {
    key: "maintenance_visibility",
    label: "Bakım ve Görünürlük",
    summary: "Repository'nin bulunabilir olması ve güncel tutulması.",
    rules: [
      { key: "repo_description", label: "Repository açıklaması", weight: 6, check: "GitHub'daki repository açıklama alanı dolu." },
      { key: "repo_topics", label: "Konu etiketleri", weight: 6, check: "Repository'de en az bir GitHub konu etiketi (topic) var." },
      { key: "recent_activity", label: "Son 12 ayda güncelleme", weight: 8, check: "Repository'ye son 12 ay içinde bir değişiklik gönderilmiş. Bu kural zamanla değişebilen tek kuraldır." },
    ],
  },
];

export const dimensionPoints = (dimension: GuideDimension): number => dimension.rules.reduce((sum, rule) => sum + rule.weight, 0);

export interface ScoreBand {
  key: "strong" | "moderate" | "weak";
  label: string;
  range: string;
  meaning: string;
  text: string;
  badge: string;
}

/** The bands shown next to the portfolio score, from the same thresholds the result screen uses. */
export const SCORE_BANDS: ScoreBand[] = [
  { key: "strong", label: "Güçlü", range: `${SCORE_STRONG_MIN}–100`, meaning: "Kanıtlar çoğu repository'de tutarlı biçimde var.", text: "text-emerald-700", badge: "bg-emerald-50 text-emerald-800" },
  { key: "moderate", label: "Gelişebilir", range: `${SCORE_MODERATE_MIN}–${SCORE_STRONG_MIN - 1}`, meaning: "Temel kanıtlar var, birkaç alan tutarsız ya da eksik.", text: "text-amber-700", badge: "bg-amber-50 text-amber-800" },
  { key: "weak", label: "Zayıf", range: `0–${SCORE_MODERATE_MIN - 1}`, meaning: "Kanıtların çoğu repository'lerde eksik; en hızlı kazanç burada.", text: "text-rose-700", badge: "bg-rose-50 text-rose-800" },
];
