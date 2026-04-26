"use client";
import { useState, useEffect } from "react";
import { dunningApi, AgingRow } from "@/lib/dunning";

export default function AgingPage() {
  const [rows, setRows] = useState<AgingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    dunningApi.getAging().then(setRows).finally(() => setLoading(false));
  }, []);

  const filtered = rows.filter((r) =>
    !search || r.customer_name.toLowerCase().includes(search.toLowerCase()) || r.customer_code.toLowerCase().includes(search.toLowerCase())
  );

  const totalRow = filtered.reduce(
    (acc, r) => ({
      current: acc.current + r.current,
      overdue_1_7: acc.overdue_1_7 + r.overdue_1_7,
      overdue_8_14: acc.overdue_8_14 + r.overdue_8_14,
      overdue_15_30: acc.overdue_15_30 + r.overdue_15_30,
      overdue_31_60: acc.overdue_31_60 + r.overdue_31_60,
      overdue_61_90: acc.overdue_61_90 + r.overdue_61_90,
      overdue_90_plus: acc.overdue_90_plus + r.overdue_90_plus,
      total_overdue: acc.total_overdue + r.total_overdue,
    }),
    { current: 0, overdue_1_7: 0, overdue_8_14: 0, overdue_15_30: 0, overdue_31_60: 0, overdue_61_90: 0, overdue_90_plus: 0, total_overdue: 0 }
  );

  const fmt = (n: number) => n > 0 ? n.toLocaleString() : "—";

  const cellClass = (n: number, danger = false) =>
    `px-3 py-2.5 text-right font-mono text-xs ${n > 0 ? (danger ? "text-red-700 font-semibold" : "text-gray-800") : "text-gray-300"}`;

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Customer Aging Report</h1>
        <p className="text-sm text-gray-500 mt-1">Overdue balance distribution across aging buckets</p>
      </div>

      {/* Summary Buckets */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "1–7 Days", value: totalRow.overdue_1_7, color: "border-yellow-300" },
          { label: "8–30 Days", value: totalRow.overdue_8_14 + totalRow.overdue_15_30, color: "border-orange-300" },
          { label: "31–90 Days", value: totalRow.overdue_31_60 + totalRow.overdue_61_90, color: "border-red-300" },
          { label: "90+ Days", value: totalRow.overdue_90_plus, color: "border-red-500" },
        ].map((b) => (
          <div key={b.label} className={`bg-white rounded-xl border-2 ${b.color} p-4`}>
            <div className="text-xl font-bold text-gray-900">{b.value.toLocaleString()}</div>
            <div className="text-xs text-gray-500 mt-1">{b.label}</div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search customer…"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-64" />
        <span className="text-xs text-gray-500">{filtered.length} customers</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Customer</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Current</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-yellow-700 uppercase">1–7d</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-orange-600 uppercase">8–14d</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-orange-700 uppercase">15–30d</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-red-600 uppercase">31–60d</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-red-700 uppercase">61–90d</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-red-800 uppercase">90+d</th>
              <th className="px-3 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Total Overdue</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase">Hold</th>
              <th className="px-3 py-3 text-center text-xs font-semibold text-gray-600 uppercase">Pri</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={11} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={11} className="px-4 py-8 text-center text-gray-400">No overdue balances found.</td></tr>
            ) : filtered.map((row) => (
              <tr key={row.customer_id} className={`hover:bg-gray-50 ${row.credit_hold ? "bg-red-50" : ""}`}>
                <td className="px-4 py-2.5">
                  <div className="font-medium text-gray-900 text-sm">{row.customer_name}</div>
                  <div className="text-xs text-gray-400">{row.customer_code} · {row.currency}</div>
                </td>
                <td className={cellClass(row.current)}>{fmt(row.current)}</td>
                <td className={cellClass(row.overdue_1_7)}>{fmt(row.overdue_1_7)}</td>
                <td className={cellClass(row.overdue_8_14, true)}>{fmt(row.overdue_8_14)}</td>
                <td className={cellClass(row.overdue_15_30, true)}>{fmt(row.overdue_15_30)}</td>
                <td className={cellClass(row.overdue_31_60, true)}>{fmt(row.overdue_31_60)}</td>
                <td className={cellClass(row.overdue_61_90, true)}>{fmt(row.overdue_61_90)}</td>
                <td className={cellClass(row.overdue_90_plus, true)}>{fmt(row.overdue_90_plus)}</td>
                <td className="px-3 py-2.5 text-right font-mono text-sm font-bold text-red-700">{row.total_overdue.toLocaleString()}</td>
                <td className="px-3 py-2.5 text-center">
                  {row.credit_hold && <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-semibold">HOLD</span>}
                </td>
                <td className="px-3 py-2.5 text-center text-xs font-bold text-gray-700">{row.priority_score}</td>
              </tr>
            ))}
            {/* Totals row */}
            {filtered.length > 0 && (
              <tr className="bg-gray-100 font-bold">
                <td className="px-4 py-3 text-sm text-gray-900">TOTAL ({filtered.length} customers)</td>
                {[totalRow.current, totalRow.overdue_1_7, totalRow.overdue_8_14, totalRow.overdue_15_30,
                  totalRow.overdue_31_60, totalRow.overdue_61_90, totalRow.overdue_90_plus, totalRow.total_overdue].map((v, i) => (
                  <td key={i} className="px-3 py-3 text-right font-mono text-sm text-gray-800">{v.toLocaleString()}</td>
                ))}
                <td colSpan={2}></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
