import { AnalysisForm } from "../components/analysis-form";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-6 py-8 sm:px-10 lg:px-12">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              aria-hidden="true"
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-sm font-semibold text-white"
            >
              D
            </div>
            <span className="text-lg font-semibold tracking-tight">DevLens</span>
          </div>
          <span className="text-right text-sm text-slate-500">Public portfolio intelligence</span>
        </header>

        <section aria-labelledby="landing-heading" className="flex flex-1 items-center py-16 sm:py-28">
          <div className="w-full min-w-0 max-w-2xl">
            <p className="mb-5 text-sm font-medium uppercase tracking-[0.18em] text-slate-500">
              Developer Portfolio Intelligence
            </p>
            <h1 id="landing-heading" className="text-4xl font-semibold tracking-tight text-slate-950 sm:text-6xl">
              GitHub portföyündeki kanıtları daha net gör.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
              DevLens, herkese açık repository&apos;lerdeki dokümantasyon ve mühendislik pratiklerini inceleyerek portföyünü anlamana yardımcı olur.
            </p>

            <div className="mt-10 w-full max-w-xl"><AnalysisForm /></div>
          </div>
        </section>

        <footer className="border-t border-slate-200 pt-5 text-sm text-slate-500">
          DevLens · İlk sürüm hazırlanıyor
        </footer>
      </div>
    </main>
  );
}
