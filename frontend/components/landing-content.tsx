export function HeroCopy() {
  return (
    <div className="mb-8 reveal">
      <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
        <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
        Geliştirici Portföy Analizi
      </p>
      <h1 id="landing-heading" className="text-4xl font-semibold leading-[1.1] tracking-tight text-slate-950 sm:text-5xl lg:text-5xl xl:text-[3.25rem]">
        GitHub portföyündeki kanıtları daha net gör.
      </h1>
      <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
        DevLens, herkese açık repository&apos;lerdeki dokümantasyon ve mühendislik pratiklerini inceleyerek portföyünü anlamana yardımcı olur.
      </p>
      <ul className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
        {["Giriş gerekmez", "Deterministik skor", "Saniyeler içinde sonuç"].map((item) => (
          <li key={item} className="flex items-center gap-2">
            <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4 text-emerald-600" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 8.5l3.2 3L13 4.5" /></svg>
            {item}
          </li>
        ))}
      </ul>
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
    <div aria-hidden="true" className="relative mx-auto w-full max-w-md reveal">
      <div className="absolute -inset-4 -z-10 rounded-[2rem] bg-gradient-to-br from-indigo-100 via-card to-emerald-50 blur-2xl" />
      <div className="rounded-2xl border border-slate-200 bg-card p-6 shadow-raised">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Portföy Kanıt Skoru</p>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">Örnek görünüm</span>
        </div>
        <div className="mt-5 flex items-center gap-6">
          <div className="relative h-28 w-28 shrink-0">
            <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
              <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="9" className="stroke-slate-100" />
              <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="9" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={circumference * 0.36} className="stroke-amber-500" />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-3xl font-semibold tracking-tight text-slate-950">64</span>
          </div>
          <div>
            <p className="text-sm text-slate-500">Toplam skor</p>
            <p className="text-4xl font-semibold tracking-tight text-amber-700">64 / 100</p>
            <span className="mt-1.5 inline-block rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-800">Gelişebilir</span>
          </div>
        </div>
        <div className="mt-6 space-y-3.5 border-t border-slate-100 pt-5">
          {SAMPLE_BARS.map(([label, value]) => (
            <div key={label}>
              <div className="flex justify-between text-xs"><span className="font-medium text-slate-700">{label}</span><span className="text-slate-500">{value}%</span></div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${value}%` }} /></div>
            </div>
          ))}
        </div>
        <div className="mt-5 rounded-lg bg-slate-50 px-3.5 py-3 text-xs leading-5 text-slate-600">
          <span className="font-semibold text-slate-800">Önce şunu yap:</span> Test yapısı ekle · CI iş akışı ekle
        </div>
      </div>
    </div>
  );
}

const STEPS: Array<{ title: string; text: string }> = [
  { title: "Kullanıcı adını gir", text: "Bir GitHub kullanıcı adı, @kullanici veya profil bağlantısı yeterli. Hesap açmana gerek yok." },
  { title: "Kanıtlar toplanır", text: "Herkese açık repository'ler taranır; README, test yapısı, CI ve repository hijyeni sinyalleri çıkarılır." },
  { title: "Skor ve yorum", text: "Sinyaller deterministik kurallarla puanlanır. AI yalnızca bulguları açıklar ve sıradaki projeyi önerir." },
];

const dimensionRows: Array<{ label: string; points: number; detail: string }> = [
  { label: "Dokümantasyon", points: 40, detail: "README başlığı, açıklama, kurulum, kullanım, gereksinimler ve teknolojiler." },
  { label: "Test ve Otomasyon", points: 25, detail: "Test dizini yapısı ve GitHub Actions CI iş akışı." },
  { label: "Repository Hijyeni", points: 15, detail: ".gitignore, lisans dosyası ve katkı rehberi." },
  { label: "Bakım ve Görünürlük", points: 20, detail: "Repository açıklaması, konu etiketleri ve son 12 ayda güncelleme." },
];

const FAQ: Array<{ question: string; answer: string }> = [
  { question: "Skor nasıl hesaplanıyor?", answer: "Her kural bir ağırlığa sahiptir; kuralın puanı, ağırlığı ile tespit edildiği repository oranının çarpımıdır. Toplam 100 puandır: 40 dokümantasyon, 25 test ve otomasyon, 15 repository hijyeni, 20 bakım ve görünürlük. Aynı veri ve aynı tarih için skor hep aynıdır; yalnızca \"son 12 ayda güncelleme\" kuralı zamanla değişebilir." },
  { question: "AI skoru değiştirir mi?", answer: "Hayır. AI yalnızca hesaplanmış bulguları açıklar ve bir sonraki proje için öneri sunar. AI yanıt vermediğinde bile skor ve bulgular eksiksiz görünür." },
  { question: "Özel repository'lerimi görüyor mu?", answer: "Hayır. Yalnızca herkese açık GitHub verileri analiz edilir. Fork'lar ve arşivlenmiş repository'ler kapsam dışı bırakılır." },
  { question: "Neden giriş yapmalıyım?", answer: "Analiz için gerekmez. GitHub ile giriş yaptığında kendi portföyün için skor geçmişini, yönlendirmeli iyileştirmeleri, AI önerilerini ve aksiyon planını kullanabilirsin." },
  { question: "Sonuçlar ne kadar güncel?", answer: "Sonuçlar kısa süre önbellekte tutulur ve ne zaman hesaplandığı sonuç sayfasında yazar. \"Yenile\" ile analizi baştan hesaplatabilirsin." },
];

export function FeatureStrip() {
  return (
    <div className="space-y-24">
      <section id="nasil-calisir" aria-labelledby="how-heading" className="scroll-mt-24">
        <h2 id="how-heading" className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Nasıl çalışır?</h2>
        <p className="mt-2 max-w-2xl text-slate-600">Üç adımda, tahmine değil ölçülebilir kanıta dayanan bir portföy değerlendirmesi.</p>
        <ol className="mt-8 grid gap-4 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step.title} className="rounded-2xl border border-slate-200 bg-card p-6 shadow-card">
              <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-50 text-sm font-semibold text-indigo-700">{index + 1}</span>
              <h3 className="mt-4 text-base font-semibold text-slate-950">{step.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section id="puanlama" aria-labelledby="scoring-heading" className="scroll-mt-24 grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:items-start">
        <div>
          <h2 id="scoring-heading" className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Şeffaf puanlama</h2>
          <p className="mt-3 leading-7 text-slate-600">
            Skorlar, herkese açık repository&apos;lerde ölçülebilen sinyallerden deterministik kurallarla hesaplanır. Eksik veri ve kısmi kanıt açıkça belirtilir; hangi adımın skoru ne kadar artıracağı sonuç ekranında görünür.
          </p>
          <ul className="mt-6 space-y-3 text-sm text-slate-700">
            {["AI yalnızca yorumlar; skoru veya bulguları değiştirmez.", "Aynı kanıt ve aynı tarih için skor hep aynıdır.", "AI kullanılamasa bile analiz sonucu eksiksiz görünür."].map((item) => (
              <li key={item} className="flex gap-2.5">
                <svg aria-hidden="true" viewBox="0 0 16 16" className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 8.5l3.2 3L13 4.5" /></svg>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <ul className="space-y-3">
          {dimensionRows.map((row) => (
            <li key={row.label} className="rounded-2xl border border-slate-200 bg-card p-5 shadow-card">
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="text-base font-semibold text-slate-950">{row.label}</h3>
                <span className="text-sm font-semibold text-indigo-700">{row.points} puan</span>
              </div>
              <div aria-hidden="true" className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-indigo-500" style={{ width: `${row.points}%` }} /></div>
              <p className="mt-3 text-sm leading-6 text-slate-600">{row.detail}</p>
            </li>
          ))}
        </ul>
      </section>

      <section id="sss" aria-labelledby="faq-heading" className="scroll-mt-24">
        <h2 id="faq-heading" className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Sık sorulan sorular</h2>
        <div className="mt-6 divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-card shadow-card">
          {FAQ.map((item) => (
            <details key={item.question} className="group px-5 py-4 sm:px-6">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-lg text-base font-medium text-slate-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 [&::-webkit-details-marker]:hidden">
                {item.question}
                <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-slate-500 transition group-open:rotate-180" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg>
              </summary>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
