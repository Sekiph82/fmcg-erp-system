"use client";
import { useState, useEffect } from "react";
import { dunningApi, CASE_STATUS_COLORS, DunningCaseStatus } from "@/lib/dunning";

export default function WorkQueuePage() {
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    dunningApi.getWorkqueue().then(setQueue).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const checkPTPs = async () => {
    const res = await dunningApi.checkBrokenPTPs();
    alert(`${res.broken_ptps_flagged} broken PTPs flagged.`);
    load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Collector Work Queue</h1>
          <p className="text-sm text-gray-500 mt-1">Priority-sorted collection cases for today&apos;s action</p>
        </div>
        <div className="flex gap-2">
          <button onClick={checkPTPs} className="px-3 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600">
            Check Broken PTPs
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Cases", value: queue.length, color: "text-blue-700" },
          { label: "Credit Holds", value: queue.filter((c) => c.credit_hold).length, color: "text-red-700" },
          { label: "Open PTPs", value: queue.reduce((s, c) => s + (c.open_ptps || 0), 0), color: "text-purple-700" },
          { label: "Escalated", value: queue.filter((c) => c.status === "ESCALATED").length, color: "text-orange-700" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className={`text-2xl font-bold ${k.color}`}>{k.value}</div>
            <div className="text-xs text-gray-500 mt-1">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {["Pri", "Case #", "Customer", "Overdue Amt", "Oldest Due", "Level", "Status", "Hold", "PTPs", "Next Action", "Actions"].map((h) => (
                <th key={h} className="px-3 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={11} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : queue.length === 0 ? (
              <tr><td colSpan={11} className="px-4 py-8 text-center text-gray-400">Queue is empty. Run overdue detection first.</td></tr>
            ) : queue.map((c) => (
              <tr key={c.case_id} className={`hover:bg-gray-50 ${c.credit_hold ? "bg-red-50/30" : ""}`}>
                <td className="px-3 py-3">
                  <div className={`text-xs font-bold px-1.5 py-0.5 rounded ${c.priority_score >= 70 ? "bg-red-100 text-red-700" : c.priority_score >= 40 ? "bg-yellow-100 text-yellow-700" : "bg-gray-100 text-gray-600"}`}>
                    {c.priority_score}
                  </div>
                </td>
                <td className="px-3 py-3 font-medium text-blue-700">
                  <a href={`/dashboard/dunning/cases/${c.case_id}`} className="hover:underline">{c.case_no}</a>
                </td>
                <td className="px-3 py-3">
                  <div className="font-medium text-gray-900 text-sm">{c.customer_name}</div>
                  <div className="text-xs text-gray-400">{c.customer_code}</div>
                </td>
                <td className="px-3 py-3 font-mono font-semibold text-red-700">{c.total_overdue?.toLocaleString()}</td>
                <td className="px-3 py-3 text-gray-500 text-xs">{c.oldest_due_date || "—"}</td>
                <td className="px-3 py-3 text-center">
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-bold">L{c.current_level}</span>
                </td>
                <td className="px-3 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${CASE_STATUS_COLORS[c.status as DunningCaseStatus] || "bg-gray-100 text-gray-700"}`}>
                    {c.status?.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="px-3 py-3">
                  {c.credit_hold && <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-bold">HOLD</span>}
                </td>
                <td className="px-3 py-3 text-center">
                  {c.open_ptps > 0 && <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs">{c.open_ptps} PTP</span>}
                </td>
                <td className="px-3 py-3 text-gray-500 text-xs">{c.next_action_date || "—"}</td>
                <td className="px-3 py-3">
                  <a href={`/dashboard/dunning/cases/${c.case_id}`} className="text-blue-600 hover:underline text-xs">Open</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
