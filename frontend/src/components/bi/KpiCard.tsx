"use client";
import { useRouter } from "next/navigation";

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  trend?: "up" | "down" | "neutral";
  color?: "default" | "green" | "red" | "amber" | "blue" | "indigo";
  href?: string;
  loading?: boolean;
}

const COLOR_MAP = {
  default: { val: "text-white", bg: "bg-white/[0.03]", border: "border-white/[0.07]" },
  green:   { val: "text-emerald-400", bg: "bg-emerald-500/5", border: "border-emerald-500/20" },
  red:     { val: "text-red-400", bg: "bg-red-500/5", border: "border-red-500/20" },
  amber:   { val: "text-amber-400", bg: "bg-amber-500/5", border: "border-amber-500/20" },
  blue:    { val: "text-blue-400", bg: "bg-blue-500/5", border: "border-blue-500/20" },
  indigo:  { val: "text-indigo-400", bg: "bg-indigo-500/5", border: "border-indigo-500/20" },
};

const TREND_ICONS = {
  up: <span className="text-emerald-400 text-xs">↑</span>,
  down: <span className="text-red-400 text-xs">↓</span>,
  neutral: <span className="text-slate-500 text-xs">→</span>,
};

export function KpiCard({ label, value, sub, trend, color = "default", href, loading }: KpiCardProps) {
  const router = useRouter();
  const c = COLOR_MAP[color];

  return (
    <button
      onClick={() => href && router.push(href)}
      className={[
        "relative rounded-xl border p-5 text-left transition-all duration-150 w-full",
        c.bg, c.border,
        href ? "cursor-pointer hover:brightness-110" : "cursor-default",
        loading ? "animate-pulse" : "",
      ].join(" ")}
    >
      <p className="text-[11px] font-medium uppercase tracking-widest text-slate-500">{label}</p>
      {loading ? (
        <div className="mt-2 h-7 w-24 rounded bg-white/10" />
      ) : (
        <p className={`mt-1.5 text-2xl font-semibold leading-none tracking-tight ${c.val}`}>
          {value}
        </p>
      )}
      {sub && (
        <div className="mt-2 flex items-center gap-1">
          {trend && TREND_ICONS[trend]}
          <span className="text-[11px] text-slate-500">{sub}</span>
        </div>
      )}
      {href && (
        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-700 text-xs">›</span>
      )}
    </button>
  );
}
