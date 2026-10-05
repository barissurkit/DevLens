import { scoreTone } from "./presentation";
import { topImprovements } from "./priorities";
import { SCORING_GUIDE } from "./scoring-guide";
import { absenceMayBeIncomplete, repositoryHasSignal, splitRepositoriesBySignal } from "./signals";
import type { GitHubPortfolioAnalysis, PortfolioRepositoryResult } from "./types";

/** At most this many repositories are listed per rule; the rest is only counted, to keep the prompt readable. */
const MAX_REPOSITORIES_PER_RULE = 12;

/** What to do for each rule, written for an AI assistant that edits repositories. */
const TASKS: Record<string, string> = {
  readme_exists: "README.md dosyası ekle; projenin ne yaptığını ve nasıl kullanıldığını repository'nin gerçek koduna bakarak yaz.",
  readme_title: "README'nin ilk satırına proje adını içeren bir Markdown başlığı (#) ekle.",
  readme_description: "Başlığın altına projenin ne yaptığını anlatan, en az 40 karakterlik düz bir açıklama paragrafı ekle (görsel, liste veya kod bloğu açıklama sayılmaz).",
  readme_installation: "README'ye “Kurulum” başlıklı bir bölüm ekle; adımları projenin gerçek bağımlılık dosyalarına bakarak yaz ve komutları çalıştırıp doğrula.",
  readme_usage: "README'ye “Kullanım” başlıklı bir bölüm ekle; gerçekten çalışan kısa bir örnek ve beklenen çıktıyı göster.",
  readme_technologies: "README'ye “Teknolojiler” başlıklı bir bölüm ekle; yalnızca projede gerçekten kullanılan teknolojileri yaz.",
  readme_requirements: "README'ye “Gereksinimler” başlıklı bir bölüm ekle; gerekli çalışma ortamı ve sürümleri bağımlılık dosyalarından çıkar.",
  tests_structure: "`tests/` dizini oluştur ve projenin temel davranışını doğrulayan, gerçekten çalışan en az birkaç test ekle; testleri çalıştırıp geçtiğini doğrula.",
  ci_workflow: "`.github/workflows/` altına testleri (varsa lint'i de) her push ve pull request'te çalıştıran bir GitHub Actions iş akışı (.yml) ekle.",
  gitignore: "Projenin diline ve araçlarına uygun bir `.gitignore` ekle; derleme çıktıları, bağımlılık klasörleri ve gizli dosyalar (ör. .env) dışarıda kalsın.",
  license: "Bir LICENSE dosyası ekle. Hangi lisansın seçileceği bana ait bir karar: önce bana sor, kendi başına lisans seçme.",
  contributing: "Katkı yapmak isteyen biri için kısa bir `CONTRIBUTING.md` ekle (kurulum, testleri çalıştırma, pull request beklentileri).",
  repo_description: "Bu bir dosya değil, GitHub ayarıdır: repository'nin açıklama alanını tek cümleyle doldur (`gh repo edit --description` veya web arayüzü).",
  repo_topics: "Bu bir dosya değil, GitHub ayarıdır: repository'ye projeyi doğru anlatan birkaç konu etiketi (topic) ekle (`gh repo edit --add-topic` veya web arayüzü).",
  recent_activity: "Yalnızca anlamlı bir iyileştirme yap (ör. yukarıdaki eksiklerden biri). Sırf kural için boş veya anlamsız commit atma.",
};

const formatPoints = (value: number) => value.toLocaleString("tr-TR", { maximumFractionDigits: 1 });

/**
 * A prompt the person can give to their own AI assistant or coding agent to close the gaps DevLens found in the
 * whole portfolio. It is built from the deterministic analysis only (no AI call), lists the rules in the order of
 * the points they would add, and names the repositories each rule is missing in. Returns null when there is no
 * score or nothing left to improve.
 */
