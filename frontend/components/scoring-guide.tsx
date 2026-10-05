import { dimensionPoints, SCORE_BANDS, SCORING_GUIDE } from "../lib/scoring-guide";

const card = "rounded-2xl border border-slate-200 bg-card p-5 shadow-card sm:p-6";
const h2 = "text-xl font-semibold tracking-tight text-slate-950 sm:text-2xl";
const DIMENSION_COLORS = ["bg-brand-700", "bg-brand-500", "bg-brand-400", "bg-brand-300"];

/** The worked example uses one rule with made-up numbers: 2 of 8 repositories have an installation section. */
const EXAMPLE = { rule: "README kurulumu", weight: 7, detected: 2, analyzed: 8 };

/** The full scoring guide: how points are earned, every rule with its weight, the bands and the limits. */
export function ScoringGuide() {
  const total = SCORING_GUIDE.reduce((sum, dimension) => sum + dimensionPoints(dimension), 0);
  const examplePoints = (EXAMPLE.weight * EXAMPLE.detected) / EXAMPLE.analyzed;

  return (
    <div className="space-y-14">
      <header className="max-w-3xl">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Puanlama nasıl çalışır?</h1>
        <p className="mt-4 text-lg leading-8 text-slate-600">
          Skor {total} puan üzerindendir ve yalnızca herkese açık repository&apos;lerde ölçülebilen kanıtlara dayanır. Kurallar herkes için aynıdır ve aşağıda eksiksiz yazılıdır; yapay zekâ skoru değiştirmez.
        </p>
      </header>

      <section aria-labelledby="split-heading" className="space-y-5">
        <h2 id="split-heading" className={h2}>{total} puan dört boyuta bölünür</h2>
        <div role="img" aria-label={SCORING_GUIDE.map((dimension) => `${dimension.label} ${dimensionPoints(dimension)} puan`).join(", ")} className="flex h-4 overflow-hidden rounded-full bg-slate-100">
          {SCORING_GUIDE.map((dimension, index) => (
            <div key={dimension.key} style={{ width: `${(dimensionPoints(dimension) / total) * 100}%` }} className={DIMENSION_COLORS[index]} />
          ))}
        </div>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {SCORING_GUIDE.map((dimension, index) => (
            <li key={dimension.key} className={card}>
              <div className="flex items-center gap-2">
                <span aria-hidden="true" className={`h-3 w-3 rounded-full ${DIMENSION_COLORS[index]}`} />
                <p className="text-sm font-semibold text-slate-950">{dimension.label}</p>
              </div>
              <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{dimensionPoints(dimension)} <span className="text-base font-medium text-slate-500">puan</span></p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{dimension.summary}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="formula-heading" className="grid gap-6 lg:grid-cols-2 lg:items-start">
        <div>
          <h2 id="formula-heading" className={h2}>Bir kural puanı nasıl kazandırır?</h2>
          <p className="mt-3 leading-7 text-slate-600">
            Her kuralın bir ağırlığı vardır. Kural, kanıtın analiz edilen repository&apos;lerin kaçında bulunduğuna göre kısmi puan verir: tamamında varsa tam puan, yarısında varsa yarım puan, hiçbirinde yoksa sıfır.
          </p>
          <p className="mt-4 rounded-xl bg-brand-50 px-4 py-3 text-sm font-semibold text-brand-800">
            kural puanı = ağırlık × (kanıtı olan repository ÷ analiz edilen repository)
          </p>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Bir boyutun puanı, kurallarının puanlarının toplamıdır ve boyut bazında en yakın tam sayıya yuvarlanır. Toplam skor dört boyutun toplamıdır.
          </p>
        </div>
        <div className={card}>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Örnek</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {EXAMPLE.analyzed} repository analiz edildi ve {EXAMPLE.detected} tanesinde kurulum bölümü var. {EXAMPLE.rule} {EXAMPLE.weight} puanlık bir kural:
          </p>
          <div role="img" aria-label={`${EXAMPLE.analyzed} repository'nin ${EXAMPLE.detected}'inde var`} className="mt-4 flex gap-1.5">
            {Array.from({ length: EXAMPLE.analyzed }, (_, index) => (
              <span key={index} className={`h-7 flex-1 rounded-md ${index < EXAMPLE.detected ? "bg-brand-600" : "bg-slate-200"}`} />
            ))}
          </div>
          <p className="mt-4 text-sm text-slate-700">
            {EXAMPLE.weight} × {EXAMPLE.detected}/{EXAMPLE.analyzed} = <strong className="font-semibold text-slate-950">{examplePoints.toLocaleString("tr-TR", { maximumFractionDigits: 2 })} puan</strong>
            <span className="text-slate-500"> ({EXAMPLE.weight} puandan)</span>
          </p>
        </div>
      </section>

      <section aria-labelledby="strength-heading" className="max-w-3xl space-y-3">
        <h2 id="strength-heading" className={h2}>Güçlü yön mü, gelişim alanı mı?</h2>
        <p className="leading-7 text-slate-600">
          Puandan ayrı olarak her kural bir yorum da üretir: kanıt repository&apos;lerin <strong className="font-semibold text-slate-900">en az yarısında</strong> varsa o kural <strong className="font-semibold text-emerald-700">güçlü yön</strong>, yarısından azında varsa <strong className="font-semibold text-amber-700">gelişim alanı</strong> olarak listelenir. Bir gelişim alanı da kısmi puan getirebilir; ikisi birbirini dışlamaz.
        </p>
      </section>

      <section aria-labelledby="rules-heading" className="space-y-6">
        <h2 id="rules-heading" className={h2}>Bütün kurallar</h2>
        {SCORING_GUIDE.map((dimension) => (
          <div key={dimension.key} className={card}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-lg font-semibold text-slate-950">{dimension.label}</h3>
              <span className="text-sm font-semibold text-brand-700">{dimensionPoints(dimension)} puan</span>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[28rem] border-collapse text-left text-sm">
                <caption className="sr-only">{dimension.label} kuralları</caption>
                <thead>
                  <tr className="border-b border-slate-200 text-xs text-slate-500">
                    <th scope="col" className="py-2 pr-4 font-medium">Kural</th>
                    <th scope="col" className="py-2 pr-4 font-medium">Neye bakılır?</th>
                    <th scope="col" className="py-2 text-right font-medium">Ağırlık</th>
                  </tr>
                </thead>
                <tbody>
                  {dimension.rules.map((rule) => (
                    <tr key={rule.key} className="border-b border-slate-100 align-top last:border-0">
                      <th scope="row" className="whitespace-nowrap py-3 pr-4 font-medium text-slate-950">{rule.label}</th>
                      <td className="py-3 pr-4 leading-6 text-slate-600">{rule.check}</td>
                      <td className="whitespace-nowrap py-3 text-right font-semibold text-slate-950">{rule.weight}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </section>

      <section aria-labelledby="bands-heading" className="space-y-5">
        <h2 id="bands-heading" className={h2}>Skor aralıkları</h2>
        <ul className="grid gap-3 md:grid-cols-3">
          {SCORE_BANDS.map((band) => (
            <li key={band.key} className={card}>
              <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${band.badge}`}>{band.label}</span>
              <p className={`mt-3 text-2xl font-semibold tracking-tight ${band.text}`}>{band.range}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{band.meaning}</p>
            </li>
          ))}
        </ul>
        <p className="max-w-3xl text-sm leading-6 text-slate-500">
          Aralıklar yalnızca okumayı kolaylaştırır; hesaplamaya girmez. Skor bir geliştiricinin yetkinliğini, kıdemini ya da işe uygunluğunu ölçmez; yalnızca herkese açık repository&apos;lerdeki dokümantasyon ve mühendislik pratiği kanıtlarını gösterir.
        </p>
      </section>

      <section aria-labelledby="limits-heading" className="max-w-3xl space-y-3">
        <h2 id="limits-heading" className={h2}>Bilmen gerekenler</h2>
        <ul className="list-disc space-y-2 pl-5 leading-7 text-slate-600">
          <li>Skor için en az iki repository&apos;nin başarıyla analiz edilmesi gerekir.</li>
          <li>Fork edilmiş ve arşivlenmiş repository&apos;ler analiz dışında kalır; özel repository&apos;ler zaten görülmez.</li>
          <li>Analiz edilemeyen ya da dosya listesi kısmen alınabilen repository&apos;ler sonuçta belirtilir; eksik görünen bir dosya aslında var olabilir.</li>
          <li>Aynı veri için skor hep aynıdır. Yalnızca &ldquo;son 12 ayda güncelleme&rdquo; kuralı, zaman geçtikçe değişebilir.</li>
          <li>Yapay zekâ yorumu bulguları açıklar ve sıradaki projeyi önerir; skoru ve kuralları değiştirmez.</li>
        </ul>
      </section>
    </div>
  );
}
