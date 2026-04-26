"use client";

import Link from "next/link";
import { TrendPoint } from "@/lib/dashboard";
import { Sparkline, TrendBadge } from "./Sparkline";

export type KPIStatus = "ok" | "warning" | "critical";

interface KPICardProps {
  label: string;
  value: string | number;
  subtext?: string;
  status?: KPIStatus;
  trend?: TrendPoint[];
  trendColor?: string;
  href?: string;
  icon?: React.ReactNode;
  loading?: boolean;
}

const statusBorder: Record<KPIStatus, string> = {
  ok:       "border-l-emerald-500",
  warning:  "border-l-amber-500",
  critical: "border-l-red-500",
};

const statusDot: Record<KPIStatus, string> = {
  ok:       "bg-emerald-500",
  warning:  "bg-amber-500",
  critical: "bg-red-500",
};

export function KPICard({
  label,
  value,
  subtext,
  status = "ok",
  trend,
  trendColor,
  href,
  icon,
  loading = false,
}: KPICardProps) {
  const prev = trend && trend.length >= 2 ? trend[trend.length - 2].value : undefined;
  const curr = trend && trend.length >= 1 ? trend[trend.length - 1].value : undefined;

  const card = (
    <div
      className={`
        glow-card relative flex flex-col justify-between gap-2
        border-l-4 ${statusBorder[status]}
        p-4 active:scale-[0.98] transition-all
        ${href ? "cursor-pointer" : ""}
      `}
    >
      {loading && (
        <div className="absolute inset-0 rounded-2xl bg-[rgba(2,8,23,0.55)] flex items-center justify-center z-10 backdrop-blur-sm">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide truncate">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-100 leading-none">{value}</p>
          {subtext && <p className="mt-1 text-xs text-slate-500">{subtext}</p>}
        </div>

        <div className="flex flex-col items-end gap-1 shrink-0">
          {icon && (
            <div className={`p-2 rounded-lg ${statusDot[status]} bg-opacity-15`}>
              {icon}
            </div>
          )}
          {typeof prev === "number" && typeof curr === "number" && (
            <TrendBadge current={curr} previous={prev} />
          )}
        </div>
      </div>

      {trend && trend.length > 1 && (
        <div className="mt-1">
          <Sparkline
            data={trend}
            color={
              trendColor ||
              (status === "ok" ? "#10b981" : status === "warning" ? "#f59e0b" : "#ef4444")
            }
            height={32}
            width={72}
          />
        </div>
      )}

      {href && (
        <span className="text-xs text-blue-400 font-medium mt-0.5">View details →</span>
      )}
    </div>
  );

  if (href) return <Link href={href}>{card}</Link>;
  return card;
}