export function buildFixPrompt(analysis: GitHubPortfolioAnalysis): string | null {
  const { score, user } = analysis;
  if (!score.is_available || score.overall_score === null) return null;
  const improvements = topImprovements(score.dimensions, 100);
  if (improvements.length === 0) return null;

  const repositories = analysis.repository_analysis.repositories;
  const owner = user.username;
  const lines: string[] = [];

  lines.push("# Görev: GitHub portföyümü iyileştir", "");
  lines.push(
    `Ben @${owner}. DevLens, herkese açık GitHub repository'lerimi deterministik kurallarla inceledi ve aşağıdaki eksikleri buldu. Görevin, bu eksikleri gerçek ve doğru içerikle kapatmak.`,
    "",
  );

  lines.push("## Mevcut durum", "");
  lines.push(`- Portföy skoru: ${score.overall_score} / 100 (${scoreTone(score.overall_score).label}); ${score.scored_repository_count} repository üzerinden hesaplandı.`);
  for (const dimension of SCORING_GUIDE) {
    const result = score.dimensions.find((item) => item.key === dimension.key);
    if (result) lines.push(`- ${dimension.label}: ${result.points_earned} / ${result.points_possible}`);
  }
  lines.push("");

  lines.push("## Yapılacaklar (skoru en çok artıran önce)", "");
  improvements.forEach((item, index) => {
    lines.push(`### ${index + 1}. ${item.label} (+${formatPoints(item.points)} puan)`, "");
    lines.push(`${item.analyzedRepositories} repository'nin ${item.missingRepositories} tanesinde eksik.`, "");
    lines.push(`Ne yapılacak: ${TASKS[item.key] ?? item.label}`, "");
    const split = splitRepositoriesBySignal(repositories, item.key);
    if (split && split.missing.length > 0) {
      lines.push("Eksik olan repository'ler:");
      for (const repository of split.missing.slice(0, MAX_REPOSITORIES_PER_RULE)) {
        const uncertain = absenceMayBeIncomplete(repository, item.key) ? " (dosya listesi eksik alındı; önce var olup olmadığını kontrol et)" : "";
        lines.push(`- ${owner}/${repository.repository.name}: ${repository.repository.html_url}${uncertain}`);
      }
      if (split.missing.length > MAX_REPOSITORIES_PER_RULE) lines.push(`- … ve ${split.missing.length - MAX_REPOSITORIES_PER_RULE} repository daha`);
      lines.push("");
    }
  });

  lines.push("## Kurallar", "");
  lines.push(
    "- Her repository için ayrı bir dal aç ve ayrı bir pull request hazırla; main dalına doğrudan yazma.",
    "- İçeriği uydurma. README, test ve açıklamaları repository'nin gerçek koduna bakarak yaz; emin olmadığın şeyi bana sor.",
    "- Yalnızca yukarıdaki eksikleri kapat. Zaten sağlanan kurallara ve ilgisiz koda dokunma; mevcut dosyaları silme veya baştan yazma.",
    "- Eklediğin komutları ve testleri çalıştırıp doğrula; çalışmayan bir şeyi ekleme.",
    "- Gizli bilgi (anahtar, parola, .env içeriği) ekleme veya paylaşma.",
    "",
    "## Bitince",
    "",
    "Repository başına ne değiştirdiğini, hangi doğrulamaları yaptığını ve benden beklediğin kararları (ör. lisans) kısa bir listeyle özetle.",
  );

  return lines.join("\n");
}

/**
 * The same kind of prompt for one repository: every rule it is missing, the heaviest first. Returns null when the
 * repository already shows every signal.
 */
export function buildRepositoryFixPrompt(owner: string, result: PortfolioRepositoryResult): string | null {
  const gaps = SCORING_GUIDE.flatMap((dimension) => dimension.rules)
    .filter((rule) => repositoryHasSignal(result, rule.key) === false)
    .sort((left, right) => right.weight - left.weight || left.label.localeCompare(right.label, "tr"));
  if (gaps.length === 0) return null;

  const { repository, score } = result;
  const lines: string[] = [];
  lines.push(`# Görev: ${owner}/${repository.name} repository'sini iyileştir`, "");
  lines.push(
    `Ben @${owner}. DevLens, ${repository.html_url} repository'sini deterministik kurallarla inceledi ve aşağıdaki eksikleri buldu. Görevin, bu eksikleri gerçek ve doğru içerikle kapatmak.`,
    "",
  );
  lines.push("## Mevcut durum", "");
  lines.push(`- Repository skoru: ${score.overall_score} / 100 (${scoreTone(score.overall_score).label})`);
  if (repository.primary_language) lines.push(`- Ana dil: ${repository.primary_language}`);
  lines.push(`- Varsayılan dal: ${repository.default_branch}`, "");

  lines.push("## Yapılacaklar (puan değeri en yüksek önce)", "");
  gaps.forEach((rule, index) => {
    const uncertain = absenceMayBeIncomplete(result, rule.key) ? " (dosya listesi eksik alındı; önce var olup olmadığını kontrol et)" : "";
    lines.push(`### ${index + 1}. ${rule.label} (${rule.weight} puanlık kural)${uncertain}`, "");
    lines.push(`Ne yapılacak: ${TASKS[rule.key] ?? rule.label}`, "");
  });

  lines.push("## Kurallar", "");
  lines.push(
    `- ${repository.default_branch} dalından yeni bir dal aç ve tek bir pull request hazırla; ${repository.default_branch} dalına doğrudan yazma.`,
    "- İçeriği uydurma. README, test ve açıklamaları repository'nin gerçek koduna bakarak yaz; emin olmadığın şeyi bana sor.",
    "- Yalnızca yukarıdaki eksikleri kapat. Zaten sağlanan kurallara ve ilgisiz koda dokunma; mevcut dosyaları silme veya baştan yazma.",
    "- Eklediğin komutları ve testleri çalıştırıp doğrula; çalışmayan bir şeyi ekleme.",
    "- Gizli bilgi (anahtar, parola, .env içeriği) ekleme veya paylaşma.",
    "",
    "## Bitince",
    "",
    "Ne değiştirdiğini, hangi doğrulamaları yaptığını ve benden beklediğin kararları (ör. lisans) kısa bir listeyle özetle.",
  );
  return lines.join("\n");
}
