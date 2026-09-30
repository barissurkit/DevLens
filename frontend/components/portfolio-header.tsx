import { forwardRef } from "react";
import type { GitHubUser, ViewerContext } from "../lib/types";
import { portfolioModeLabel } from "../lib/presentation";

interface PortfolioHeaderProps {
  user: GitHubUser;
  viewerContext: ViewerContext;
  isPartial: boolean;
}

export const PortfolioHeader = forwardRef<HTMLHeadingElement, PortfolioHeaderProps>(function PortfolioHeader({ user, viewerContext, isPartial }, headingRef) {
  const displayName = user.name || `@${user.username}`;
  return (
    <header className="rounded-xl border border-slate-200 bg-card p-5 shadow-card sm:p-6">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <Avatar url={user.avatar_url} name={displayName} />
          <div className="min-w-0">
            <span className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">{portfolioModeLabel(viewerContext)}</span>
            <h2 ref={headingRef} id="portfolio-dashboard" tabIndex={-1} className="mt-1.5 break-words text-xl font-semibold tracking-tight text-slate-950 focus:outline-none sm:text-2xl">
              {displayName} portföyü
            </h2>
            <p className="mt-1 break-words text-sm text-slate-600">@{user.username} için herkese açık GitHub kanıtları incelendi.</p>
            {user.bio && <p className="mt-1 line-clamp-2 break-words text-sm text-slate-500">{user.bio}</p>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-6 sm:flex-col sm:items-end sm:gap-3">
          <dl className="flex gap-5 text-sm">
            <Meta label="Repository" value={user.public_repos} />
            <Meta label="Takipçi" value={user.followers} />
          </dl>
          <a href={user.html_url} target="_blank" rel="noreferrer" className="inline-flex min-h-10 items-center rounded-lg border border-slate-300 bg-card px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2">
            GitHub profilini aç
          </a>
        </div>
      </div>
      {isPartial && <p className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">Bu sonuç, bazı repository verileri eksik olduğu için kısmi kanıt içerebilir.</p>}
    </header>
  );
});

function Meta({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold text-slate-950">{value ?? "—"}</dd>
    </div>
  );
}

function Avatar({ url, name }: { url: string | undefined; name: string }) {
  if (!url) {
    return <span aria-hidden="true" className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-lg font-semibold text-white sm:h-16 sm:w-16">{name.replace(/^@/, "").charAt(0).toUpperCase()}</span>;
  }
  // eslint-disable-next-line @next/next/no-img-element -- small external GitHub avatar; no Image optimization domain config needed
  return <img src={url} alt="" width={64} height={64} className="h-14 w-14 shrink-0 rounded-full border border-slate-200 bg-slate-100 object-cover sm:h-16 sm:w-16" />;
}
