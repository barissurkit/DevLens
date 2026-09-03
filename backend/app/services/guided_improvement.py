from dataclasses import dataclass

from app.schemas.analysis import GitHubPortfolioAnalysis, ViewerContext
from app.schemas.guided_improvement import (
    GuidedImprovement,
    GuidedImprovementState,
    GuidedImprovementVerification,
)
from app.services.portfolio_scoring import (
    PORTFOLIO_SCORING_DIMENSIONS,
    is_portfolio_rule_passing,
)


@dataclass(frozen=True, slots=True)
class GuidedImprovementDefinition:
    title: str
    why: str
    steps: tuple[str, ...]


GUIDED_IMPROVEMENT_REGISTRY: dict[str, GuidedImprovementDefinition] = {
    "readme_exists": GuidedImprovementDefinition("README ekle", "README, repository'nin amacını ve nasıl kullanılacağını hızlıca anlaşılır kılar.", ("Repository köküne bir README.md dosyası ekleyin.", "Projenin amacını ve temel özelliklerini açıklayın.", "Kurulum ve kullanım adımlarını belgeleyin.")),
    "readme_title": GuidedImprovementDefinition("README başlığını netleştir", "Açık bir başlık, projenin ne olduğunu ilk bakışta anlaşılır hale getirir.", ("README'nin başına projenin adını içeren bir başlık ekleyin.", "Başlığın repository içeriğiyle uyumlu olduğundan emin olun.")),
    "readme_description": GuidedImprovementDefinition("README açıklamasını güçlendir", "Kısa ve somut bir açıklama, değerlendirene projenin amacını hızlıca aktarır.", ("Projenin hangi problemi çözdüğünü açıklayın.", "Ana kullanım senaryosunu ve önemli özellikleri birkaç cümleyle belirtin.")),
    "readme_installation": GuidedImprovementDefinition("Kurulum adımlarını belgele", "Tekrarlanabilir kurulum talimatları, projenin denenmesini ve yeniden kurulmasını kolaylaştırır.", ("Gereken bağımlılıkları ve ön koşulları listeleyin.", "Kurulum komutlarını çalıştırılabilir sırayla ekleyin.")),
    "readme_usage": GuidedImprovementDefinition("Kullanım örneği ekle", "Kullanım talimatları, projenin beklenen giriş ve çıktılarının anlaşılmasını sağlar.", ("Uygulamayı veya ana komutu nasıl çalıştıracağınızı açıklayın.", "En az bir temsilî kullanım örneği ve beklenen çıktıyı ekleyin.")),
    "readme_technologies": GuidedImprovementDefinition("Kullanılan teknolojileri açıkla", "Teknoloji bilgisi, projenin teknik yaklaşımını ve temel bağımlılıklarını görünür kılar.", ("Kullanılan ana framework, kütüphane ve servisleri listeleyin.", "Her teknolojinin projedeki rolünü kısa bir ifadeyle belirtin.")),
    "readme_requirements": GuidedImprovementDefinition("Gereksinimleri belgele", "Açık gereksinimler, projeyi çalıştırmak için gereken ortamın doğru kurulmasına yardımcı olur.", ("Dil, runtime ve sürüm gereksinimlerini belirtin.", "Gerekli environment variable veya harici servisleri açıklayın.")),
    "tests_structure": GuidedImprovementDefinition("Test yapısı ekle", "Testler, davranışın korunmasına ve değişikliklerin güvenle doğrulanmasına yardımcı olur.", ("Ana davranışlar için düzenli bir test dizini veya test modülü oluşturun.", "Başarılı senaryoların yanında önemli hata durumlarını da test edin.")),
    "ci_workflow": GuidedImprovementDefinition("CI iş akışı ekle", "CI, test ve kalite kontrollerinin her değişiklikte tekrarlanabilir biçimde çalışmasını sağlar.", (".github/workflows altında bir CI workflow tanımlayın.", "Bağımlılık kurulumu, test ve mevcut kalite kontrollerini workflow'a ekleyin.")),
    "gitignore": GuidedImprovementDefinition(".gitignore dosyasını düzenle", ".gitignore, üretilen dosyaların ve yerel makineye özgü içeriklerin repository'ye girmesini önler.", ("Kullandığınız dil ve araçlara uygun bir .gitignore dosyası ekleyin.", "Build çıktıları, cache'ler ve yerel environment dosyalarını hariç tutun.")),
    "license": GuidedImprovementDefinition("Lisans bilgisi ekle", "Lisans, başkalarının repository'yi hangi koşullarda kullanabileceğini açıkça belirtir.", ("Projenizin kullanım koşullarına uygun bir lisans seçin.", "Lisans dosyasını repository köküne ekleyin ve README'de referans verin.")),
    "contributing": GuidedImprovementDefinition("Katkı rehberi ekle", "Katkı rehberi, başkalarının projeye nasıl güvenli ve tutarlı katkı yapacağını açıklar.", ("Katkı, issue ve pull request sürecini açıklayan bir CONTRIBUTING dosyası ekleyin.", "Geliştirme ortamı, test ve kod biçimlendirme beklentilerini belirtin.")),
}


def canonical_guided_rule_keys() -> set[str]:
    return {rule.key for dimension in PORTFOLIO_SCORING_DIMENSIONS for rule in dimension.rules}


def build_guided_improvements(
    analysis: GitHubPortfolioAnalysis,
    viewer_context: ViewerContext,
) -> list[GuidedImprovement]:
    if not viewer_context.is_owner or viewer_context.mode != "my_workspace":
        return []
    if not analysis.score.is_available or analysis.score.is_partial:
        return []

    improvements: list[GuidedImprovement] = []
    for dimension in analysis.score.dimensions:
        for rule in dimension.rules:
            definition = GUIDED_IMPROVEMENT_REGISTRY.get(rule.key)
            if definition is None or is_portfolio_rule_passing(
                detected_repository_count=rule.detected_repository_count,
                analyzed_repository_count=rule.analyzed_repository_count,
            ):
                continue
            improvements.append(
                GuidedImprovement(
                    rule_key=rule.key,
                    title=definition.title,
                    why=definition.why,
                    steps=list(definition.steps),
                    verification=GuidedImprovementVerification(
                        detected_repository_count=rule.detected_repository_count,
                        analyzed_repository_count=rule.analyzed_repository_count,
                        current_state=GuidedImprovementState.NEEDS_IMPROVEMENT,
                        analysis_available=analysis.score.is_available,
                        analysis_partial=analysis.score.is_partial,
                        reanalysis_required=True,
                    ),
                )
            )
    return improvements
