import type { Metadata } from "next";
import { InfoPage } from "../../components/info-page";
import { HowItWorks } from "../../components/landing-content";

export const metadata: Metadata = {
  title: "Nasıl çalışır? | DevLens",
  description: "DevLens bir GitHub portföyünü üç adımda, ölçülebilir kanıtlarla nasıl değerlendirir.",
  alternates: { canonical: "/nasil-calisir" },
};

export default function HowItWorksPage() {
  return <InfoPage><HowItWorks as="h1" /></InfoPage>;
}
