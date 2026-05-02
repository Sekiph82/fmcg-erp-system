"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  lcApi, LC_STATUS_COLOR, COST_TYPE_LABEL, fmtCurrency, LCDashboard,
} from "@/lib/landed_cost";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const CHART_COLORS = [
  "#3b82f6","#f97316","#10b981","#8b5cf6","#ef4444",
];

export default function LandedCostDashboard() {
  const { data, isLoading, error } = useQuery<LCDashboard>({
    queryKey: ["lc-dashboard"],
    queryFn: () => lcApi.getDashboard(),
  });

  if (isLoading) return <div className="p-8 text-gray-500">Loading dashboard…</div>;
  if (error) return <div className="p-8 text-red-500">Failed to load dashboard. Ensure the database migration has been run (alembic upgrade heads).</div>;
  if (!data) return null;

  const statusCards = [
    { label: "Draft",     value: data.draft_count,     color: "bg-gray-100 text-gray-700" },
    { label: "Validated", value: data.validated_count, color: "bg-blue-100 text-blue-700" },
    { label: "Posted",    value: data.posted_count,    color: "bg-green-100 text-green-700" },
    { label: "Cancelled", value: data.cancelled_count, color: "bg-red-100 text-red-600" },
  ];

  const chartData = (data.top_cost_types ?? []).map((t) => ({
    name: COST_TYPE_LABEL[t.cost_type as keyof typeof COST_TYPE_LABEL] ?? t.cost_type,
    total: t.total,
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Landed Cost Allocation</h1>
        <Link
          href="/dashboard/landed-cost/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          + New Document
        </Link>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statusCards.map((c) => (
          <div key={c.label} className={`rounded-xl p-4 ${c.color}`}>
            <p className="text-xs font-medium uppercase tracking-wide opacity-70">{c.label}</p>
            <p className="text-3xl font-bold mt-1">{c.value}</p>
          </div>
        ))}
      </div>

      {/* Cost summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border rounded-xl p-5 space-y-1">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Documents</p>
          <p className="text-2xl font-bold text-gray-900">{data.total_documents}</p>
        </div>
        <div className="bg-white border rounded-xl p-5 space-y-1">
          <p className="text-xs text-gray-500 uppercase tracking-wide">LC Cost MTD (Base)</p>
          <p className="text-2xl font-bold text-green-700">{fmtCurrency(data.total_lc_cost_mtd)}</p>
        </div>
        <div className="bg-white border rounded-xl p-5 space-y-1">
          <p className="text-xs text-gray-500 uppercase tracking-wide">LC Cost YTD (Base)</p>
          <p className="text-2xl font-bold text-blue-700">{fmtCurrency(data.total_lc_cost_ytd)}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top cost types chart */}
        <div className="bg-white border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Top Cost Types (Posted)</h2>
          {chartData.length === 0 ? (
            <p className="text-sm text-gray-400">No posted data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 40, left: 8 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: unknown) => fmtCurrency(v as number | null | undefined)} />
                <Bar dataKey="total" radius={[4, 4, 0, 0]}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* AI alert */}
        <div className="bg-white border rounded-xl p-5 flex flex-col justify-between">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">AI Insights</h2>
          {data.pending_ai_recs > 0 ? (
            <div className="flex items-center gap-3 bg-yellow-50 border border-yellow-200 rounded-lg p-3 mt-2">
              <span className="text-yellow-500 text-xl">⚠</span>
              <div>
                <p className="text-sm font-medium text-yellow-800">
                  {data.pending_ai_recs} pending AI recommendation{data.pending_ai_recs > 1 ? "s" : ""}
                </p>
                <Link href="/dashboard/landed-cost/ai" className="text-xs text-yellow-700 underline">
                  Review now →
                </Link>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400 mt-2">No pending AI recommendations.</p>
          )}
          <Link
            href="/dashboard/landed-cost/ai"
            className="mt-4 text-sm text-blue-600 hover:underline"
          >
            View all AI recommendations →
          </Link>
        </div>
      </div>

      {/* Recent documents */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h2 className="text-sm font-semibold text-gray-700">Recent Documents</h2>
          <Link href="/dashboard/landed-cost/documents" className="text-xs text-blue-600 hover:underline">
            View all →
          </Link>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["LC No", "Vendor", "Currency", "Total (Base)", "Method", "Status", ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(data.recent_documents ?? []).map((doc) => (
              <tr key={doc.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{doc.lc_no}</td>
                <td className="px-4 py-2">{doc.vendor_name ?? "—"}</td>
                <td className="px-4 py-2">{doc.currency_code}</td>
                <td className="px-4 py-2 font-medium">{fmtCurrency(doc.total_lc_amount_base)}</td>
                <td className="px-4 py-2 text-gray-600">{doc.allocation_method.replace(/_/g, " ")}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LC_STATUS_COLOR[doc.status]}`}>
                    {doc.status}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <Link href={`/dashboard/landed-cost/${doc.id}`} className="text-blue-600 hover:underline text-xs">
                    View
                  </Link>
                </td>
              </tr>
            ))}
            {(data.recent_documents ?? []).length === 0 && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">No documents yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
