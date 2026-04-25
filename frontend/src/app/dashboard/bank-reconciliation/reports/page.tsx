"use client";
import { useQuery } from "@tanstack/react-query";
import { brApi } from "@/lib/bank_reconciliation";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const COLORS = ["#ef4444", "#f97316", "#eab308", "#10b981", "#3b82f6", "#8b5cf6"];

export default function BRReportsPage() {
  const { data: unreconciled = [], isLoading: l1 } = useQuery<Record<string, unknown>[]>({
    queryKey: ["br-report-unrecon"],
    queryFn: () => brApi.reportUnreconciled(),
  });

  const { data: aged = [], isLoading: l2 } = useQuery<Record<string, unknown>[]>({
    queryKey: ["br-report-aged"],
    queryFn: () => brApi.reportAgedOpenItems(),
  });

  const agedChart = aged.map((r) => ({
    bucket: String(r.bucket),
    count: Number(r.count),
    total: Number(r.total),
  }));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Bank Reconciliation Reports</h1>

      {/* Aged open items */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Aged Open Items</h2>
        {l2 ? <p className="text-sm text-gray-400">Loading…</p> : agedChart.length === 0 ? (
          <p className="text-green-600 text-sm">✓ No open items.</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={agedChart}>
                <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })} />
                <Bar dataKey="total" name="Unmatched Amt" radius={[4, 4, 0, 0]}>
                  {agedChart.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <table className="text-sm w-full self-start">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Bucket</th>
                  <th className="px-4 py-2 text-left">Lines</th>
                  <th className="px-4 py-2 text-left">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {agedChart.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-xs">{r.bucket}</td>
                    <td className="px-4 py-2">{r.count}</td>
                    <td className={`px-4 py-2 font-medium ${r.total > 0 ? "text-red-600" : "text-green-600"}`}>
                      {r.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Unreconciled by statement */}
      <div className="bg-white border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Unreconciled Items by Statement</h2>
        {l1 ? <p className="text-sm text-gray-400">Loading…</p> : unreconciled.length === 0 ? (
          <p className="text-green-600 text-sm">✓ All statements fully reconciled.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Account", "Statement", "Period End", "Unmatched Lines", "Unmatched Total"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {unreconciled.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-600">{String(r.account_name)}</td>
                  <td className="px-4 py-2 font-mono text-xs font-medium">{String(r.statement_no)}</td>
                  <td className="px-4 py-2 text-xs">{String(r.period_end_date)}</td>
                  <td className="px-4 py-2">{String(r.unmatched_lines)}</td>
                  <td className="px-4 py-2 font-medium text-red-600">
                    {Number(r.unmatched_total).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
