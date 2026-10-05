import type { Metadata } from "next";
import { InfoPage } from "../../components/info-page";
import { ScoringGuide } from "../../components/scoring-guide";

export const metadata: Metadata = {
  title: "Puanlama | DevLens",
  description: "DevLens skoru nasıl hesaplanır: dört boyut, her kuralın ağırlığı, örnek hesap ve skor aralıkları.",
  alternates: { canonical: "/puanlama" },
};

export default function ScoringPage() {
  return <InfoPage><ScoringGuide /></InfoPage>;
}
