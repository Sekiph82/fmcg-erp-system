"use client";
import { useEffect, useState } from "react";
import { portalApi } from "@/lib/portal";

export default function PortalReportsPage() {
  const [adoption, setAdoption] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portalApi.getAdoptionReport()
      .then(d => setAdoption(d as Record<string, unknown>))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-500">Loading…</div>;

  const kpis = adoption ? [
    { label: "Total Portal Accounts", value: adoption.total_accounts as number, color: "bg-blue-50 border-blue-200 text-blue-700" },
    { label: "Active Accounts", value: adoption.active_accounts as number, color: "bg-green-50 border-green-200 text-green-700" },
    { label: "Activation Rate", value: `${adoption.activation_rate_pct}%`, color: "bg-indigo-50 border-indigo-200 text-indigo-700" },
    { label: "Total Portal Users", value: adoption.total_users as number, color: "bg-purple-50 border-purple-200 text-purple-700" },
    { label: "Active Users", value: adoption.active_users as number, color: "bg-emerald-50 border-emerald-200 text-emerald-700" },
    { label: "Logins (30 Days)", value: adoption.logins_last_30_days as number, color: "bg-yellow-50 border-yellow-200 text-yellow-700" },
    { label: "Orders Submitted (30d)", value: adoption.orders_submitted_last_30_days as number, color: "bg-orange-50 border-orange-200 text-orange-700" },
    { label: "Claims (30 Days)", value: adoption.claims_submitted_last_30_days as number, color: "bg-red-50 border-red-200 text-red-700" },
  ] : [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Portal Reports</h1>

      {/* Adoption KPIs */}
      <div>
        <h2 className="font-semibold text-gray-700 mb-3">Portal Adoption Report</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {kpis.map(k => (
            <div key={k.label} className={`rounded-xl border p-4 ${k.color}`}>
              <div className="text-xs text-gray-500 mb-1">{k.label}</div>
              <div className="text-2xl font-bold">{k.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Activation Rate Bar */}
      {adoption && (
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <h2 className="font-semibold text-gray-800 mb-3">Activation Rate</h2>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${adoption.activation_rate_pct}%` }} />
            </div>
            <span className="text-sm font-bold text-blue-700">{adoption.activation_rate_pct}%</span>
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>{adoption.active_accounts} active</span>
            <span>{adoption.total_accounts} total</span>
          </div>
        </div>
      )}

      {/* Activity Summary */}
      {adoption && (
        <div className="bg-white rounded-xl border shadow-sm p-4">
          <h2 className="font-semibold text-gray-800 mb-3">30-Day Activity Summary</h2>
          <div className="space-y-3">
            {[
              { label: "Login Sessions", value: adoption.logins_last_30_days as number, max: 500, color: "#3B82F6" },
              { label: "Orders Submitted", value: adoption.orders_submitted_last_30_days as number, max: 100, color: "#8B5CF6" },
              { label: "Claims Filed", value: adoption.claims_submitted_last_30_days as number, max: 50, color: "#EF4444" },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-3">
                <div className="w-32 text-sm text-gray-600">{item.label}</div>
                <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all"
                    style={{ width: `${Math.min((item.value / item.max) * 100, 100)}%`, background: item.color }} />
                </div>
                <div className="w-12 text-right text-sm font-semibold" style={{ color: item.color }}>{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
