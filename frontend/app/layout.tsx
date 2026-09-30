import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "../components/auth-provider";
import { SITE_URL } from "../lib/share";
import { THEME_STORAGE_KEY } from "../lib/theme";

// Runs before first paint so a stored light/dark choice does not flash the wrong theme.
const THEME_INIT_SCRIPT = `try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}`;

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? SITE_URL),
  title: "DevLens | Geliştirici Portföy Analizi",
  description:
    "DevLens ile geliştirici portföylerini anlamaya yönelik yeni nesil içgörüler.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body><AuthProvider>{children}</AuthProvider></body>
    </html>
  );
}
