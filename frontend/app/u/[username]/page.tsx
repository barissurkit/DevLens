import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AnalysisForm } from "../../../components/analysis-form";
import { FeatureStrip, HeroCopy, SamplePreview } from "../../../components/landing-content";
import { SiteShell } from "../../../components/site-shell";
import { usernameFromRouteParam, userPageMetadata } from "../../../lib/share";

interface UserPageProps {
  params: Promise<{ username: string }>;
}

export async function generateMetadata({ params }: UserPageProps): Promise<Metadata> {
  const username = usernameFromRouteParam((await params).username);
  if (!username) return {};
  const { title, description, path } = userPageMetadata(username);
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { title, description, url: path, type: "website", siteName: "DevLens", locale: "tr_TR" },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default async function UserPage({ params }: UserPageProps) {
  const username = usernameFromRouteParam((await params).username);
  if (!username) redirect("/");

  return (
    <SiteShell>
      <AnalysisForm initialUsername={username} hero={<HeroCopy />} preview={<SamplePreview />} features={<FeatureStrip />} />
    </SiteShell>
  );
}
