import type { GitHubPortfolioAnalysis } from "../lib/types";
import { scoreTone } from "../lib/presentation";
import { BrandMark } from "./brand-mark";

const dateFormatter = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul" });

interface PrintCoverProps {
  analysis: GitHubPortfolioAnalysis;
  /** ISO time the analysis was computed; the current time is used when the backend does not send it. */
  generatedAt?: string | null;
  /** Address of the shareable result page. */
  url: string;
}

/**
 * The first page of a printed report: logo, title, who it is about, the score and where it came from.
 * It is invisible on screen and forces the content to start on the second page when printed.
 */
export function PrintCover({ analysis, generatedAt, url }: PrintCoverProps) {
  const { user, score } = analysis;
  const date = generatedAt && !Number.isNaN(Date.parse(generatedAt)) ? new Date(generatedAt) : new Date();
  const hasScore = score.is_available && score.overall_score !== null;
  const tone = hasScore ? scoreTone(score.overall_score as number) : null;
  const displayName = user.name || `@${user.username}`;

  return (
    <section aria-hidden="true" className="print-cover hidden print:flex">
      <div className="flex items-center gap-4">
        <BrandMark className="h-16 w-16" idPrefix="cover" />
        <p className="text-4xl font-semibold tracking-tight text-slate-950">Dev<span className="text-brand-700">Lens</span></p>
      </div>

      <div className="mt-auto">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-700">Portföy Analiz Raporu</p>
        <h1 className="mt-4 text-5xl font-semibold leading-tight tracking-tight text-slate-950">{displayName}</h1>
        <p className="mt-2 text-xl text-slate-600">@{user.username}</p>

        {hasScore && tone && (
          <div className="mt-12 flex items-end gap-6">
            <p className={`text-8xl font-semibold leading-none tracking-tight ${tone.text}`}>{score.overall_score}<span className="text-3xl text-slate-500"> / 100</span></p>
            <span className={`mb-2 rounded-full px-4 py-1.5 text-base font-semibold ${tone.badge}`}>{tone.label}</span>
          </div>
        )}

        {score.dimensions.length > 0 && (
          <ul className="mt-10 max-w-xl space-y-3">
            {score.dimensions.map((dimension) => (
              <li key={dimension.key}>
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-slate-800">{dimension.label}</span>
                  <span className="text-slate-600">{dimension.points_earned} / {dimension.points_possible}</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-slate-200"><div className="h-2 rounded-full bg-brand-600" style={{ width: `${dimension.score}%` }} /></div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-auto border-t border-slate-300 pt-6 text-sm leading-6 text-slate-600">
        <p><span className="font-semibold text-slate-800">Oluşturulma:</span> {dateFormatter.format(date)}</p>
        <p><span className="font-semibold text-slate-800">Kaynak:</span> {url}</p>
        <p className="mt-3 text-xs text-slate-500">
          Skor, herkese açık GitHub repository&apos;lerindeki ölçülebilir sinyallere dayanır ve deterministik kurallarla hesaplanır. Bir geliştiricinin yetkinliğinin tamamını ölçmez.
        </p>
      </div>
    </section>
  );
}
