import Link from "next/link";
import type { PortfolioScoreDimensionResult, PortfolioScoreRuleResult } from "../lib/types";
import { SCORE_MODERATE_MIN, SCORE_STRONG_MIN } from "../lib/presentation";

interface ScoreMethodologyProps {
  dimensions: PortfolioScoreDimensionResult[];
  scoredRepositoryCount: number;
}

const formatPoints = (value: number) => value.toLocaleString("tr-TR", { maximumFractionDigits: 1 });

/** Unrounded points a rule contributes: its weight times the share of analyzed repositories that have the signal. */
export function rulePoints(rule: PortfolioScoreRuleResult): number {
  return rule.analyzed_repository_count > 0
    ? (rule.weight * rule.detected_repository_count) / rule.analyzed_repository_count
    : 0;
}

/** A rule is a strength when the signal is in at least half of the analyzed repositories (the backend policy). */
export function isStrength(rule: PortfolioScoreRuleResult): boolean {
  return rule.analyzed_repository_count > 0 && rule.detected_repository_count * 2 >= rule.analyzed_repository_count;
}

/** Picks a rule that is present in some but not all repositories, so the worked example is instructive. */
function pickExampleRule(dimensions: PortfolioScoreDimensionResult[]): PortfolioScoreRuleResult | null {
  const rules = dimensions.flatMap((dimension) => dimension.rules);
  return rules.find((rule) => rule.detected_repository_count > 0 && rule.detected_repository_count < rule.analyzed_repository_count) ?? null;
}

export function ScoreMethodology({ dimensions, scoredRepositoryCount }: ScoreMethodologyProps) {
  const example = pickExampleRule(dimensions);
  const totalPossible = dimensions.reduce((sum, dimension) => sum + dimension.points_possible, 0);

  return (
    <details className="group mt-6 rounded-lg border border-slate-200 bg-slate-50">
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 rounded-lg px-4 text-sm font-medium text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2">
        <span>Skor nasıl hesaplanır?</span>
        <span aria-hidden="true" className="text-lg leading-none text-slate-500 transition-transform group-open:rotate-90">›</span>
      </summary>
      <div className="space-y-5 border-t border-slate-200 px-4 py-4 text-sm leading-6 text-slate-700">
        <p>
          Skor {totalPossible > 0 ? `${totalPossible} ` : "100 "}puan üzerinden hesaplanır. Her kural, o sinyalin analiz edilen
          repository&apos;lerin kaçında bulunduğuna göre ağırlığı kadar puan verir:{" "}
          <strong className="font-semibold text-slate-950">ağırlık × (sinyali olan repository / analiz edilen repository)</strong>.
        </p>
        {example && (
          <p className="rounded-md bg-card px-3 py-2 ring-1 ring-slate-200">
            <span className="font-medium text-slate-950">Örnek:</span> {example.label} ({example.weight} puan)
            {" "}{example.analyzed_repository_count} repository&apos;nin {example.detected_repository_count}&apos;inde var →{" "}
            {example.weight} × {example.detected_repository_count}/{example.analyzed_repository_count} ≈{" "}
            <strong className="font-semibold text-slate-950">{formatPoints(rulePoints(example))} puan</strong>.
          </p>
        )}

        {dimensions.length > 0 && (
          <div className="space-y-4">
            {dimensions.map((dimension) => (
              <div key={dimension.key} className="overflow-x-auto">
                <table className="w-full min-w-[20rem] border-collapse text-left">
                  <caption className="pb-1.5 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                    {dimension.label} · {dimension.points_earned} / {dimension.points_possible} puan
                  </caption>
                  <thead>
                    <tr className="border-b border-slate-200 text-xs text-slate-500">
                      <th scope="col" className="py-1.5 pr-3 font-medium">Kural</th>
                      <th scope="col" className="py-1.5 pr-3 font-medium">Sinyali olan repository</th>
                      <th scope="col" className="py-1.5 pr-3 font-medium">Durum</th>
                      <th scope="col" className="py-1.5 text-right font-medium">Puan</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dimension.rules.map((rule) => (
                      <tr key={rule.key} className="border-b border-slate-100 last:border-0">
                        <th scope="row" className="py-1.5 pr-3 font-normal text-slate-800">{rule.label}</th>
                        <td className="py-1.5 pr-3 text-slate-600">{rule.detected_repository_count} / {rule.analyzed_repository_count}</td>
                        <td className={`py-1.5 pr-3 text-xs font-medium ${isStrength(rule) ? "text-emerald-700" : "text-amber-700"}`}>{isStrength(rule) ? "Güçlü yön" : "Gelişim alanı"}</td>
                        <td className="py-1.5 text-right font-medium text-slate-900">{formatPoints(rulePoints(rule))} / {rule.weight}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
            <p className="text-xs leading-5 text-slate-500">
              Puanlar boyut bazında toplanıp yuvarlanır; bu yüzden satırlardaki ondalıklı puanların toplamı, yukarıda gösterilen tam sayıdan küçük farklarla ayrışabilir.
            </p>
          </div>
        )}

        <p>
          Bir sinyal repository&apos;lerin en az yarısında varsa güçlü yön, yarısından azında varsa gelişim alanı sayılır; gelişim alanları da kısmi puan getirebilir.{" "}
          <Link href="/puanlama" className="font-semibold text-brand-700 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600">Bütün kuralları ve ağırlıkları gör →</Link>
        </p>

        <ul className="list-disc space-y-1.5 pl-5">
          <li>Skor için en az iki repository&apos;nin başarıyla analiz edilmesi gerekir{scoredRepositoryCount > 0 ? ` (bu skor ${scoredRepositoryCount} repository üzerinden hesaplandı)` : ""}.</li>
          <li>Fork edilmiş ve arşivlenmiş repository&apos;ler analiz dışında tutulur.</li>
          <li>Yapay zekâ yorumu skoru ve bulguları değiştirmez; yalnızca açıklar.</li>
          <li>
            Renk bantları: {SCORE_STRONG_MIN} ve üzeri <strong className="font-semibold text-emerald-700">Güçlü</strong>,{" "}
            {SCORE_MODERATE_MIN}–{SCORE_STRONG_MIN - 1} <strong className="font-semibold text-amber-700">Gelişebilir</strong>,{" "}
            {SCORE_MODERATE_MIN} altı <strong className="font-semibold text-rose-700">Zayıf</strong>.
          </li>
        </ul>
      </div>
    </details>
  );
}
