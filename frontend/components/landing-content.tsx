export function HeroCopy() {
  return (
    <div className="mb-8">
      <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
        Geliştirici Portföy Analizi
      </p>
      <h1 id="landing-heading" className="text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
        GitHub portföyündeki kanıtları daha net gör.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
        DevLens, herkese açık repository&apos;lerdeki dokümantasyon ve mühendislik pratiklerini inceleyerek portföyünü anlamana yardımcı olur.
      </p>
    </div>
  );
}

const SAMPLE_BARS: Array<[string, number]> = [
  ["Dokümantasyon", 78],
  ["Test ve Otomasyon", 46],
  ["Repository Hijyeni", 68],
];

/** Static, decorative illustration of the result screen. It shows made-up numbers and is labelled as a sample. */
export function SamplePreview() {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  return (
    <div aria-hidden="true" className="relative mx-auto w-full max-w-md">
      <div className="absolute -inset-4 -z-10 rounded-3xl bg-gradient-to-br from-indigo-100 via-card to-slate-100 blur-2xl" />
      <div className="rounded-xl border border-slate-200 bg-card p-5 shadow-raised">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Portföy Kanıt Skoru</p>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">Örnek görünüm</span>
        </div>
        <div className="mt-4 flex items-center gap-5">
          <svg viewBox="0 0 100 100" className="h-24 w-24 shrink-0 -rotate-90">
            <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="9" className="stroke-slate-100" />
            <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="9" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={circumference * 0.36} className="stroke-amber-500" />
          </svg>
          <div>
            <p className="text-4xl font-semibold tracking-tight text-amber-700">64 / 100</p>
            <span className="mt-1 inline-block rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-800">Gelişebilir</span>
          </div>
        </div>
        <div className="mt-5 space-y-3 border-t border-slate-100 pt-5">
          {SAMPLE_BARS.map(([label, value]) => (
            <div key={label}>
              <div className="flex justify-between text-xs"><span className="font-medium text-slate-700">{label}</span><span className="text-slate-500">{value}%</span></div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${value}%` }} /></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const FEATURES: Array<{ title: string; text: string }> = [
  { title: "Kanıta dayalı puanlama", text: "Skorlar, herkese açık repository'lerde ölçülebilen sinyallerden deterministik kurallarla hesaplanır." },
  { title: "AI yalnızca yorumlar", text: "Gemini kanıtları açıklar ve bir sonraki projeyi önerir; skorları veya bulguları değiştirmez." },
  { title: "Şeffaf sınırlar", text: "Eksik veri ve kısmi kanıt açıkça belirtilir; AI kullanılamasa bile analiz sonucu görünür." },
];

export function FeatureStrip() {
  return (
    <ul className="grid gap-4 sm:grid-cols-3">
      {FEATURES.map((feature) => (
        <li key={feature.title} className="rounded-xl border border-slate-200 bg-card p-5 shadow-card">
          <h2 className="text-sm font-semibold text-slate-950">{feature.title}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{feature.text}</p>
        </li>
      ))}
    </ul>
  );
}
