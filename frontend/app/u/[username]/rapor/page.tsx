import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { ReportView } from "../../../../components/report/report-view";
import { parseReportMode } from "../../../../lib/report";
import { usernameFromRouteParam } from "../../../../lib/share";

interface ReportPageProps {
  params: Promise<{ username: string }>;
  searchParams: Promise<{ tur?: string }>;
}

export async function generateMetadata({ params }: ReportPageProps): Promise<Metadata> {
  const username = usernameFromRouteParam((await params).username);
  return {
    title: username ? `@${username} portföy raporu | DevLens` : "Portföy raporu | DevLens",
    description: "GitHub portföy analizinin yazdırılabilir raporu.",
    robots: { index: false },
  };
}

export default async function ReportPage({ params, searchParams }: ReportPageProps) {
  const username = usernameFromRouteParam((await params).username);
  if (!username) redirect("/");
  const mode = parseReportMode((await searchParams).tur);
  return <ReportView username={username} mode={mode} />;
}
