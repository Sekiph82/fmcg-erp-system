"use client";

import {
  useState, useEffect, useRef, useCallback, useMemo,
  KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { NAV_CONFIG, NavSection, NavStandaloneLink } from "./nav-config";
import { ACTION_REGISTRY, filterActions, PaletteAction } from "@/lib/actionRegistry";
import { apiClient } from "@/lib/api";
import { RecentItem } from "@/hooks/useCommandPalette";

// ── Types ──────────────────────────────────────────────────────────────────────

interface NavResult {
  type: "nav";
  id: string;
  label: string;
  subtitle: string;
  href: string;
  icon?: React.ReactNode;
}

interface RecordResult {
  type: "record";
  id: string;
  label: string;
  subtitle: string;
  href: string;
  recordType: string;
}

type Result = NavResult | RecordResult | PaletteAction;

interface Props {
  open: boolean;
  onClose: () => void;
  onVisit: (item: Omit<RecentItem, "ts">) => void;
  recent: RecentItem[];
}

// ── Icon map for record types ─────────────────────────────────────────────────

const RECORD_ICONS: Record<string, string> = {
  customer: "👤",
  supplier: "🏢",
  product: "📦",
  material: "🧪",
  sales_order: "🛒",
  purchase_order: "📋",
  invoice: "📄",
};

const CAT_ICONS: Record<string, string> = {
  navigation: "🗺️",
  action: "⚡",
  report: "📊",
  ai: "🧠",
  record: "🔍",
};

const CAT_LABEL: Record<string, string> = {
  navigation: "Navigation",
  action: "Actions",
  report: "Reports",
  ai: "AI Commands",
  record: "Records",
};

// ── Fuzzy match ──────────────────────────────────────────────────────────────

function fuzzyMatch(text: string, query: string): boolean {
  if (!query) return true;
  const t = text.toLowerCase();
  const q = query.toLowerCase();
  if (t.includes(q)) return true;
  let ti = 0;
  for (let qi = 0; qi < q.length; qi++) {
    const idx = t.indexOf(q[qi], ti);
    if (idx === -1) return false;
    ti = idx + 1;
  }
  return true;
}

// ── Build nav index from NAV_CONFIG ──────────────────────────────────────────

function buildNavResults(
  query: string,
  hasPermission: (code: string) => boolean,
): NavResult[] {
  const results: NavResult[] = [];
  const q = query.toLowerCase();

  for (const entry of NAV_CONFIG) {
    if (entry.type === "cluster-header") continue;

    if (entry.type === "link") {
      const e = entry as NavStandaloneLink;
      if (e.permission && !hasPermission(e.permission)) continue;
      if (!q || fuzzyMatch(e.label, q)) {
        results.push({ type: "nav", id: e.id, label: e.label, subtitle: "Dashboard", href: e.href });
      }
      continue;
    }

    if (entry.type === "section") {
      const sec = entry as NavSection;
      if (sec.permission && !hasPermission(sec.permission)) continue;

      // Section matches — add section link and top items
      const secMatches = !q || fuzzyMatch(sec.label, q);

      for (const item of sec.items) {
        if (item.permission && !hasPermission(item.permission)) continue;
        if (secMatches || fuzzyMatch(item.label, q)) {
          results.push({
            type: "nav",
            id: `${sec.id}-${item.label}`,
            label: item.label,
            subtitle: sec.label,
            href: item.href,
          });
          if (results.length >= 40) break;
        }
      }
    }
  }

  return results.slice(0, query ? 8 : 6);
}

// ── Command Palette component ─────────────────────────────────────────────────

export function CommandPalette({ open, onClose, onVisit, recent }: Props) {
  const [query, setQuery] = useState("");
  const [recordResults, setRecordResults] = useState<RecordResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();
  const { hasPermission } = useAuth();

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setRecordResults([]);
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  // Fetch records with debounce
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length < 2) { setRecordResults([]); return; }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await apiClient.get<{ records: RecordResult[] }>("/api/v1/search/", {
          params: { q: query, limit: 6 },
        });
        setRecordResults(res.data.records ?? []);
      } catch {
        setRecordResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query]);

  // Build result groups
  const { allResults, groups } = useMemo(() => {
    const q = query.trim();

    // No query → show recent
    if (!q) {
      const recentResults: NavResult[] = recent.map((r) => ({
        type: "nav" as const,
        id: r.href,
        label: r.label,
        subtitle: r.subtitle ?? "Recent",
        href: r.href,
      }));
      return {
        allResults: recentResults as Result[],
        groups: recentResults.length > 0
          ? [{ category: "recent", label: "Recent", items: recentResults as Result[] }]
          : [],
      };
    }

    const navItems = buildNavResults(q, hasPermission);
    const actions = filterActions(ACTION_REGISTRY, q, hasPermission).slice(0, 5);
    const records = recordResults.map((r) => ({ ...r, type: "record" as const }));

    const groupList = [
      navItems.length > 0   && { category: "navigation", label: "Navigation",  items: navItems as Result[] },
      actions.length > 0    && { category: "action",     label: "Actions",     items: actions as Result[] },
      records.length > 0    && { category: "record",     label: "Records",     items: records as Result[] },
    ].filter(Boolean) as { category: string; label: string; items: Result[] }[];

    const all = groupList.flatMap((g) => g.items);
    return { allResults: all, groups: groupList };
  }, [query, recordResults, recent, hasPermission]);

  // Reset selection when results change
  useEffect(() => { setSelectedIdx(0); }, [allResults.length, query]);

  // Scroll selected item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${selectedIdx}"]`) as HTMLElement | null;
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIdx]);

  const navigate = useCallback((result: Result) => {
    const href = (result as NavResult).href ?? (result as PaletteAction).href;
    if (!href) return;
    onVisit({ label: result.label, href, subtitle: (result as NavResult).subtitle ?? (result as PaletteAction).description });
    onClose();
    router.push(href);
  }, [onClose, onVisit, router]);

  const handleKey = useCallback((e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, allResults.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (allResults[selectedIdx]) navigate(allResults[selectedIdx]);
    } else if (e.key === "Escape") {
      onClose();
    }
  }, [allResults, selectedIdx, navigate, onClose]);

  if (!open) return null;

  const globalIdx = (groupItems: Result[], offset: number) =>
    allResults.indexOf(groupItems[0]) + offset;

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-start justify-center pt-[10vh] px-4"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Panel */}
      <div
        className="relative w-full max-w-2xl rounded-2xl overflow-hidden shadow-2xl"
        style={{
          background: "rgba(5, 18, 35, 0.92)",
          border: "1px solid rgba(0, 212, 255, 0.18)",
          boxShadow: "0 0 0 1px rgba(0,212,255,0.08), 0 32px 64px -12px rgba(0,0,0,0.8), 0 0 40px rgba(0,212,255,0.06)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/[0.08]">
          <svg className="h-4.5 w-4.5 shrink-0 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Search modules, actions, records…"
            className="flex-1 bg-transparent text-[15px] text-slate-100 placeholder:text-slate-500 outline-none"
            autoComplete="off"
            spellCheck={false}
          />
          {loading && (
            <div className="h-3.5 w-3.5 rounded-full border-2 border-cyan-500/40 border-t-cyan-400 animate-spin shrink-0" />
          )}
          <kbd className="hidden sm:flex items-center gap-0.5 shrink-0 text-[10px] text-slate-600 font-mono bg-white/[0.05] rounded px-1.5 py-0.5 border border-white/[0.07]">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[420px] overflow-y-auto overscroll-contain py-1">
          {groups.length === 0 && query.trim() && !loading && (
            <div className="px-4 py-10 text-center text-sm text-slate-500">
              No results for <span className="text-slate-300 font-medium">"{query}"</span>
            </div>
          )}

          {groups.length === 0 && !query.trim() && (
            <div className="px-4 py-8 text-center text-sm text-slate-500">
              Type to search modules, actions, records…
              <div className="mt-2 text-xs text-slate-600">↑↓ navigate · Enter select · Esc close</div>
            </div>
          )}

          {groups.map((group) => {
            const startOffset = allResults.indexOf(group.items[0]);
            return (
              <div key={group.category}>
                {/* Group header */}
                <div className="flex items-center gap-2 px-4 pt-3 pb-1">
                  <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                    {group.category === "recent" ? "Recent" : CAT_LABEL[group.category] ?? group.label}
                  </span>
                  {group.category !== "recent" && (
                    <span className="text-slate-700 text-[10px]">{CAT_ICONS[group.category]}</span>
                  )}
                </div>

                {/* Items */}
                {group.items.map((item, i) => {
                  const absIdx = startOffset + i;
                  const isSelected = selectedIdx === absIdx;
                  const href = (item as NavResult).href ?? (item as PaletteAction).href ?? "";
                  const subtitle = (item as NavResult).subtitle
                    ?? (item as PaletteAction).description
                    ?? "";
                  const iconStr = (item as PaletteAction).icon
                    ?? RECORD_ICONS[(item as RecordResult).recordType ?? ""]
                    ?? (item.type === "nav" || item.type === "record" ? "🗺️" : "⚡");

                  return (
                    <button
                      key={item.id ?? href}
                      data-idx={absIdx}
                      onClick={() => navigate(item)}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                        isSelected
                          ? "bg-cyan-500/[0.12] text-white"
                          : "text-slate-300 hover:bg-white/[0.04] hover:text-white"
                      }`}
                    >
                      {/* Icon */}
                      <span className="text-base shrink-0 w-6 text-center select-none">{iconStr}</span>

                      {/* Text */}
                      <div className="flex-1 min-w-0">
                        <div className="text-[13.5px] font-medium truncate">{item.label}</div>
                        {subtitle && (
                          <div className="text-[11px] text-slate-500 truncate mt-0.5">{subtitle}</div>
                        )}
                      </div>

                      {/* Category badge */}
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border shrink-0 ${
                        item.type === "nav" || item.type === "record"
                          ? "text-slate-600 border-slate-700 bg-slate-800/50"
                          : item.type === "ai"
                          ? "text-cyan-600 border-cyan-900 bg-cyan-950/50"
                          : "text-indigo-500 border-indigo-900 bg-indigo-950/50"
                      }`}>
                        {item.type === "record"
                          ? (item as RecordResult).recordType?.replace("_", " ")
                          : item.type === "nav"
                          ? "page"
                          : (item as PaletteAction).category}
                      </span>

                      {/* Arrow on selected */}
                      {isSelected && (
                        <svg className="h-3.5 w-3.5 text-cyan-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-white/[0.06]">
          <div className="flex items-center gap-3 text-[11px] text-slate-600">
            <span className="flex items-center gap-1">
              <kbd className="bg-white/[0.05] border border-white/[0.08] rounded px-1 py-0.5 font-mono text-[10px] text-slate-500">↑↓</kbd>
              navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="bg-white/[0.05] border border-white/[0.08] rounded px-1 py-0.5 font-mono text-[10px] text-slate-500">↵</kbd>
              open
            </span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-slate-600">
            <kbd className="bg-white/[0.05] border border-white/[0.08] rounded px-1 py-0.5 font-mono text-[10px] text-slate-500">Ctrl K</kbd>
            to toggle
          </div>
        </div>
      </div>
    </div>
  );
}
