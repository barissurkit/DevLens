"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { GitHubPortfolioInterpretationResponse } from "../lib/types";
import { ActionsLockedPanel } from "./actions-locked-panel";
import { PortfolioInterpretationSection } from "./portfolio-interpretation-section";
import { ActionPlan } from "./action-plan";
import { AISuggestedActions } from "./ai-suggested-actions";
import { AnalysisHistory } from "./analysis-history";
import { RepositoryAnalysisSection } from "./repository-analysis-section";
import { GuidedImprovementSection } from "./guided-improvement-section";
import { PortfolioHeader } from "./portfolio-header";
import { PortfolioOverview } from "./portfolio-overview";
import { panelElementId, ResultTabs, tabElementId, type ResultTab } from "./result-tabs";

interface AnalysisResultShellProps {
  result: GitHubPortfolioInterpretationResponse;
  onReanalyze: () => void;
  /** Retries only the AI interpretation; omitted where retrying is not possible. */
  onRetryInterpretation?: () => void;
}

const ID_PREFIX = "result";

export function AnalysisResultShell({ result, onReanalyze, onRetryInterpretation }: AnalysisResultShellProps) {
  const dashboardHeadingRef = useRef<HTMLHeadingElement>(null);
  const [activeTab, setActiveTab] = useState("overview");
  const tabsRegionRef = useRef<HTMLDivElement>(null);
  const { analysis, interpretation, viewer_context } = result;
  const { aggregation, score, selection, user } = analysis;
  const isPartial = score.is_partial || aggregation.has_failures || aggregation.partial_evidence_repository_count > 0;
  const isWorkspace = viewer_context.mode === "my_workspace";
  const hasActions = viewer_context.is_owner || isWorkspace;
  const repositories = analysis.repository_analysis.repositories;

  const tabs = useMemo<ResultTab[]>(() => {
    const list: ResultTab[] = [
      { id: "overview", label: "Genel Bakış" },
      { id: "repositories", label: "Repository'ler", badge: repositories.length },
      { id: "ai", label: "AI Yorumu", warning: interpretation.status === "unavailable" ? "şu anda kullanılamıyor" : undefined },
    ];
    list.push({
      id: "actions",
      label: "Aksiyonlar",
      locked: !hasActions,
      badge: viewer_context.is_owner && result.guided_improvements.length > 0 ? result.guided_improvements.length : undefined,
    });
    return list;
  }, [hasActions, interpretation.status, repositories.length, result.guided_improvements.length, viewer_context.is_owner]);

  useEffect(() => {
    dashboardHeadingRef.current?.focus();
  }, []);

  // The tab bar is sticky, so a tab can be switched while the page is scrolled deep into another panel.
  // Bring the new panel's start into view instead of leaving the reader in the middle of it.
  function selectTab(id: string) {
    setActiveTab(id);
    const region = tabsRegionRef.current;
    if (!region || typeof window === "undefined") return;
    const stickyOffset = 53;
    const top = region.getBoundingClientRect().top + window.scrollY - stickyOffset;
    if (window.scrollY > top) window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
  }

  return (
    <section aria-labelledby="portfolio-dashboard" className="space-y-6">
      <h1 className="sr-only">@{user.username} portföy analizi</h1>
      <PortfolioHeader
        ref={dashboardHeadingRef}
        user={user}
        viewerContext={viewer_context}
        isPartial={isPartial}
        generatedAt={result.analysis_generated_at}
        cached={result.cached}
        onRefresh={onReanalyze}
      />

      <div ref={tabsRegionRef}>
        <ResultTabs tabs={tabs} activeId={activeTab} onChange={selectTab} idPrefix={ID_PREFIX} />

        <TabPanel id="overview" activeId={activeTab}>
          <PortfolioOverview analysis={analysis} />
        </TabPanel>

        <TabPanel id="repositories" activeId={activeTab}>
          <RepositoryAnalysisSection repositories={repositories} failures={analysis.repository_analysis.failures} excluded={selection.excluded} />
        </TabPanel>

        <TabPanel id="ai" activeId={activeTab}>
          <PortfolioInterpretationSection analysis={analysis} interpretation={interpretation} onRetry={onRetryInterpretation} />
        </TabPanel>

        <TabPanel id="actions" activeId={activeTab}>
          {hasActions ? (
            <>
              {viewer_context.is_owner && <GuidedImprovementSection improvements={result.guided_improvements} onReanalyze={onReanalyze} />}
              {!isWorkspace && result.guided_improvements.length === 0 && <p className="rounded-2xl border border-slate-200 bg-card p-6 text-sm text-slate-600 shadow-card">Şu an önerilen bir iyileştirme adımı yok.</p>}
              {isWorkspace && <>
                <AnalysisHistory key={`history-${user.username}`} visible={viewer_context.is_owner} />
                <AISuggestedActions key={`suggestions-${user.username}`} username={user.username} />
                <ActionPlan />
              </>}
            </>
          ) : (
            <ActionsLockedPanel />
          )}
        </TabPanel>
      </div>
    </section>
  );
}

function TabPanel({ id, activeId, children }: { id: string; activeId: string; children: React.ReactNode }) {
  return (
    <div
      role="tabpanel"
      id={panelElementId(ID_PREFIX, id)}
      aria-labelledby={tabElementId(ID_PREFIX, id)}
      hidden={id !== activeId}
      tabIndex={0}
      className="space-y-6 pt-6 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
    >
      {children}
    </div>
  );
}
