import { AnalysisForm } from "../components/analysis-form";
import { FeatureStrip, HeroCopy, SamplePreview } from "../components/landing-content";
import { SiteShell } from "../components/site-shell";

export default function Home() {
  return (
    <SiteShell>
      <AnalysisForm hero={<HeroCopy />} preview={<SamplePreview />} features={<FeatureStrip />} />
    </SiteShell>
  );
}
