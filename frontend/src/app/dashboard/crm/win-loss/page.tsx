"use client";
import { useEffect, useState } from "react";
import { crmApi, fmtCurrency, LOSS_REASON_LABELS, WIN_REASON_LABELS } from "@/lib/crm_pipeline";
import { tx } from "@/lib/i18n/core";

interface WinLossReport {
  total_won: number;
  total_lost: number;
  win_rate_pct: number;
  loss_by_reason: { reason_code: string; count: number; total_revenue: number; pct_of_total: number }[];
  win_by_reason: { reason_code: string; count: number; total_revenue: number; pct_of_total: number }[];
  top_competitors_causing_loss: { competitor: string; loss_count: number }[];
}

export default function WinLossPage() {
  const [data, setData] = useState<WinLossReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"loss" | "win" | "competitor">("loss");

  useEffect(() => {
    crmApi.getWinLossReport().then(d => setData(d as unknown as WinLossReport)).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-500">{tx("Loading…")}</div>;
  if (!data) return <div className="p-6 text-red-500">{tx("Failed to load report")}</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">{tx("Win / Loss Analysis")}</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-green-50 border border-green-200 rounded-xl p-4">
          <div className="text-xs text-gray-500">{tx("Total Won")}</div>
          <div className="text-2xl font-bold text-green-700">{data.total_won}</div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="text-xs text-gray-500">{tx("Total Lost")}</div>
          <div className="text-2xl font-bold text-red-700">{data.total_lost}</div>
        </div>
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
          <div className="text-xs text-gray-500">{tx("Win Rate")}</div>
          <div className="text-2xl font-bold text-indigo-700">{data.win_rate_pct}%</div>
        </div>
      </div>

      {/* Win Rate Bar */}
      <div className="bg-white rounded-xl border shadow-sm p-4">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
          <span>{tx("Win Rate")}</span>
          <span>{data.win_rate_pct}%</span>
        </div>
        <div className="h-4 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full rounded-full bg-green-500 transition-all"
            style={{ width: `${data.win_rate_pct}%` }} />
        </div>
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>{data.total_won} {tx("won")}</span>
          <span>{data.total_lost} {tx("lost")}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {[{ id: "loss", label: tx("Loss Reasons") }, { id: "win", label: tx("Win Reasons") }, { id: "competitor", label: tx("Competitor Analysis") }].map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id as "loss" | "win" | "competitor")}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === t.id ? "border-red-600 text-red-600" : "border-transparent text-gray-500 hover:text-gray-700"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Loss Reasons */}
      {activeTab === "loss" && (
        <div className="space-y-2">
          {data.loss_by_reason.length === 0 && <p className="text-sm text-gray-400">{tx("No loss data")}</p>}
          {data.loss_by_reason.map(row => (
            <div key={row.reason_code} className="bg-white rounded-xl border shadow-sm p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-medium text-gray-800 text-sm">
                    {LOSS_REASON_LABELS[row.reason_code as keyof typeof LOSS_REASON_LABELS] || row.reason_code}
                  </div>
                  <div className="text-xs text-gray-500">{row.count} {tx("deals ·")} {fmtCurrency(row.total_revenue)}</div>
                </div>
                <div className="text-lg font-bold text-red-600">{row.pct_of_total}%</div>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-red-400 rounded-full" style={{ width: `${row.pct_of_total}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Win Reasons */}
      {activeTab === "win" && (
        <div className="space-y-2">
          {data.win_by_reason.length === 0 && <p className="text-sm text-gray-400">{tx("No win data")}</p>}
          {data.win_by_reason.map(row => (
            <div key={row.reason_code} className="bg-white rounded-xl border shadow-sm p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <div className="font-medium text-gray-800 text-sm">
                    {WIN_REASON_LABELS[row.reason_code as keyof typeof WIN_REASON_LABELS] || row.reason_code}
                  </div>
                  <div className="text-xs text-gray-500">{row.count} {tx("deals ·")} {fmtCurrency(row.total_revenue)}</div>
                </div>
                <div className="text-lg font-bold text-green-600">{row.pct_of_total}%</div>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className="h-full bg-green-400 rounded-full" style={{ width: `${row.pct_of_total}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Competitor Analysis */}
      {activeTab === "competitor" && (
        <div className="space-y-2">
          {data.top_competitors_causing_loss.length === 0 && <p className="text-sm text-gray-400">{tx("No competitor data")}</p>}
          <div className="bg-white rounded-xl border shadow-sm overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-xs text-gray-600">
                  <th className="px-3 py-2 text-left">{tx("Competitor")}</th>
                  <th className="px-3 py-2 text-right">{tx("Deals Lost")}</th>
                  <th className="px-3 py-2 text-right">{tx("% of Total Losses")}</th>
                </tr>
              </thead>
              <tbody>
                {data.top_competitors_causing_loss.map(row => (
                  <tr key={row.competitor} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium text-gray-800">{row.competitor}</td>
                    <td className="px-3 py-2 text-right text-red-700 font-semibold">{row.loss_count}</td>
                    <td className="px-3 py-2 text-right text-gray-500">
                      {data.total_lost > 0 ? Math.round(row.loss_count / data.total_lost * 100) : 0}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
