"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  imApi, IMDashboard, MATCH_STATUS_COLOR, MatchOverallStatus,
} from "@/lib/invoice_match";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const COLORS = ["#ef4444","#f97316","#eab308","#8b5cf6","#06b6d4","#10b981"];

export default function InvoiceMatchDashboard() {
  const { data, isLoading, error } = useQuery<IMDashboard>({
    queryKey: ["im-dashboard"],
    queryFn: () => imApi.getDashboard(),
  });

  if (isLoading) return <div className="p-8 text-gray-500">Loading…</div>;
  if (error) return <div className="p-8 text-red-500">Failed to load dashboard. Ensure the database migration has been run (alembic upgrade heads).</div>;
  if (!data) return null;

  const kpis = [
    { label: "Fully Matched",     value: data.fully_matched,   color: "bg-green-100 text-green-700" },
    { label: "In Tolerance",      value: data.within_tolerance, color: "bg-teal-100 text-teal-700" },
    { label: "Mismatched",        value: data.mismatched,       color: "bg-orange-100 text-orange-700" },
    { label: "Blocked",           value: data.blocked,          color: "bg-red-100 text-red-700" },
    { label: "Pending Review",    value: data.pending_review,   color: "bg-yellow-100 text-yellow-700" },
    { label: "Duplicate Suspected",value: data.duplicate_suspected, color: "bg-purple-100 text-purple-700" },
  ];

  const chartData = (data.mismatch_by_type ?? []).map((m) => ({
    name: String(m.type).replace(/_/g, " "),
    count: m.count,
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">3-Way Invoice Matching</h1>
        <div className="flex gap-2">
          <Link href="/dashboard/invoice-match/review-queue"
            className="px-3 py-1.5 text-sm border rounded-lg bg-white hover:bg-gray-50">
            Review Queue {data.pending_review > 0 && <span className="ml-1 text-yellow-600 font-bold">({data.pending_review})</span>}
          </Link>
          <Link href="/dashboard/invoice-match/matches"
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
            All Matches
          </Link>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {kpis.map((k) => (
          <div key={k.label} className={`rounded-xl p-4 ${k.color}`}>
            <p className="text-xs font-medium opacity-70">{k.label}</p>
            <p className="text-3xl font-bold mt-1">{k.value}</p>
          </div>
        ))}
      </div>

      {/* Payment readiness */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border rounded-xl p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Matches</p>
          <p className="text-3xl font-bold text-gray-900">{data.total_matches}</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <p className="text-xs text-green-600 uppercase tracking-wide font-medium">Payable</p>
          <p className="text-3xl font-bold text-green-700">{data.payable_count}</p>
          <p className="text-xs text-green-500 mt-1">Cleared for payment</p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <p className="text-xs text-red-600 uppercase tracking-wide font-medium">On Hold</p>
          <p className="text-3xl font-bold text-red-700">{data.on_hold_count}</p>
          <Link href="/dashboard/invoice-match/blocked" className="text-xs text-red-500 hover:underline">
            View blocked →
          </Link>
        </div>
      </div>

      {/* Mismatch chart + AI alert */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Mismatch by Type</h2>
          {chartData.length === 0 ? (
            <p className="text-sm text-gray-400">No mismatches recorded.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData}>
                <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-15} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-white border rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Quick Links</h2>
          {[
            { href: "/dashboard/invoice-match/duplicates", label: "Duplicate Suspicion Queue", count: data.duplicate_suspected, color: "text-purple-600" },
            { href: "/dashboard/invoice-match/blocked", label: "Blocked Invoices", count: data.on_hold_count, color: "text-red-600" },
            { href: "/dashboard/invoice-match/review-queue", label: "Pending Review", count: data.pending_review, color: "text-yellow-600" },
            { href: "/dashboard/invoice-match/ai", label: "AI Recommendations", count: data.pending_ai_recs, color: "text-purple-600" },
          ].map((q) => (
            <Link key={q.href} href={q.href}
              className="flex items-center justify-between px-3 py-2.5 border rounded-lg hover:bg-gray-50">
              <span className="text-sm text-gray-700">{q.label}</span>
              {q.count > 0 && <span className={`text-sm font-bold ${q.color}`}>{q.count}</span>}
            </Link>
          ))}
        </div>
      </div>

      {/* Recent matches */}
      <div className="bg-white border rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h2 className="text-sm font-semibold text-gray-700">Recent Matches</h2>
          <Link href="/dashboard/invoice-match/matches" className="text-xs text-blue-600 hover:underline">View all →</Link>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["Match No", "Invoice No", "Date", "Total", "Status", "Payable", ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(data.recent_matches ?? []).map((m) => (
              <tr key={m.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{m.match_no}</td>
                <td className="px-4 py-2 text-gray-600">{m.invoice_no ?? "—"}</td>
                <td className="px-4 py-2 text-gray-500 text-xs">{m.invoice_date ?? "—"}</td>
                <td className="px-4 py-2 font-medium">{Number(m.invoice_total).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${MATCH_STATUS_COLOR[m.overall_status]}`}>
                    {m.overall_status.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <span className={`text-xs font-medium ${m.is_payable ? "text-green-600" : "text-red-600"}`}>
                    {m.is_payable ? "✓ Payable" : "✗ Hold"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <Link href={`/dashboard/invoice-match/${m.id}`} className="text-blue-600 hover:underline text-xs">View</Link>
                </td>
              </tr>
            ))}
            {(data.recent_matches ?? []).length === 0 && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">No matches yet. Run a match from an invoice.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
