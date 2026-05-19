"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { HELP_REGISTRY, HELP_MODULES, HELP_ROLES } from "@/lib/help/help-registry";
import { searchHelpEntries } from "@/lib/help/get-help-for-route";

export default function HelpCenterPage() {
  const [query, setQuery] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");

  const results = useMemo(() => {
    let entries = searchHelpEntries(query);
    if (moduleFilter) entries = entries.filter((e) => e.module === moduleFilter);
    if (roleFilter) entries = entries.filter((e) => e.role === roleFilter);
    return entries;
  }, [query, moduleFilter, roleFilter]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Help Center</h1>
        <p className="mt-1 text-sm text-slate-400">
          Browse ERP module guides, manual references, and quick training material.
        </p>
      </div>

      {/* PDF note */}
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3">
        <p className="text-sm text-amber-300/80">
          <span className="font-semibold">PDF manuals</span> are available from your admin or training package.
          Kenya Go-Live PDF and Full Reference PDF can be generated locally from{" "}
          <code className="text-[11px] text-amber-400">docs/user-manual/pdf-export/</code>.
        </p>
      </div>

      {/* Search + filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search topics, modules, keywords…"
          className="flex-1 min-w-48 rounded-lg border border-slate-700/60 bg-slate-800/50 px-4 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-cyan-500/50 focus:outline-none"
        />
        <select
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
          className="rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-300 focus:border-cyan-500/50 focus:outline-none"
        >
          <option value="">All modules</option>
          {HELP_MODULES.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="rounded-lg border border-slate-700/60 bg-slate-800/50 px-3 py-2 text-sm text-slate-300 focus:border-cyan-500/50 focus:outline-none"
        >
          <option value="">All roles</option>
          {HELP_ROLES.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        {(query || moduleFilter || roleFilter) && (
          <button
            onClick={() => { setQuery(""); setModuleFilter(""); setRoleFilter(""); }}
            className="rounded-lg border border-slate-700/50 bg-slate-800/30 px-3 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Results count */}
      <p className="text-xs text-slate-500">
        {results.length} of {HELP_REGISTRY.length} topics
      </p>

      {/* Entry list */}
      <div className="grid gap-3 sm:grid-cols-2">
        {results.map((entry) => (
          <Link
            key={entry.id}
            href={entry.route}
            className="group flex flex-col gap-1.5 rounded-lg border border-slate-700/50 bg-slate-800/30 p-4 hover:border-cyan-500/30 hover:bg-slate-800/60 transition-all"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm font-medium text-slate-100 group-hover:text-cyan-300 transition-colors">
                {entry.title}
              </span>
              <span className="shrink-0 rounded border border-slate-700/40 bg-slate-700/30 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider text-slate-400">
                {entry.module}
              </span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-2">{entry.description}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-slate-600">{entry.route}</span>
              {entry.quickGuidePath && (
                <span className="rounded border border-amber-500/20 bg-amber-500/5 px-1.5 py-0.5 text-[9px] text-amber-400">
                  Kenya guide
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>

      {results.length === 0 && (
        <div className="rounded-lg border border-slate-700/40 bg-slate-800/20 py-12 text-center">
          <p className="text-sm text-slate-400">No help topics match your search.</p>
          <button
            onClick={() => { setQuery(""); setModuleFilter(""); setRoleFilter(""); }}
            className="mt-2 text-xs text-cyan-400 hover:underline"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Manual references */}
      <div className="border-t border-slate-700/40 pt-6 space-y-3">
        <h2 className="text-sm font-semibold text-slate-300">Manual Source Files</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-700/40 bg-slate-800/20 p-3">
            <p className="text-xs font-semibold text-amber-400">Kenya Go-Live Training Manuals</p>
            <p className="text-[11px] text-slate-500 mt-1">docs/user-manual/kenya-go-live/</p>
            <p className="text-[11px] text-slate-500">10 chapters — role-based training</p>
          </div>
          <div className="rounded-lg border border-slate-700/40 bg-slate-800/20 p-3">
            <p className="text-xs font-semibold text-slate-300">Full Reference Manual</p>
            <p className="text-[11px] text-slate-500 mt-1">docs/user-manual/full-reference/</p>
            <p className="text-[11px] text-slate-500">15 chapters — all modules</p>
          </div>
        </div>
      </div>
    </div>
  );
}
