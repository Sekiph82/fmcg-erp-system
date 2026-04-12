"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

interface DashboardShellProps {
  title: string;
  subtitle?: string;
  days: number;
  onDaysChange: (d: number) => void;
  backHref?: string;
  children: React.ReactNode;
  loading?: boolean;
}

const DAY_OPTIONS = [7, 14, 30, 60, 90];

export function DashboardShell({ title, subtitle, days, onDaysChange, backHref, children, loading }: DashboardShellProps) {
  const router = useRouter();

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          {backHref && (
            <button onClick={() => router.push(backHref)} className="text-xs text-slate-500 hover:text-slate-300 mb-1 block">
              ← Reports
            </button>
          )}
          <h1 className="text-xl font-semibold text-white leading-tight">{title}</h1>
          {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-white/[0.07] bg-white/[0.03] p-1">
          {DAY_OPTIONS.map(d => (
            <button
              key={d}
              onClick={() => onDaysChange(d)}
              className={[
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                days === d
                  ? "bg-indigo-600 text-white"
                  : "text-slate-500 hover:text-slate-300",
              ].join(" ")}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl border border-white/[0.06] bg-white/[0.03] animate-pulse" />
          ))}
        </div>
      ) : (
        children
      )}
    </div>
  );
}

// Section header inside a dashboard
export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">{title}</p>
      {children}
    </div>
  );
}

// Chart card wrapper
export function ChartCard({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 ${className}`}>
      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-4">{title}</p>
      {children}
    </div>
  );
}

// Distribution table (top items ranked)
export function DistTable({ items, valueLabel = "Value" }: {
  items: { label: string; value: number; count: number }[];
  valueLabel?: string;
}) {
  const max = Math.max(...items.map(i => i.value), 1);
  return (
    <div className="space-y-2">
      {items.map((item, idx) => (
        <div key={idx} className="group flex items-center gap-3">
          <span className="w-4 text-[10px] text-slate-600 font-mono">{idx + 1}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[12px] text-slate-300 truncate">{item.label}</span>
              <span className="text-[12px] text-slate-400 font-mono ml-4 shrink-0">
                {item.value >= 1000 ? `${(item.value/1000).toFixed(1)}K` : item.value.toFixed(0)}
              </span>
            </div>
            <div className="h-1 w-full rounded-full bg-white/[0.04]">
              <div
                className="h-1 rounded-full bg-indigo-500/60"
                style={{ width: `${(item.value / max) * 100}%` }}
              />
            </div>
          </div>
          <span className="text-[10px] text-slate-600 w-8 text-right">{item.count}</span>
        </div>
      ))}
    </div>
  );
}
