import type { HelpEntry } from "./types";
import { HELP_REGISTRY, HELP_REGISTRY_MAP } from "./help-registry";

export function getHelpForRoute(pathname: string, tab?: string | null): HelpEntry | undefined {
  // Exact match with tab
  const withTab = tab ? `${pathname}?tab=${tab}` : pathname;
  const exact = HELP_REGISTRY_MAP.get(withTab);
  if (exact) return exact;

  // Exact match without tab (workspace-level fallback)
  const base = HELP_REGISTRY_MAP.get(pathname);
  if (base) return base;

  // Partial match: find closest entry whose path starts with pathname
  const partial = HELP_REGISTRY.find(
    (e) => pathname.startsWith(e.path) && e.path !== "/dashboard"
  );
  return partial;
}

export function getHelpById(id: string): HelpEntry | undefined {
  return HELP_REGISTRY.find((e) => e.id === id);
}

export function searchHelpEntries(query: string): HelpEntry[] {
  if (!query.trim()) return HELP_REGISTRY;
  const q = query.toLowerCase();
  return HELP_REGISTRY.filter(
    (e) =>
      e.title.toLowerCase().includes(q) ||
      e.description.toLowerCase().includes(q) ||
      e.keywords.some((k) => k.toLowerCase().includes(q)) ||
      e.module.toLowerCase().includes(q)
  );
}

export function getHelpEntriesByModule(module: string): HelpEntry[] {
  return HELP_REGISTRY.filter((e) => e.module === module);
}

export function getHelpEntriesByRole(role: string): HelpEntry[] {
  return HELP_REGISTRY.filter((e) => e.role === role);
}
