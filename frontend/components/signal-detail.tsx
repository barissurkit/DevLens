import type { PortfolioRepositoryResult } from "../lib/types";
import { absenceMayBeIncomplete, splitRepositoriesBySignal } from "../lib/signals";

interface SignalDetailProps {
  signalKey: string;
  repositories: PortfolioRepositoryResult[];
}

/** Lists which analyzed repositories have and which lack a signal, with links to each repository. */
export function SignalDetail({ signalKey, repositories }: SignalDetailProps) {
  const split = splitRepositoriesBySignal(repositories, signalKey);
  if (!split || repositories.length === 0) return null;

  return (
    <details className="group mt-3">
      <summary className="inline-flex min-h-9 cursor-pointer list-none items-center gap-1.5 rounded-md text-xs font-medium text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2">
        <span aria-hidden="true" className="transition-transform group-open:rotate-90">›</span>
        Hangi repository&apos;lerde?
      </summary>
      <div className="mt-2 space-y-3 text-xs">
        <RepositoryGroup title="Var" tone="present" repositories={split.present} signalKey={signalKey} />
        <RepositoryGroup title="Yok" tone="missing" repositories={split.missing} signalKey={signalKey} />
      </div>
    </details>
  );
}

function RepositoryGroup({
  title,
  tone,
  repositories,
  signalKey,
}: {
  title: string;
  tone: "present" | "missing";
  repositories: PortfolioRepositoryResult[];
  signalKey: string;
}) {
  return (
    <div>
      <p className="font-semibold text-slate-700">{title} ({repositories.length})</p>
      {repositories.length === 0 ? (
        <p className="mt-1 text-slate-500">Bu gruptaki repository yok.</p>
      ) : (
        <ul className="mt-1.5 flex flex-wrap gap-1.5">
          {repositories.map((result) => {
            const incomplete = tone === "missing" && absenceMayBeIncomplete(result, signalKey);
            return (
              <li key={result.repository.html_url}>
                <a
                  href={result.repository.html_url}
                  target="_blank"
                  rel="noreferrer"
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2 ${
                    tone === "present"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800 hover:border-emerald-300"
                      : "border-amber-200 bg-amber-50 text-amber-900 hover:border-amber-300"
                  }`}
                >
                  {result.repository.name}
                  {incomplete && <span className="font-normal opacity-80">· kısmi kanıt</span>}
                </a>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
