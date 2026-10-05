import type { Metadata } from "next";
import { SiteShell } from "../../components/site-shell";
import { WorkspaceView } from "../../components/workspace-view";

export const metadata: Metadata = {
  title: "Çalışma alanım | DevLens",
  description: "Skor geçmişin, yapay zekâ önerilerin ve aksiyon planın.",
  robots: { index: false },
};

export default function WorkspacePage() {
  return (
    <SiteShell>
      <WorkspaceView />
    </SiteShell>
  );
}
