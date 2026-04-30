"use client";
import { useEffect, useState } from "react";
import { expensesApi, fmtCurrency } from "@/lib/expenses";

type Tab = "employee" | "category" | "violations";

export default function ExpenseReportsPage() {
  const [tab, setTab] = useState<Tab>("employee");
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    if (tab === "employee") setData(await expensesApi.reportByEmployee());
    else if (tab === "category") setData(await expensesApi.reportByCategory());
    else setData(await expensesApi.reportViolations());
    setLoading(false);
  };
  useEffect(() => { load(); }, [tab]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "employee", label: "By Employee" },
    { id: "category", label: "By Category" },
    { id: "violations", label: "Policy Violations" },
  ];

  return (
    <div className="p-6 space-y-5 text-slate-200">
      <h1 className="text-xl font-bold text-white">Expense Reports</h1>

      <div className="flex gap-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${tab === t.id ? "bg-indigo-600 border-indigo-500 text-white" : "border-white/[0.08] text-slate-400 hover:border-white/20"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <p className="text-slate-500 text-sm">Loading…</p> : (
        <div className="rounded-xl border border-white/[0.07] bg-[#0d1829] overflow-hidden">
          {tab === "employee" && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-white/[0.07]">
                {["Employee ID", "Claims", "Total Claimed", "Total Approved"].map((h) => (
                  <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h !== "Employee ID" && h !== "Claims" ? "text-right" : "text-left"}`}>{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{r.employee_id}</td>
                    <td className="px-4 py-3 text-white">{r.claim_count}</td>
                    <td className="px-4 py-3 text-right text-white">{fmtCurrency(r.total_claimed || 0)}</td>
                    <td className="px-4 py-3 text-right text-emerald-400">{fmtCurrency(r.total_approved || 0)}</td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-600">No data</td></tr>}
              </tbody>
            </table>
          )}
          {tab === "category" && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-white/[0.07]">
                {["Category", "Lines", "Total Claimed", "Total Approved"].map((h) => (
                  <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h !== "Category" && h !== "Lines" ? "text-right" : "text-left"}`}>{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                    <td className="px-4 py-3 text-white font-medium">{r.category_name}</td>
                    <td className="px-4 py-3 text-slate-400">{r.line_count}</td>
                    <td className="px-4 py-3 text-right text-white">{fmtCurrency(r.total_claimed || 0)}</td>
                    <td className="px-4 py-3 text-right text-emerald-400">{fmtCurrency(r.total_approved || 0)}</td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-slate-600">No data</td></tr>}
              </tbody>
            </table>
          )}
          {tab === "violations" && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-white/[0.07]">
                {["Line ID", "Receipt", "Amount", "Severity", "Note"].map((h) => (
                  <th key={h} className={`px-4 py-3 text-[10px] text-slate-500 uppercase tracking-widest ${h === "Amount" ? "text-right" : "text-left"}`}>{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {data.map((r, i) => (
                  <tr key={i} className="border-b border-white/[0.05] hover:bg-white/[0.02]">
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{r.expense_line_id?.slice(-8)}</td>
                    <td className="px-4 py-3 text-slate-400">{r.receipt_no || "—"}</td>
                    <td className="px-4 py-3 text-right text-white">{fmtCurrency(r.claimed_amount)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${r.severity === "block" ? "bg-red-500/20 text-red-300" : "bg-amber-500/20 text-amber-300"}`}>{r.severity}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{r.note}</td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-600">No violations</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
