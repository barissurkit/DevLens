import { AnalysisForm } from "../components/analysis-form";
import { AuthControls } from "../components/auth-controls";
import { FeatureStrip, HeroCopy, SamplePreview } from "../components/landing-content";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div
              aria-hidden="true"
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-sm font-semibold text-white"
            >
              D
            </div>
            <span className="text-lg font-semibold tracking-tight text-slate-950">DevLens</span>
            <span className="hidden rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 sm:inline">Herkese Açık Portföy Analizi</span>
          </div>
          <AuthControls />
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <AnalysisForm hero={<HeroCopy />} preview={<SamplePreview />} features={<FeatureStrip />} />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto w-full max-w-6xl px-4 py-5 text-sm text-slate-500 sm:px-6 lg:px-8">
          DevLens · Herkese açık GitHub verilerinden kanıta dayalı portföy analizi
        </div>
      </footer>
    </div>
  );
}
