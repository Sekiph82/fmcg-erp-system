"use client";

import Link from "next/link";
import { MpesaSummary } from "@/lib/dashboard";

const statusConfig: Record<string, { badge: string; label: string }> = {
  completed: { badge: "bg-emerald-100 text-emerald-700", label: "Success" },
  pending:   { badge: "bg-amber-100 text-amber-700",    label: "Pending" },
  failed:    { badge: "bg-red-100 text-red-600",         label: "Failed"  },
  cancelled: { badge: "bg-gray-100 text-gray-500",       label: "Cancelled" },
};

interface MpesaSectionProps {
  data: MpesaSummary;
}

export function MpesaSection({ data }: MpesaSectionProps) {
  const successColor =
    data.success_rate >= 90
      ? "text-emerald-600"
      : data.success_rate >= 70
      ? "text-amber-600"
      : "text-red-600";

  return (
    <div className="space-y-4">
      {/* Summary grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl bg-emerald-50 border border-emerald-100 p-3 text-center">
          <p className="text-[11px] uppercase tracking-wide text-emerald-600 font-medium">Collected</p>
          <p className="text-xl font-bold text-emerald-700 mt-0.5">
            KES {data.today_collected.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div className="rounded-xl bg-amber-50 border border-amber-100 p-3 text-center">
          <p className="text-[11px] uppercase tracking-wide text-amber-600 font-medium">Pending</p>
          <p className="text-xl font-bold text-amber-700 mt-0.5">{data.pending_count}</p>
        </div>
        <div className="rounded-xl bg-red-50 border border-red-100 p-3 text-center">
          <p className="text-[11px] uppercase tracking-wide text-red-600 font-medium">Failed</p>
          <p className="text-xl font-bold text-red-700 mt-0.5">{data.failed_today}</p>
        </div>
        <div className="rounded-xl bg-white border border-gray-100 p-3 text-center">
          <p className="text-[11px] uppercase tracking-wide text-gray-500 font-medium">Success Rate</p>
          <p className={`text-xl font-bold mt-0.5 ${successColor}`}>
            {data.success_rate.toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Success rate bar */}
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Transaction success rate today</span>
          <span>{data.total_today} total</span>
        </div>
        <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              data.success_rate >= 90
                ? "bg-emerald-500"
                : data.success_rate >= 70
                ? "bg-amber-500"
                : "bg-red-500"
            }`}
            style={{ width: `${Math.min(data.success_rate, 100)}%` }}
          />
        </div>
      </div>

      {/* Last 10 transactions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-700">Recent Transactions</h4>
          <Link href="/dashboard/finance/mpesa" className="text-xs text-indigo-500 hover:underline">
            View all →
          </Link>
        </div>
        <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
          {data.last_10.length === 0 ? (
            <p className="text-sm text-gray-400 py-2 text-center">No transactions today</p>
          ) : (
            data.last_10.map((tx) => {
              const cfg = statusConfig[tx.status] ?? statusConfig.pending;
              const t = new Date(tx.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              });
              return (
                <div
                  key={tx.id}
                  className="flex items-center justify-between gap-2 rounded-lg bg-gray-50 px-3 py-2 text-sm"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800 truncate">{tx.phone_number}</p>
                    {tx.reference && (
                      <p className="text-[11px] text-gray-400 truncate">{tx.reference}</p>
                    )}
                  </div>
                  <span className="font-semibold text-gray-900 shrink-0">
                    KES {tx.amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${cfg.badge} shrink-0`}>
                    {cfg.label}
                  </span>
                  <span className="text-[11px] text-gray-400 shrink-0">{t}</span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
