export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-6 py-8 sm:px-10 lg:px-12">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              aria-hidden="true"
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-sm font-semibold text-white"
            >
              D
            </div>
            <span className="text-lg font-semibold tracking-tight">DevLens</span>
          </div>
          <span className="text-sm text-slate-500">Yakında</span>
        </header>

        <section className="flex flex-1 items-center py-20 sm:py-28">
          <div className="max-w-2xl">
            <p className="mb-5 text-sm font-medium uppercase tracking-[0.18em] text-slate-500">
              Developer Portfolio Intelligence
            </p>
            <h1 className="text-4xl font-semibold tracking-tight text-slate-950 sm:text-6xl">
              Geliştirici portföylerine daha net bir bakış.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">
              DevLens, geliştirici çalışmalarını ve teknik üretimini anlamaya yardımcı
              olacak sade ve güçlü içgörüler için hazırlanıyor.
            </p>

            <div className="mt-10 inline-flex items-center gap-3 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-600 shadow-sm">
              <span className="h-2 w-2 rounded-full bg-amber-500" aria-hidden="true" />
              <span>Uygulama geliştirme aşamasında</span>
            </div>
          </div>
        </section>

        <footer className="border-t border-slate-200 pt-5 text-sm text-slate-500">
          DevLens · İlk sürüm hazırlanıyor
        </footer>
      </div>
    </main>
  );
}
