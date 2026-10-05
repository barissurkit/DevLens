"use client";

import Link from "next/link";
import { useCallback, useId, useRef, useState } from "react";
import type { AuthenticatedUser } from "../lib/types";
import { useDismiss } from "./use-dismiss";

export const WORKSPACE_PATH = "/calisma-alani";

/** The result page of the signed-in person's own profile, analysed as their workspace (actions unlocked). */
export function ownProfileAnalysisHref(login: string): string {
  return `/?workspace=1&username=${encodeURIComponent(login)}`;
}

const itemClass = "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 disabled:cursor-wait disabled:opacity-60";

function Avatar({ user, size }: { user: AuthenticatedUser; size: "sm" | "md" }) {
  const box = size === "sm" ? "h-9 w-9 text-sm" : "h-11 w-11 text-base";
  if (user.avatar_url) {
    // eslint-disable-next-line @next/next/no-img-element -- small external GitHub avatar
    return <img src={user.avatar_url} alt="" width={44} height={44} className={`${box} rounded-full border border-slate-200 object-cover`} />;
  }
  return <span aria-hidden="true" className={`${box} flex items-center justify-center rounded-full bg-indigo-600 font-semibold uppercase text-white`}>{user.github_login.slice(0, 1)}</span>;
}

function MenuIcon({ children }: { children: React.ReactNode }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0 text-slate-500" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{children}</svg>;
}

/**
 * The signed-in person in the top bar: the GitHub avatar opens a menu with the profile analysis, the workspace
 * and sign-out, instead of three loose buttons.
 */
export function UserMenu({ user, onLogout, busy }: { user: AuthenticatedUser; onLogout: () => void; busy: boolean }) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const close = useCallback(() => setOpen(false), []);
  useDismiss(open, close, menuRef, buttonRef);
  const name = user.display_name ?? `@${user.github_login}`;

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-label={`Hesap menüsü: ${name}`}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1.5 rounded-full p-0.5 transition hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
      >
        <Avatar user={user} size="sm" />
        <svg aria-hidden="true" viewBox="0 0 24 24" className={`mr-1 hidden h-3.5 w-3.5 text-slate-500 transition sm:block ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <div ref={menuRef} id={menuId} role="group" aria-label="Hesap menüsü" className="absolute right-0 top-full z-40 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-card p-1.5 shadow-raised">
          <div className="flex items-center gap-3 px-3 py-3">
            <Avatar user={user} size="md" />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-950">{name}</p>
              <p className="truncate text-xs text-slate-500">@{user.github_login}</p>
            </div>
          </div>
          <div className="my-1 border-t border-slate-100" />
          <a href={ownProfileAnalysisHref(user.github_login)} className={itemClass}>
            <MenuIcon><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></MenuIcon>
            Profilimi analiz et
          </a>
          <Link href={WORKSPACE_PATH} className={itemClass} onClick={close}>
            <MenuIcon><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></MenuIcon>
            Çalışma alanım
          </Link>
          {user.github_html_url && (
            <a href={user.github_html_url} target="_blank" rel="noreferrer" className={itemClass}>
              <MenuIcon><path d="M14 4h6v6M20 4l-9 9M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" /></MenuIcon>
              GitHub profilim
            </a>
          )}
          <div className="my-1 border-t border-slate-100" />
          <button type="button" onClick={onLogout} disabled={busy} className={itemClass}>
            <MenuIcon><path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4M16 8l4 4-4 4M20 12H9" /></MenuIcon>
            {busy ? "Çıkış yapılıyor…" : "Çıkış yap"}
          </button>
        </div>
      )}
    </div>
  );
}
