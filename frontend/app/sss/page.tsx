import type { Metadata } from "next";
import { InfoPage } from "../../components/info-page";
import { FaqSection } from "../../components/landing-content";

export const metadata: Metadata = {
  title: "Sık sorulan sorular | DevLens",
  description: "DevLens hakkında sık sorulan sorular: skor, yapay zekâ, gizlilik ve güncellik.",
  alternates: { canonical: "/sss" },
};

export default function FaqPage() {
  return <InfoPage><FaqSection as="h1" /></InfoPage>;
}
