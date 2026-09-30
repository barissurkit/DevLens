/** Placeholder shaped like the result page, shown while a linked analysis is loading. Purely decorative. */
export function ResultSkeleton() {
  return (
    <div aria-hidden="true" className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-card p-6 shadow-card">
        <div className="flex items-center gap-5">
          <div className="skeleton h-20 w-20 shrink-0 !rounded-2xl" />
          <div className="flex-1 space-y-3">
            <div className="skeleton h-4 w-40" />
            <div className="skeleton h-7 w-2/3 max-w-sm" />
            <div className="skeleton h-4 w-1/2 max-w-xs" />
          </div>
        </div>
      </div>
      <div className="flex gap-6 border-b border-slate-200 pb-3">
        {[64, 88, 72, 76].map((width) => <div key={width} className="skeleton h-4" style={{ width }} />)}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-card p-6 shadow-card lg:col-span-2">
          <div className="flex items-center gap-6">
            <div className="skeleton h-32 w-32 shrink-0 !rounded-full" />
            <div className="flex-1 space-y-3">
              <div className="skeleton h-3 w-32" />
              <div className="skeleton h-10 w-48" />
              <div className="skeleton h-3 w-full max-w-md" />
            </div>
          </div>
          <div className="mt-6 grid gap-4 border-t border-slate-100 pt-6 md:grid-cols-3">
            {[0, 1, 2].map((item) => <div key={item} className="skeleton h-24" />)}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-card p-6 shadow-card">
          <div className="skeleton h-4 w-32" />
          <div className="mt-5 space-y-4">
            {[0, 1, 2, 3, 4].map((item) => <div key={item} className="skeleton h-4 w-full" />)}
          </div>
        </div>
      </div>
    </div>
  );
}
