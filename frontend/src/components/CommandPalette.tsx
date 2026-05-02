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

// ── Icon maps ─────────────────────────────────────────────────────────────────

const RECORD_ICONS: Record<string, string> = {
  customer:       "👤",
  supplier:       "🏢",
  product:        "📦",
  material:       "🧪",
  sales_order:    "🛒",
  purchase_order: "📋",
  invoice:        "📄",
};

const CAT_LABEL: Record<string, string> = {
  navigation: "Navigation",
  action:     "Actions",
  report:     "Reports",
  ai:         "AI Commands",
  record:     "Records",
  recent:     "Recent",
};

// ── Fuzzy match ───────────────────────────────────────────────────────────────

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

// ── Build nav results from NAV_CONFIG ─────────────────────────────────────────

function buildNavResults(query: string, hasPermission: (c: string) => boolean): NavResult[] {
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
      const secMatches = !q || fuzzyMatch(sec.label, q);

      for (const item of sec.items) {
        if (item.permission && !hasPermission(item.permission)) continue;
        if (secMatches || fuzzyMatch(item.label, q)) {
          results.push({
            type: "nav",
            id: `${sec.id}__${item.label}`,
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

// ── Command Palette ───────────────────────────────────────────────────────────

export function CommandPalette({ open, onClose, onVisit, recent }: Props) {
  const [query, setQuery]               = useState("");
  const [recordResults, setRecordResults] = useState<RecordResult[]>([]);
  const [loading, setLoading]           = useState(false);
  const [selectedIdx, setSelectedIdx]   = useState(0);

  const inputRef    = useRef<HTMLInputElement>(null);
  const listRef     = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const router = useRouter();
  const { hasPermission } = useAuth();

  // Focus + reset on open
  useEffect(() => {
    if (open) {
      setQuery("");
      setRecordResults([]);
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  // Debounced record search
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

  // Build grouped results
  const { allResults, groups } = useMemo(() => {
    const q = query.trim();

    if (!q) {
      const recentItems: NavResult[] = recent.map((r) => ({
        type: "nav" as const,
        id: r.href,
        label: r.label,
        subtitle: r.subtitle ?? "Recent",
        href: r.href,
      }));
      return {
        allResults: recentItems as Result[],
        groups: recentItems.length > 0
          ? [{ category: "recent", items: recentItems as Result[] }]
          : [],
      };
    }

    const navItems = buildNavResults(q, hasPermission);
    const actions  = filterActions(ACTION_REGISTRY, q, hasPermission).slice(0, 5);
    const records  = recordResults.map((r) => ({ ...r, type: "record" as const }));

    const groupList = [
      navItems.length > 0 && { category: "navigation", items: navItems as Result[] },
      actions.length > 0  && { category: "action",     items: actions as Result[] },
      records.length > 0  && { category: "record",     items: records as Result[] },
    ].filter(Boolean) as { category: string; items: Result[] }[];

    return { allResults: groupList.flatMap((g) => g.items), groups: groupList };
  }, [query, recordResults, recent, hasPermission]);

  // Reset selection on result change
  useEffect(() => { setSelectedIdx(0); }, [allResults.length, query]);

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${selectedIdx}"]`) as HTMLElement | null;
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIdx]);

  const navigate = useCallback((result: Result) => {
    const href = (result as NavResult).href ?? (result as PaletteAction).href;
    if (!href) return;
    onVisit({
      label:    result.label,
      href,
      subtitle: (result as NavResult).subtitle ?? (result as PaletteAction).description,
    });
    onClose();
    router.push(href);
  }, [onClose, onVisit, router]);

  const handleKey = useCallback((e: ReactKeyboardEvent<HTMLInputElement>) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIdx((i) => Math.min(i + 1, allResults.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIdx((i) => Math.max(i - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (allResults[selectedIdx]) navigate(allResults[selectedIdx]);
        break;
      case "Escape":
        onClose();
        break;
    }
  }, [allResults, selectedIdx, navigate, onClose]);

  if (!open) return null;

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    // Full-screen overlay — intercepts clicks outside panel
    <div
      className="fixed inset-0 z-[9999] flex items-start justify-center"
      style={{ paddingTop: "10vh", paddingLeft: 16, paddingRight: 16 }}
      onMouseDown={onClose}
    >
      {/* Backdrop — solid enough to fully cover underlying content */}
      <div
        className="absolute inset-0"
        style={{ background: "rgba(0, 0, 0, 0.72)" }}
        aria-hidden="true"
      />

      {/*
        Panel — sits above the backdrop.
        No overflow-hidden on the outer shell so box-shadow renders correctly.
        Inner sections handle their own overflow.
      */}
      <div
        className="relative w-full max-w-[640px] rounded-2xl shadow-2xl flex flex-col"
        style={{
          maxHeight: "min(540px, calc(90vh - 10vh))",
          background: "#0a1628",
          border: "1px solid rgba(99, 102, 241, 0.25)",
          boxShadow: "0 0 0 1px rgba(99,102,241,0.08), 0 24px 48px rgba(0,0,0,0.8)",
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* ── Search input row ─────────────────────────────────────────────── */}
        <div
          className="flex items-center gap-3 px-4 shrink-0"
          style={{
            height: 52,
            borderBottom: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          {/* Small, non-dominant search icon */}
          <svg
            className="h-4 w-4 shrink-0 text-slate-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>

          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Search modules, actions, records…"
            className="flex-1 bg-transparent text-[14.5px] text-slate-100 placeholder:text-slate-500 outline-none"
            autoComplete="off"
            spellCheck={false}
            aria-label="Search"
          />

          {loading ? (
            <div className="h-3.5 w-3.5 rounded-full border-2 border-cyan-500/30 border-t-cyan-400 animate-spin shrink-0" />
          ) : (
            <kbd className="hidden sm:inline-flex items-center shrink-0 text-[10px] text-slate-600 font-mono bg-white/[0.04] rounded px-1.5 py-0.5 border border-white/[0.06]">
              ESC
            </kbd>
          )}
        </div>

        {/* ── Results area — scrolls inside the panel ──────────────────────── */}
        <div
          ref={listRef}
          className="flex-1 overflow-y-auto overscroll-contain"
          style={{ minHeight: 0 }}
        >
          {/* Empty states */}
          {groups.length === 0 && query.trim() && !loading && (
            <div className="px-4 py-10 text-center">
              <p className="text-sm text-slate-500">
                No results for{" "}
                <span className="text-slate-300 font-medium">"{query}"</span>
              </p>
            </div>
          )}

          {groups.length === 0 && !query.trim() && (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-slate-500">Type to search modules, actions, records…</p>
              <p className="mt-2 text-xs text-slate-600">↑↓ navigate · Enter open · Esc close</p>
            </div>
          )}

          {/* Result groups */}
          {groups.map((group, gi) => {
            // Compute the flat index offset for this group
            const offset = groups.slice(0, gi).reduce((acc, g) => acc + g.items.length, 0);

            return (
              <div key={group.category}>
                {/* Group label */}
                <div className="flex items-center gap-2 px-4 pt-3 pb-1">
                  <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                    {CAT_LABEL[group.category] ?? group.category}
                  </span>
                </div>

                {/* Items */}
                {group.items.map((item, i) => {
                  const absIdx     = offset + i;
                  const isSelected = selectedIdx === absIdx;

                  const href = (item as NavResult).href ?? (item as PaletteAction).href ?? "";
                  const subtitle =
                    (item as NavResult).subtitle ??
                    (item as PaletteAction).description ??
                    "";
                  // PaletteAction has no 'type' field; use loose cast for discriminating
                  const itemType = (item as { type?: string }).type;

                  const icon =
                    (item as PaletteAction).icon ??
                    RECORD_ICONS[(item as RecordResult).recordType ?? ""] ??
                    (itemType === "record" ? "🔍" : "🗺️");

                  const badgeText =
                    itemType === "record"
                      ? (item as RecordResult).recordType?.replace("_", " ")
                      : itemType === "nav"
                      ? "page"
                      : (item as PaletteAction).category;

                  const badgeCls =
                    itemType === "ai"
                      ? "text-cyan-600 border-cyan-900/80 bg-cyan-950/60"
                      : itemType === "nav" || itemType === "record"
                      ? "text-slate-500 border-slate-700/80 bg-slate-800/60"
                      : "text-indigo-400 border-indigo-900/80 bg-indigo-950/60";

                  return (
                    <button
                      key={`${group.category}-${item.id ?? href}-${i}`}
                      data-idx={absIdx}
                      onClick={() => navigate(item)}
                      className={[
                        "w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors",
                        isSelected
                          ? "bg-indigo-500/[0.14] text-white"
                          : "text-slate-300 hover:bg-white/[0.04] hover:text-white",
                      ].join(" ")}
                    >
                      {/* Emoji icon */}
                      <span className="text-[15px] shrink-0 w-5 text-center select-none leading-none">
                        {icon}
                      </span>

                      {/* Label + subtitle */}
                      <div className="flex-1 min-w-0">
                        <div className="text-[13px] font-medium truncate leading-snug">
                          {item.label}
                        </div>
                        {subtitle && (
                          <div className="text-[11px] text-slate-500 truncate mt-[1px]">
                            {subtitle}
                          </div>
                        )}
                      </div>

                      {/* Type badge */}
                      {badgeText && (
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border shrink-0 ${badgeCls}`}>
                          {badgeText}
                        </span>
                      )}

                      {/* Arrow on selected */}
                      {isSelected && (
                        <svg className="h-3 w-3 text-indigo-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            );
          })}

          <div className="h-1" />
        </div>

        {/* ── Footer hints ─────────────────────────────────────────────────── */}
        <div
          className="flex items-center justify-between px-4 py-2 shrink-0"
          style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
        >
          <div className="flex items-center gap-3 text-[11px] text-slate-600">
            <span>
              <kbd className="font-mono text-[10px] bg-white/[0.04] border border-white/[0.07] rounded px-1 py-0.5">↑↓</kbd>
              {" "}navigate
            </span>
            <span>
              <kbd className="font-mono text-[10px] bg-white/[0.04] border border-white/[0.07] rounded px-1 py-0.5">↵</kbd>
              {" "}open
            </span>
          </div>
          <span className="text-[11px] text-slate-600">
            <kbd className="font-mono text-[10px] bg-white/[0.04] border border-white/[0.07] rounded px-1 py-0.5">Ctrl K</kbd>
            {" "}toggle
          </span>
        </div>
      </div>
    </div>
  );
}
