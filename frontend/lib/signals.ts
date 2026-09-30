import type { PortfolioRepositoryResult } from "./types";

type SignalReader = (repository: PortfolioRepositoryResult) => boolean;

const SIGNAL_READERS: Record<string, SignalReader> = {
  readme_exists: (r) => r.analysis.readme.exists,
  readme_title: (r) => r.analysis.readme.has_title,
  readme_description: (r) => r.analysis.readme.has_description,
  readme_installation: (r) => r.analysis.readme.has_installation,
  readme_usage: (r) => r.analysis.readme.has_usage,
  readme_technologies: (r) => r.analysis.readme.has_technologies,
  readme_requirements: (r) => r.analysis.readme.has_requirements,
  tests_structure: (r) => r.analysis.structure.has_tests,
  ci_workflow: (r) => r.analysis.structure.has_ci,
  gitignore: (r) => r.analysis.structure.has_gitignore,
  license: (r) => r.analysis.structure.has_license,
  contributing: (r) => r.analysis.structure.has_contributing,
};

/** Signals derived from the repository file tree; a truncated tree can hide them. */
const STRUCTURE_SIGNALS = new Set(["tests_structure", "ci_workflow", "gitignore", "license", "contributing"]);

export function isKnownSignal(key: string): boolean {
  return key in SIGNAL_READERS;
}

/** Whether the repository shows the signal, or null for an unknown signal key. */
export function repositoryHasSignal(repository: PortfolioRepositoryResult, key: string): boolean | null {
  const reader = SIGNAL_READERS[key];
  return reader ? reader(repository) : null;
}

/** True when the signal is absent but the repository tree was truncated, so it may exist unseen. */
export function absenceMayBeIncomplete(repository: PortfolioRepositoryResult, key: string): boolean {
  return STRUCTURE_SIGNALS.has(key) && repository.analysis.tree_truncated;
}

export interface SignalSplit {
  present: PortfolioRepositoryResult[];
  missing: PortfolioRepositoryResult[];
}

export function splitRepositoriesBySignal(repositories: PortfolioRepositoryResult[], key: string): SignalSplit | null {
  if (!isKnownSignal(key)) return null;
  const present: PortfolioRepositoryResult[] = [];
  const missing: PortfolioRepositoryResult[] = [];
  for (const repository of repositories) {
    (repositoryHasSignal(repository, key) ? present : missing).push(repository);
  }
  return { present, missing };
}
