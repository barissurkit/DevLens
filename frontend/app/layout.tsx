import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DevLens | Developer Portfolio Intelligence",
  description:
    "DevLens ile geliştirici portföylerini anlamaya yönelik yeni nesil içgörüler.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
