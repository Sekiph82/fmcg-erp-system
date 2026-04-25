"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { brApi, BRStatement, STATUS_COLOR } from "@/lib/bank_reconciliation";

export default function BRDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["br-dashboard"],
    queryFn: () => brApi.getDashboard(),
  });

  if (isLoading || !data) return <p className="p-6 text-gray-400">Loading…</p>;

  const kpis = [
    { label: "Bank Accounts", value: data.total_accounts, color: "text-blue-700" },
    { label: "In Reconciliation", value: data.statements_in_recon, color: "text-yellow-700" },
    { label: "Unmatched Lines", value: data.unmatched_items, color: "text-red-700" },
    { label: "Partially Matched", value: data.partially_matched_items, color: "text-orange-700" },
    { label: "Unmatched Amount", value: `${data.total_unmatched_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: "text-red-600" },
    { label: "Locked Statements", value: data.statements_locked, color: "text-purple-700" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Bank Reconciliation</h1>
        <div className="flex gap-2">
          <Link href="/dashboard/bank-reconciliation/import"
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
            Import Statement
          </Link>
          <Link href="/dashboard/bank-reconciliation/statements"
            className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200">
            All Statements
          </Link>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="bg-white border rounded-xl p-4">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: "/dashboard/bank-reconciliation/open-items", label: "Open Items Aging", icon: "⏱" },
          { href: "/dashboard/bank-reconciliation/balance", label: "Bank vs Ledger", icon: "⚖️" },
          { href: "/dashboard/bank-reconciliation/rules", label: "Matching Rules", icon: "⚡" },
          { href: "/dashboard/bank-reconciliation/ai", label: "AI Insights", icon: "🤖", badge: data.pending_ai_recs },
        ].map((q) => (
          <Link key={q.href} href={q.href}
            className="bg-white border rounded-xl p-4 hover:shadow-md transition flex items-center gap-3">
            <span className="text-2xl">{q.icon}</span>
            <div>
              <p className="text-sm font-medium text-gray-800">{q.label}</p>
              {q.badge ? <p className="text-xs text-yellow-600">{q.badge} pending</p> : null}
            </div>
          </Link>
        ))}
      </div>

      {/* Recent statements */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b bg-gray-50 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Recent Statements</h2>
          <Link href="/dashboard/bank-reconciliation/statements" className="text-xs text-blue-600 hover:underline">View all</Link>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["Statement No", "Period", "Opening", "Closing", "Lines", "Status", ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {data.recent_statements.map((s: BRStatement) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs font-medium">{s.statement_no}</td>
                <td className="px-4 py-2 text-xs text-gray-600">
                  {s.period_start_date} → {s.period_end_date}
                </td>
                <td className="px-4 py-2">{Number(s.opening_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })} {s.statement_currency}</td>
                <td className="px-4 py-2 font-medium">{Number(s.closing_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })} {s.statement_currency}</td>
                <td className="px-4 py-2">{s.total_lines}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[s.status]}`}>
                    {s.status.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <Link href={`/dashboard/bank-reconciliation/statements/${s.id}`}
                    className="text-blue-600 hover:underline text-xs">
                    Open
                  </Link>
                </td>
              </tr>
            ))}
            {data.recent_statements.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400 text-sm">No statements yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
