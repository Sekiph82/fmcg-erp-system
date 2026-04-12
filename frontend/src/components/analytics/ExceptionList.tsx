"use client";

import Link from "next/link";
import { ExceptionRow } from "@/lib/analytics";

const SEV_COLOR: Record<string, string> = {
  critical: "bg-red-50 text-red-700 border-red-200",
  high:     "bg-orange-50 text-orange-700 border-orange-200",
  medium:   "bg-amber-50 text-amber-700 border-amber-200",
  low:      "bg-gray-50 text-gray-600 border-gray-200",
};

const SEV_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high:     "bg-orange-500",
  medium:   "bg-amber-500",
  low:      "bg-gray-400",
};

interface ExceptionListProps {
  items: ExceptionRow[];
  title?: string;
  maxItems?: number;
}

export function ExceptionList({ items, title = "Exceptions", maxItems = 8 }: ExceptionListProps) {
  const visible = items.slice(0, maxItems);

  if (!visible.length) {
    return (
      <div className="text-xs text-emerald-600 text-center py-4 flex items-center justify-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
        No exceptions
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {title && <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</p>}
      {visible.map((row) => (
        <Link
          key={row.id}
          href={row.href}
          className={`flex items-start gap-2.5 p-2.5 rounded-lg border text-xs hover:opacity-80 transition-opacity ${SEV_COLOR[row.severity] ?? SEV_COLOR.low}`}
        >
          <span className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${SEV_DOT[row.severity] ?? SEV_DOT.low}`} />
          <div className="flex-1 min-w-0">
            <span className="font-medium">{row.label}</span>
            {row.detail && <span className="ml-1 opacity-70">&mdash; {row.detail}</span>}
          </div>
          <span className="shrink-0 opacity-50">→</span>
        </Link>
      ))}
    </div>
  );
}
