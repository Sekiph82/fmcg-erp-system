"use client";
import { useState, useEffect } from "react";
import { dunningApi, DunningCase, DunningCaseStatus, CASE_STATUS_COLORS } from "@/lib/dunning";

export default function DunningCaseList() {
  const [cases, setCases] = useState<DunningCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [creditHoldFilter, setCreditHoldFilter] = useState<"" | "true" | "false">("");

  const load = () => {
    setLoading(true);
    dunningApi.listCases({
      status: statusFilter || undefined,
      credit_hold: creditHoldFilter === "" ? undefined : creditHoldFilter === "true",
      limit: 200,
    }).then(setCases).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter, creditHoldFilter]);

  const STATUSES: DunningCaseStatus[] = ["OPEN", "ON_HOLD", "DISPUTED", "PROMISE_TO_PAY", "RESOLVED", "CLOSED", "ESCALATED"];

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Dunning Cases</h1>
        <span className="text-sm text-gray-500">{cases.length} case{cases.length !== 1 ? "s" : ""}</span>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="flex flex-wrap gap-2">
          {["", ...STATUSES].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${statusFilter === s ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300 hover:border-blue-400"}`}>
              {s || "All Status"}
            </button>
          ))}
        </div>
        <select value={creditHoldFilter} onChange={(e) => setCreditHoldFilter(e.target.value as any)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
          <option value="">All Holds</option>
          <option value="true">Credit Hold Only</option>
          <option value="false">No Hold</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Case #", "Customer", "Total Overdue", "Level", "Status", "Hold", "Priority", "Next Action", "Actions"].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : cases.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">No cases found.</td></tr>
            ) : cases.map((c) => (
              <tr key={c.id} className={`hover:bg-gray-50 ${c.credit_hold_flag ? "bg-red-50/40" : ""}`}>
                <td className="px-4 py-3 font-medium text-blue-700">
                  <a href={`/dashboard/dunning/cases/${c.id}`} className="hover:underline">{c.case_no}</a>
                </td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{c.customer_id.slice(0, 12)}…</td>
                <td className="px-4 py-3 font-mono font-bold text-red-700">{Number(c.total_overdue_amount).toLocaleString()}</td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-bold">L{c.current_level_no}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${CASE_STATUS_COLORS[c.case_status]}`}>
                    {c.case_status.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {c.credit_hold_flag && <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-bold">HOLD</span>}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <div className="w-12 bg-gray-200 rounded-full h-1.5">
                      <div className="bg-red-500 h-1.5 rounded-full" style={{ width: `${c.priority_score}%` }}></div>
                    </div>
                    <span className="text-xs text-gray-500">{c.priority_score}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{c.next_action_date || "—"}</td>
                <td className="px-4 py-3">
                  <a href={`/dashboard/dunning/cases/${c.id}`} className="text-blue-600 hover:underline text-xs">Open</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
