"use client";

import Link from "next/link";
import { AlertItem } from "@/lib/dashboard";

const severityConfig = {
  critical: {
    bg: "bg-red-50",
    border: "border-red-300",
    badge: "bg-red-100 text-red-700",
    dot: "bg-red-500",
    label: "CRITICAL",
  },
  medium: {
    bg: "bg-amber-50",
    border: "border-amber-300",
    badge: "bg-amber-100 text-amber-700",
    dot: "bg-amber-500",
    label: "WARNING",
  },
  low: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    badge: "bg-blue-100 text-blue-700",
    dot: "bg-blue-400",
    label: "INFO",
  },
};

const moduleIcons: Record<string, string> = {
  production: "⚙️",
  inventory: "📦",
  sales: "📄",
  finance: "💰",
  logistics: "🚢",
  maintenance: "🔧",
  quality: "🔬",
};

interface AlertsPanelProps {
  alerts: AlertItem[];
}

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="text-4xl mb-2">✅</div>
        <p className="text-sm font-medium text-gray-700">All systems normal</p>
        <p className="text-xs text-gray-400 mt-0.5">No active alerts</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {alerts.map((alert) => {
        const cfg = severityConfig[alert.severity] ?? severityConfig.low;
        const icon = moduleIcons[alert.module] ?? "⚠️";
        const time = new Date(alert.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });

        return (
          <div
            key={alert.id}
            className={`flex items-start gap-3 rounded-lg border px-3 py-2.5 ${cfg.bg} ${cfg.border}`}
          >
            <div className="mt-0.5 text-lg leading-none">{icon}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide ${cfg.badge}`}>
                  {cfg.label}
                </span>
                <span className="text-[11px] text-gray-400">{time}</span>
              </div>
              <p className="mt-0.5 text-sm text-gray-800">{alert.message}</p>
            </div>
            <Link
              href={alert.action_url}
              className="shrink-0 text-xs font-medium text-indigo-600 hover:underline mt-0.5"
            >
              View →
            </Link>
          </div>
        );
      })}
    </div>
  );
}
