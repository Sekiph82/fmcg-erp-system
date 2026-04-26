"use client";
import { useState, useEffect } from "react";
import { dunningApi, DunningDashboard, DunningCase, CASE_STATUS_COLORS, DunningCaseStatus } from "@/lib/dunning";

export default function DunningDashboardPage() {
  const [kpis, setKpis] = useState<DunningDashboard | null>(null);
  const [cases, setCases] = useState<DunningCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      dunningApi.getDashboard(),
      dunningApi.listCases({ limit: 10 }),
    ]).then(([k, c]) => { setKpis(k); setCases(c); }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const runDetection = async () => {
    setRunning(true);
    const res = await dunningApi.runDetection();
    setRunning(false);
    load();
    alert(`Detection complete: ${res.cases_created} cases created, ${res.cases_updated} updated, ${res.overdue_invoices} overdue invoices found.`);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dunning & Collections</h1>
          <p className="text-sm text-gray-500 mt-1">Automated overdue receivables management — reminders, holds, escalations</p>
        </div>
        <div className="flex gap-3">
          <button onClick={runDetection} disabled={running}
            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50">
            {running ? "Scanning…" : "Run Overdue Detection"}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {kpis && (
        <div className="grid grid-cols-3 gap-4 lg:grid-cols-6">
          {[
            { label: "Open Cases", value: kpis.open_cases, color: "text-blue-700" },
            { label: "Total Overdue", value: `KES ${kpis.total_overdue_amount.toLocaleString()}`, color: "text-red-700" },
            { label: "Credit Holds", value: kpis.credit_hold_count, color: "text-orange-700" },
            { label: "Disputed Cases", value: kpis.disputed_cases, color: "text-yellow-700" },
            { label: "Open PTPs", value: kpis.open_ptps, color: "text-purple-700" },
            { label: "Broken PTPs", value: kpis.broken_ptps, color: "text-red-700" },
          ].map((k) => (
            <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className={`text-2xl font-bold ${k.color}`}>{k.value}</div>
              <div className="text-xs text-gray-500 mt-1">{k.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Quick Links */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Aging Report", href: "/dashboard/dunning/aging", icon: "📊", desc: "Customer-level aging buckets" },
          { label: "Collector Queue", href: "/dashboard/dunning/workqueue", icon: "📋", desc: "Today's action queue" },
          { label: "Credit Holds", href: "/dashboard/dunning/credit-holds", icon: "🔒", desc: "Review & release holds" },
          { label: "Policies", href: "/dashboard/dunning/policies", icon: "⚙️", desc: "Configure dunning rules" },
        ].map((l) => (
          <a key={l.label} href={l.href}
            className="bg-white rounded-xl border border-gray-200 p-4 hover:border-blue-400 hover:bg-blue-50 transition">
            <div className="text-2xl mb-2">{l.icon}</div>
            <div className="font-semibold text-gray-900 text-sm">{l.label}</div>
            <div className="text-xs text-gray-500 mt-1">{l.desc}</div>
          </a>
        ))}
      </div>

      {/* Top Priority Cases */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">Top Priority Cases</h2>
          <a href="/dashboard/dunning/cases" className="text-blue-600 text-sm hover:underline">View all →</a>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Case #", "Customer", "Overdue Amount", "Level", "Status", "Credit Hold", "Priority", "Next Action"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : cases.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No cases. Run overdue detection to generate cases.</td></tr>
            ) : cases.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-blue-700">
                  <a href={`/dashboard/dunning/cases/${c.id}`}>{c.case_no}</a>
                </td>
                <td className="px-4 py-3 text-gray-600 font-mono text-xs">{c.customer_id.slice(0, 8)}…</td>
                <td className="px-4 py-3 font-mono font-semibold">{Number(c.total_overdue_amount).toLocaleString()}</td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">L{c.current_level_no}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${CASE_STATUS_COLORS[c.case_status]}`}>{c.case_status}</span>
                </td>
                <td className="px-4 py-3">
                  {c.credit_hold_flag && <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-semibold">HOLD</span>}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-red-500 h-1.5 rounded-full" style={{ width: `${c.priority_score}%` }}></div>
                    </div>
                    <span className="text-xs text-gray-500">{c.priority_score}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{c.next_action_date || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
