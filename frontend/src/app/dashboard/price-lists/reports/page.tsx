"use client";
import { useState, useEffect } from "react";
import { plApi, PLHeader, PL_TYPE_COLORS, PL_STATUS_COLORS } from "@/lib/price_list";

export default function PLReports() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [expiring, setExpiring] = useState<PLHeader[]>([]);
  const [belowMargin, setBelowMargin] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      plApi.getDashboard(),
      plApi.getExpiring(60),
      plApi.getBelowMargin(),
    ]).then(([d, e, b]) => { setDashboard(d); setExpiring(e); setBelowMargin(b); }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-gray-400">Loading…</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Price List Reports</h1>

      {/* KPIs */}
      {dashboard && (
        <div className="grid grid-cols-5 gap-4">
          {[
            { label: "Active Lists", v: dashboard.active_price_lists, c: "text-green-700" },
            { label: "Draft", v: dashboard.draft_price_lists, c: "text-gray-700" },
            { label: "Pending Approval", v: dashboard.pending_approval, c: "text-yellow-700" },
            { label: "Expired (Active)", v: dashboard.expired_active_lists, c: "text-red-700" },
            { label: "Active Lines", v: dashboard.total_active_lines, c: "text-blue-700" },
          ].map((k) => (
            <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className={`text-2xl font-bold ${k.c}`}>{k.v}</div>
              <div className="text-xs text-gray-500 mt-1">{k.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Expiring Soon */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Expiring Price Lists (next 60 days)</h2>
        </div>
        {expiring.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">No price lists expiring in the next 60 days.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Code", "Name", "Type", "Currency", "Expires", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {expiring.map((h) => (
                <tr key={h.id} className="hover:bg-red-50/30">
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{h.price_list_code}</td>
                  <td className="px-4 py-3 font-medium text-blue-700">
                    <a href={`/dashboard/price-lists/${h.id}`} className="hover:underline">{h.price_list_name}</a>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PL_TYPE_COLORS[h.pl_type]}`}>{h.pl_type.replace(/_/g, " ")}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{h.currency}</td>
                  <td className="px-4 py-3 text-red-700 font-semibold text-sm">{h.valid_to}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${PL_STATUS_COLORS[h.status]}`}>{h.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Below Margin */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Below-Margin Price Lines (&lt;10% margin)</h2>
        </div>
        {belowMargin.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">No below-margin price lines detected.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-red-50 border-b border-red-200">
              <tr>
                {["Product ID", "Base Price", "Cost", "Margin %", "Price List"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-red-800 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {belowMargin.map((r, i) => (
                <tr key={i}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.product_id?.slice(0, 16)}…</td>
                  <td className="px-4 py-3 font-mono">{r.base_price?.toLocaleString()}</td>
                  <td className="px-4 py-3 font-mono text-gray-500">{r.cost_price?.toLocaleString()}</td>
                  <td className="px-4 py-3 font-bold text-red-700">{r.margin_pct}%</td>
                  <td className="px-4 py-3">
                    <a href={`/dashboard/price-lists/${r.header_id}`} className="text-blue-600 hover:underline text-xs">View</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Quick Report Links */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Approval Queue", href: "/dashboard/price-lists/approval-queue", icon: "⏳" },
          { label: "Discount Rules", href: "/dashboard/price-lists/discount-rules", icon: "🎯" },
          { label: "Margin Check", href: "/dashboard/price-lists/margin", icon: "📉" },
          { label: "Version Compare", href: "/dashboard/price-lists/compare", icon: "🔄" },
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
