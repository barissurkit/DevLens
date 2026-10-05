"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export const NAV_LINKS: Array<{ href: string; label: string }> = [
  { href: "/nasil-calisir", label: "Nasıl çalışır" },
  { href: "/puanlama", label: "Puanlama" },
  { href: "/sss", label: "Sık sorulanlar" },
];

const focusRing = "focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2";

/** The product links of the header and footer. They are real pages, so they work from every screen. */
export function NavLinks({ variant }: { variant: "header" | "footer" }) {
  const pathname = usePathname();
  return (
    <>
      {NAV_LINKS.map((link) => {
        const current = pathname === link.href;
        const className = variant === "header"
          ? `rounded-lg px-3 py-2 text-sm font-medium transition hover:bg-slate-100 hover:text-slate-950 ${current ? "bg-slate-100 text-slate-950" : "text-slate-600"} ${focusRing}`
          : `rounded hover:text-slate-950 hover:underline ${current ? "font-medium text-slate-950" : ""} ${focusRing}`;
        const anchor = <Link href={link.href} aria-current={current ? "page" : undefined} className={className}>{link.label}</Link>;
        return variant === "footer" ? <li key={link.href}>{anchor}</li> : <span key={link.href}>{anchor}</span>;
      })}
    </>
  );
}
