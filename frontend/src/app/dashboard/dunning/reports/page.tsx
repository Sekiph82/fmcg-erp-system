"use client";
import { useState, useEffect } from "react";
import { dunningApi, DunningDashboard } from "@/lib/dunning";

export default function DunningReports() {
  const [dashboard, setDashboard] = useState<DunningDashboard | null>(null);
  const [effectiveness, setEffectiveness] = useState<any[]>([]);
  const [ptp, setPTP] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      dunningApi.getDashboard(),
      dunningApi.getEffectiveness(),
      dunningApi.getPTPFulfillment(),
    ]).then(([d, e, p]) => { setDashboard(d); setEffectiveness(e); setPTP(p); }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-400">Loading…</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Dunning Reports & Analytics</h1>

      {/* KPI Summary */}
      {dashboard && (
        <div className="grid grid-cols-3 gap-4 lg:grid-cols-6">
          {[
            { label: "Open Cases", v: dashboard.open_cases },
            { label: "Total Overdue", v: `${dashboard.total_overdue_amount.toLocaleString()}` },
            { label: "Credit Holds", v: dashboard.credit_hold_count },
            { label: "Disputed", v: dashboard.disputed_cases },
            { label: "Open PTPs", v: dashboard.open_ptps },
            { label: "Broken PTPs", v: dashboard.broken_ptps },
          ].map((k) => (
            <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="text-2xl font-bold text-gray-900">{k.v}</div>
              <div className="text-xs text-gray-500 mt-1">{k.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* PTP Fulfillment */}
      {ptp && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Promise-to-Pay Fulfillment</h2>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "Total PTPs", value: ptp.total, color: "text-gray-900" },
              { label: "Met", value: ptp.met, color: "text-green-700" },
              { label: "Broken", value: ptp.broken, color: "text-red-700" },
              { label: "Success Rate", value: `${ptp.success_rate_pct}%`, color: ptp.success_rate_pct >= 70 ? "text-green-700" : "text-red-700" },
            ].map((k) => (
              <div key={k.label} className="text-center">
                <div className={`text-3xl font-bold ${k.color}`}>{k.value}</div>
                <div className="text-xs text-gray-500 mt-1">{k.label}</div>
              </div>
            ))}
          </div>
          {ptp.total > 0 && (
            <div className="mt-4">
              <div className="flex h-3 rounded-full overflow-hidden">
                <div className="bg-green-500 transition-all" style={{ width: `${ptp.met / ptp.total * 100}%` }}></div>
                <div className="bg-red-400 transition-all" style={{ width: `${ptp.broken / ptp.total * 100}%` }}></div>
                <div className="bg-blue-300 transition-all" style={{ width: `${ptp.open / ptp.total * 100}%` }}></div>
              </div>
              <div className="flex gap-4 mt-1 text-xs text-gray-500">
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-500 rounded-full"></span>Met</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-400 rounded-full"></span>Broken</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-300 rounded-full"></span>Open</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Effectiveness */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Dunning Level Effectiveness</h2>
          <p className="text-xs text-gray-500 mt-0.5">Actions sent per dunning level and channel</p>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Level", "Action Type", "Total Actions", "Sent", "Delivered"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {effectiveness.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No action data yet. Run detection and send reminders to populate.</td></tr>
            ) : effectiveness.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-bold text-gray-700">L{row.level_no}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">{row.action_type?.replace(/_/g, " ")}</span>
                </td>
                <td className="px-4 py-3 font-mono">{row.total_actions}</td>
                <td className="px-4 py-3 font-mono">{row.sent}</td>
                <td className="px-4 py-3 font-mono text-green-700">{row.delivered}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Quick report links */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Aging Report", href: "/dashboard/dunning/aging", icon: "📊" },
          { label: "Collector Workqueue", href: "/dashboard/dunning/workqueue", icon: "📋" },
          { label: "Credit Hold Review", href: "/dashboard/dunning/credit-holds", icon: "🔒" },
        ].map((l) => (
          <a key={l.label} href={l.href}
            className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3 hover:border-blue-400 hover:bg-blue-50 transition">
            <span className="text-2xl">{l.icon}</span>
            <span className="font-medium text-gray-900 text-sm">{l.label}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
