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
    let result: any[] = [];
    if (tab === "employee") result = await expensesApi.reportByEmployee();
    else if (tab === "category") result = await expensesApi.reportByCategory();
    else result = await expensesApi.reportViolations();
    setData(result);
    setLoading(false);
  };

  useEffect(() => { load(); }, [tab]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "employee", label: "By Employee" },
    { id: "category", label: "By Category" },
    { id: "violations", label: "Policy Violations" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold">Expense Reports</h1>

      <div className="flex gap-2">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded text-sm border ${tab === t.id ? "bg-blue-600 text-white" : "bg-white"}`}>{t.label}</button>
        ))}
      </div>

      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="bg-white rounded-xl border overflow-hidden">
          {tab === "employee" && (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Employee ID</th>
                  <th className="px-4 py-3 text-right">Claims</th>
                  <th className="px-4 py-3 text-right">Total Claimed</th>
                  <th className="px-4 py-3 text-right">Total Approved</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{r.employee_id}</td>
                    <td className="px-4 py-3 text-right">{r.claim_count}</td>
                    <td className="px-4 py-3 text-right">{fmtCurrency(r.total_claimed || 0)}</td>
                    <td className="px-4 py-3 text-right">{fmtCurrency(r.total_approved || 0)}</td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No data</td></tr>}
              </tbody>
            </table>
          )}

          {tab === "category" && (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Category</th>
                  <th className="px-4 py-3 text-right">Lines</th>
                  <th className="px-4 py-3 text-right">Total Claimed</th>
                  <th className="px-4 py-3 text-right">Total Approved</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{r.category_name}</td>
                    <td className="px-4 py-3 text-right">{r.line_count}</td>
                    <td className="px-4 py-3 text-right">{fmtCurrency(r.total_claimed || 0)}</td>
                    <td className="px-4 py-3 text-right">{fmtCurrency(r.total_approved || 0)}</td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No data</td></tr>}
              </tbody>
            </table>
          )}

          {tab === "violations" && (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3 text-left">Line ID</th>
                  <th className="px-4 py-3 text-left">Receipt</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3 text-left">Severity</th>
                  <th className="px-4 py-3 text-left">Note</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{r.expense_line_id?.slice(-8)}</td>
                    <td className="px-4 py-3">{r.receipt_no || "—"}</td>
                    <td className="px-4 py-3 text-right">{fmtCurrency(r.claimed_amount)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${r.severity === "block" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
                        {r.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{r.note}</td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No violations</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
