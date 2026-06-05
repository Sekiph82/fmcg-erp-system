"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { helpTopics } from "@/lib/help-content";

type Props = {
  topic: string;
  className?: string;
};

export function PageHelpTooltip({ topic, className = "" }: Props) {
  const [open, setOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const entry = helpTopics[topic];

  const cancelClose = useCallback(() => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  }, []);

  const scheduleClose = useCallback(() => {
    closeTimer.current = setTimeout(() => setOpen(false), 150);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  if (!entry) return null;

  return (
    <div
      className={`relative inline-block shrink-0 ${className}`}
      onMouseEnter={() => { cancelClose(); setOpen(true); }}
      onMouseLeave={scheduleClose}
    >
      {/* Trigger button */}
      <button
        type="button"
        aria-label="Open page help"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onFocus={() => { cancelClose(); setOpen(true); }}
        onBlur={scheduleClose}
        className="flex h-7 w-7 items-center justify-center rounded-full border border-gray-300 bg-white/80 text-gray-400 text-sm font-semibold hover:border-gray-400 hover:bg-gray-50 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 transition-colors"
      >
        ?
      </button>

      {/* Popover */}
      {open && (
        <div
          role="dialog"
          aria-label={`Help: ${entry.title}`}
          className="absolute right-0 top-9 z-50 w-[400px] rounded-xl border border-gray-200 bg-white shadow-lg text-sm"
        >
          {/* Arrow */}
          <div className="absolute -top-[5px] right-2.5 h-2.5 w-2.5 rotate-45 border-l border-t border-gray-200 bg-white" />

          <div className="p-4 space-y-3 max-h-[80vh] overflow-y-auto">
            {/* Title + purpose */}
            <div>
              <h3 className="font-semibold text-gray-900 text-base leading-tight">{entry.title}</h3>
              <p className="text-gray-500 mt-1 leading-relaxed">{entry.purpose}</p>
            </div>

            {/* Main actions */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Main Actions
              </p>
              <ul className="space-y-1">
                {entry.mainActions.map((a, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-gray-700">
                    <span className="mt-[5px] h-1.5 w-1.5 rounded-full bg-indigo-400 shrink-0" />
                    {a}
                  </li>
                ))}
              </ul>
            </div>

            {/* Key fields */}
            {entry.keyFields && entry.keyFields.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                  Key Fields
                </p>
                <div className="space-y-1">
                  {entry.keyFields.map((f, i) => (
                    <div key={i} className="flex gap-1.5">
                      <span className="font-medium text-gray-700 shrink-0">{f.label}:</span>
                      <span className="text-gray-500">{f.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Statuses */}
            {entry.statuses && entry.statuses.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                  Status Meanings
                </p>
                <div className="space-y-1">
                  {entry.statuses.map((s, i) => (
                    <div key={i} className="flex items-start gap-1.5">
                      <code className="text-[10px] bg-gray-100 px-1.5 py-0.5 rounded text-gray-700 shrink-0 leading-4 mt-0.5">
                        {s.status}
                      </code>
                      <span className="text-gray-500">{s.meaning}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Warnings */}
            {entry.warnings && entry.warnings.length > 0 && (
              <div className="bg-amber-50 border border-amber-100 rounded-lg p-2.5">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-600 mb-1.5">
                  Warnings
                </p>
                <ul className="space-y-1">
                  {entry.warnings.map((w, i) => (
                    <li key={i} className="text-amber-800 flex items-start gap-1.5">
                      <span className="shrink-0 mt-0.5">⚠</span>
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Related manual */}
            {entry.relatedManual && (
              <p className="text-[11px] text-gray-400 border-t border-gray-100 pt-2">
                📖 {entry.relatedManual}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
