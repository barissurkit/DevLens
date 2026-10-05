import type { Metadata } from "next";
import { InfoPage } from "../../components/info-page";
import { ScoringOverview } from "../../components/landing-content";

export const metadata: Metadata = {
  title: "Puanlama | DevLens",
  description: "DevLens skoru nasıl hesaplanır: dört boyut, açık ağırlıklar ve deterministik kurallar.",
  alternates: { canonical: "/puanlama" },
};

export default function ScoringPage() {
  return <InfoPage><ScoringOverview as="h1" /></InfoPage>;
}
