"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { brApi, BRStatement, STATUS_COLOR } from "@/lib/bank_reconciliation";

export default function BRDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["br-dashboard"],
    queryFn: () => brApi.getDashboard(),
  });

  if (isLoading || !data) return (
    <div className="p-6 flex items-center gap-3 text-gray-400">
      <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      Loading…
    </div>
  );

  const kpis = [
    { label: "Bank Accounts",     value: data.total_accounts,   color: "text-blue-700" },
    { label: "In Reconciliation", value: data.statements_in_recon,     color: "text-yellow-700" },
    { label: "Unmatched Lines",   value: data.unmatched_items,  color: "text-red-700" },
    { label: "Partially Matched", value: data.partially_matched_items, color: "text-orange-700" },
    { label: "Unmatched Amount",  value: `${data.total_unmatched_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: "text-red-600" },
    { label: "Locked Statements", value: data.statements_locked, color: "text-purple-700" },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Bank Reconciliation</h1>
        <div className="flex gap-2">
          <Link href="/dashboard/bank-reconciliation/import" className="glow-button">
            Import Statement
          </Link>
          <Link href="/dashboard/bank-reconciliation/statements" className="glow-button-secondary">
            All Statements
          </Link>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="glow-card p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{k.label}</p>
            <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { href: "/dashboard/bank-reconciliation/open-items", label: "Open Items Aging",  icon: "⏱" },
          { href: "/dashboard/bank-reconciliation/balance",    label: "Bank vs Ledger",    icon: "⚖️" },
          { href: "/dashboard/bank-reconciliation/rules",      label: "Matching Rules",    icon: "⚡" },
          { href: "/dashboard/bank-reconciliation/ai",         label: "AI Insights",       icon: "🤖", badge: data.pending_ai_recs },
        ].map((q) => (
          <Link key={q.href} href={q.href} className="liquid-glass glow-hover p-4 flex items-center gap-3">
            <span className="text-2xl">{q.icon}</span>
            <div>
              <p className="text-sm font-medium text-gray-800">{q.label}</p>
              {q.badge ? <p className="text-xs text-yellow-600">{q.badge} pending</p> : null}
            </div>
          </Link>
        ))}
      </div>

      {/* Recent statements */}
      <div className="glass-table overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Recent Statements</h2>
          <Link href="/dashboard/bank-reconciliation/statements" className="text-xs text-blue-600 hover:underline">
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                {["Statement No", "Period", "Opening", "Closing", "Lines", "Status", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data.recent_statements ?? []).map((s: BRStatement) => (
                <tr key={s.id}>
                  <td className="px-4 py-3 font-mono text-xs font-medium">{s.statement_no}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">
                    {s.period_start_date} → {s.period_end_date}
                  </td>
                  <td className="px-4 py-3">
                    {Number(s.opening_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })} {s.statement_currency}
                  </td>
                  <td className="px-4 py-3 font-medium">
                    {Number(s.closing_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })} {s.statement_currency}
                  </td>
                  <td className="px-4 py-3">{s.total_lines}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[s.status]}`}>
                      {s.status.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/dashboard/bank-reconciliation/statements/${s.id}`}
                      className="text-blue-600 hover:underline text-xs">
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
              {data.recent_statements.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-gray-400">
                    <div className="flex flex-col items-center gap-2 opacity-60">
                      <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="text-sm">No statements yet.</span>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
