"use client";
import { useQuery } from "@tanstack/react-query";
import { imApi } from "@/lib/invoice_match";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const COLORS = ["#ef4444","#f97316","#eab308","#8b5cf6","#10b981","#3b82f6","#06b6d4","#ec4899"];

export default function IMReportsPage() {
  const { data: mismatchData = [], isLoading: l1 } = useQuery<Record<string, unknown>[]>({
    queryKey: ["im-report-mismatch"],
    queryFn: () => imApi.reportMismatchSummary(),
  });

  const { data: supplierData = [], isLoading: l2 } = useQuery<Record<string, unknown>[]>({
    queryKey: ["im-report-supplier"],
    queryFn: () => imApi.reportSupplierAccuracy(),
  });

  const chartData = mismatchData.map((r) => ({
    name: String(r.match_status).replace(/_/g, " "),
    count: Number(r.count),
  }));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">3-Way Match Reports</h1>

      {/* Mismatch by type */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Match Status Distribution (All Lines)</h2>
        {l1 ? <p className="text-sm text-gray-400">Loading…</p> : chartData.length === 0 ? (
          <p className="text-sm text-gray-400">No data.</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData}>
                <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <table className="text-sm w-full self-start">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Count</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {mismatchData.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-xs">{String(r.match_status).replace(/_/g, " ")}</td>
                    <td className="px-4 py-2 font-medium">{String(r.count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Supplier accuracy */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Supplier Invoice Accuracy</h2>
        {l2 ? <p className="text-sm text-gray-400">Loading…</p> : supplierData.length === 0 ? (
          <p className="text-sm text-gray-400">No data.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Supplier ID", "Total Invoices", "Matched", "Mismatched", "Accuracy %"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {supplierData.map((r, i) => {
                const acc = Number(r.accuracy_pct);
                return (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs text-gray-500">
                      {String(r.supplier_id ?? "—").slice(0, 12)}…
                    </td>
                    <td className="px-4 py-2">{String(r.total)}</td>
                    <td className="px-4 py-2 text-green-700">{String(r.matched)}</td>
                    <td className="px-4 py-2 text-red-600">{String(r.mismatched)}</td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 w-24">
                          <div className={`h-2 rounded-full ${acc >= 90 ? "bg-green-500" : acc >= 70 ? "bg-yellow-500" : "bg-red-500"}`}
                               style={{ width: `${Math.min(acc, 100)}%` }} />
                        </div>
                        <span className={`text-xs font-semibold ${acc >= 90 ? "text-green-700" : acc >= 70 ? "text-yellow-700" : "text-red-700"}`}>
                          {acc.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
