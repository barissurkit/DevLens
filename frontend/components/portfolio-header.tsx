import { forwardRef } from "react";
import type { GitHubUser, ViewerContext } from "../lib/types";
import { portfolioModeLabel } from "../lib/presentation";
import { BadgeButton } from "./badge-button";
import { CopyLinkButton } from "./copy-link-button";
import { ReportMenu } from "./report/report-menu";
import { comparePath } from "../lib/share";
import { FreshnessNote } from "./freshness-note";

interface PortfolioHeaderProps {
  user: GitHubUser;
  viewerContext: ViewerContext;
  isPartial: boolean;
  /** ISO time the analysis was computed; the freshness line is hidden when the backend does not provide it. */
  generatedAt?: string | null;
  cached?: boolean;
  onRefresh?: () => void;
}

export const PortfolioHeader = forwardRef<HTMLHeadingElement, PortfolioHeaderProps>(function PortfolioHeader({ user, viewerContext, isPartial, generatedAt, cached = false, onRefresh }, headingRef) {
  const displayName = user.name || `@${user.username}`;
  return (
    <header className="reveal relative overflow-hidden rounded-2xl border border-slate-200 bg-card p-5 shadow-card sm:p-7">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r from-indigo-500 via-indigo-400 to-emerald-400" />
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <Avatar url={user.avatar_url} name={displayName} />
          <div className="min-w-0">
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${viewerContext.mode === "my_workspace" ? "bg-emerald-50 text-emerald-800" : "bg-indigo-50 text-indigo-700"}`}>{portfolioModeLabel(viewerContext)}</span>
            <h2 ref={headingRef} id="portfolio-dashboard" tabIndex={-1} className="mt-1.5 break-words text-2xl font-semibold tracking-tight text-slate-950 focus:outline-none sm:text-3xl">
              {displayName} portföyü
            </h2>
            <p className="mt-1 break-words text-sm text-slate-600">@{user.username} için herkese açık GitHub kanıtları incelendi.</p>
            {user.bio && <p className="mt-1 line-clamp-2 break-words text-sm text-slate-500">{user.bio}</p>}
          </div>
        </div>
        <div className="flex min-w-0 shrink-0 flex-col gap-4 sm:max-w-[30rem] sm:items-end sm:gap-3">
          <dl className="flex gap-5 text-sm">
            <Meta label="Repository" value={user.public_repos} />
            <Meta label="Takipçi" value={user.followers} />
          </dl>
          <div className="flex flex-wrap items-center gap-2 print:hidden sm:justify-end [&>*]:flex-auto sm:[&>*]:flex-none">
            <CopyLinkButton username={user.username} />
            <BadgeButton username={user.username} />
            <ReportMenu username={user.username} />
            <a href={comparePath(user.username)} className="inline-flex min-h-10 items-center justify-center whitespace-nowrap rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2">
              Karşılaştır
            </a>
            <a href={user.html_url} target="_blank" rel="noreferrer" className="inline-flex min-h-10 items-center justify-center whitespace-nowrap rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2">
              GitHub profilini aç
            </a>
          </div>
        </div>
      </div>
      {isPartial && <p className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">Bu sonuç, bazı repository verileri eksik olduğu için kısmi kanıt içerebilir.</p>}
      {generatedAt && onRefresh && <FreshnessNote generatedAt={generatedAt} cached={cached} onRefresh={onRefresh} />}
    </header>
  );
});

function Meta({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-xl font-semibold text-slate-950">{value ?? "—"}</dd>
    </div>
  );
}

function Avatar({ url, name }: { url: string | undefined; name: string }) {
  if (!url) {
    return <span aria-hidden="true" className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-xl font-semibold text-white sm:h-20 sm:w-20">{name.replace(/^@/, "").charAt(0).toUpperCase()}</span>;
  }
  // eslint-disable-next-line @next/next/no-img-element -- small external GitHub avatar; no Image optimization domain config needed
  return <img src={url} alt="" width={80} height={80} className="h-16 w-16 shrink-0 rounded-2xl border border-slate-200 bg-slate-100 object-cover sm:h-20 sm:w-20" />;
}
