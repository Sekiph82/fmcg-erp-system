"use client";

import { DistributionSlice } from "@/lib/analytics";

const PALETTE = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444",
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
];

interface DistributionBarProps {
  data: DistributionSlice[];
  title?: string;
  formatValue?: (v: number) => string;
  maxItems?: number;
}

export function DistributionBar({
  data,
  title,
  formatValue = (v) => v.toLocaleString(undefined, { maximumFractionDigits: 0 }),
  maxItems = 8,
}: DistributionBarProps) {
  const items = data.slice(0, maxItems);
  const total = items.reduce((s, d) => s + Math.max(d.count, d.value), 0);

  if (!items.length) {
    return <div className="text-xs text-gray-400 text-center py-4">No data</div>;
  }

  return (
    <div className="space-y-2">
      {title && <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{title}</p>}
      {items.map((d, i) => {
        const metric = Math.max(d.count, 1);
        const pct = total > 0 ? (metric / total) * 100 : 0;
        const color = PALETTE[i % PALETTE.length];
        return (
          <div key={d.label} className="flex items-center gap-2">
            <span className="text-xs text-gray-600 w-24 truncate shrink-0" title={d.label}>
              {d.label}
            </span>
            <div className="flex-1 bg-gray-100 rounded-full h-2">
              <div
                className="h-2 rounded-full"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
            <span className="text-xs text-gray-500 w-14 text-right shrink-0">
              {d.value > 0 ? formatValue(d.value) : d.count.toLocaleString()}
            </span>
          </div>
        );
      })}
    </div>
  );
}
