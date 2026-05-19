"use client";

import { useEffect } from "react";
import Link from "next/link";
import type { HelpEntry } from "@/lib/help/types";

interface HelpDrawerProps {
  open: boolean;
  onClose: () => void;
  entry: HelpEntry | undefined;
}

export function HelpDrawer({ open, onClose, entry }: HelpDrawerProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[1px]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Help"
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-sm flex-col border-l border-cyan-500/20 bg-[#0a1628] shadow-2xl"
        style={{ boxShadow: "-4px 0 32px rgba(0,212,255,0.08)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-cyan-500/20 px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-full border border-cyan-500/30 bg-cyan-500/10 text-sm font-bold text-cyan-300">
              ?
            </span>
            <span className="text-sm font-semibold text-slate-100">Help</span>
          </div>
          <button
            onClick={onClose}
            aria-label="Close help"
            className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 hover:bg-white/10 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {entry ? (
            <div className="space-y-5">
              {/* Page info */}
              <div>
                <div className="mb-1 flex items-center gap-2">
                  <span className="rounded border border-cyan-500/20 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-cyan-400">
                    {entry.module}
                  </span>
                  <span className="text-[10px] text-slate-500">{entry.role}</span>
                </div>
                <h2 className="text-base font-semibold text-slate-100">{entry.title}</h2>
                <p className="mt-1 text-sm text-slate-400">{entry.description}</p>
              </div>

              {/* Quick guide */}
              {entry.quickGuidePath && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-400">
                    Kenya Go-Live Quick Guide
                  </p>
                  <p className="text-xs text-slate-400">
                    Manual file:{" "}
                    <code className="text-amber-300/80">{entry.quickGuidePath.split("/").pop()}</code>
                  </p>
                  <p className="mt-1 text-[11px] text-slate-500">
                    Found at: docs/user-manual/{entry.quickGuidePath}
                  </p>
                </div>
              )}

              {/* Full reference */}
              <div className="rounded-lg border border-slate-700/50 bg-slate-800/30 p-4">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Full Reference Manual
                </p>
                <p className="text-xs text-slate-400">
                  Chapter:{" "}
                  <code className="text-slate-300">{entry.fullReferencePath.split("/").pop()}</code>
                </p>
                <p className="mt-1 text-[11px] text-slate-500">
                  Found at: docs/user-manual/{entry.fullReferencePath}
                </p>
              </div>

              {/* PDF note */}
              <div className="rounded-lg border border-slate-700/40 bg-slate-900/40 p-3">
                <p className="text-[11px] text-slate-500">
                  <span className="font-medium text-slate-400">PDF manuals</span> are available from
                  your admin or training package. Generate locally with{" "}
                  <code className="text-[10px] text-slate-400">
                    node docs/user-manual/pdf-export/generate-full-reference-pdf.mjs
                  </code>
                </p>
              </div>

              {/* Keywords */}
              {entry.keywords.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium text-slate-500">Related topics</p>
                  <div className="flex flex-wrap gap-1.5">
                    {entry.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="rounded border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 text-[10px] text-slate-400"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-slate-400">
                No specific help found for this page.
              </p>
              <p className="text-sm text-slate-500">
                Visit the{" "}
                <Link href="/dashboard/help" onClick={onClose} className="text-cyan-400 underline hover:text-cyan-300">
                  Help Center
                </Link>{" "}
                to browse all topics.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-cyan-500/20 px-5 py-3">
          <Link
            href="/dashboard/help"
            onClick={onClose}
            className="flex items-center justify-center gap-2 rounded-lg border border-cyan-500/20 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-300 hover:bg-cyan-500/20 transition-colors"
          >
            Browse Help Center
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      </div>
    </>
  );
}
