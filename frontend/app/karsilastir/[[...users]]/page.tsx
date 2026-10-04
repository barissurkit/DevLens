import type { Metadata } from "next";
import { ComparisonView } from "../../../components/comparison-view";
import { SiteShell } from "../../../components/site-shell";
import { usernameFromRouteParam } from "../../../lib/share";

interface ComparePageProps {
  params: Promise<{ users?: string[] }>;
}

function logins(segments: string[] | undefined): [string | undefined, string | undefined] {
  const [first, second] = segments ?? [];
  return [first ? usernameFromRouteParam(first) ?? undefined : undefined, second ? usernameFromRouteParam(second) ?? undefined : undefined];
}

export async function generateMetadata({ params }: ComparePageProps): Promise<Metadata> {
  const [first, second] = logins((await params).users);
  const title = first && second ? `@${first} ve @${second} portföy karşılaştırması | DevLens` : "Portföy karşılaştırma | DevLens";
  return {
    title,
    description: "İki herkese açık GitHub portföyünü aynı deterministik kurallarla puanlayıp yan yana karşılaştır.",
    robots: { index: false },
  };
}

export default async function ComparePage({ params }: ComparePageProps) {
  const [first, second] = logins((await params).users);
  return (
    <SiteShell>
      <ComparisonView a={first} b={first ? second : undefined} />
    </SiteShell>
  );
}
