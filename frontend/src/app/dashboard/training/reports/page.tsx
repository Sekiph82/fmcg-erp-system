"use client";
import { useEffect, useState } from "react";
import { trainingApi, EmployeeSkillRow, LEVEL_COLOR, CATEGORY_COLOR } from "@/lib/training";

type ReportTab = "skill_gaps" | "completion" | "cert_expiry" | "cost";

export default function TrainingReportsPage() {
  const [tab, setTab] = useState<ReportTab>("skill_gaps");
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [deptFilter, setDeptFilter] = useState("");
  const [certDays, setCertDays] = useState(60);

  const run = async () => {
    setLoading(true);
    setData(null);
    try {
      if (tab === "skill_gaps") setData(await trainingApi.reportSkillGaps(deptFilter || undefined));
      else if (tab === "completion") setData(await trainingApi.reportCompletion());
      else if (tab === "cert_expiry") setData(await trainingApi.reportCertExpiry(certDays));
      else setData(await trainingApi.reportTrainingCost());
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { run(); }, [tab]);

  const tabs: { key: ReportTab; label: string }[] = [
    { key: "skill_gaps", label: "Skill Gap Report" },
    { key: "completion", label: "Completion Report" },
    { key: "cert_expiry", label: "Cert Expiry Report" },
    { key: "cost", label: "Training Cost Report" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Training Reports</h1>

      <div className="flex gap-2 flex-wrap">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm rounded font-medium ${tab === t.key ? "bg-blue-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        {tab === "skill_gaps" && (
          <div className="flex gap-2 items-end">
            <div>
              <label className="text-xs text-gray-500">Department ID (optional)</label>
              <input className="block border rounded px-2 py-1 text-sm mt-1 w-40" value={deptFilter}
                onChange={(e) => setDeptFilter(e.target.value)} />
            </div>
            <button onClick={run} disabled={loading} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
              {loading ? "Loading…" : "Run"}
            </button>
          </div>
        )}

        {tab === "cert_expiry" && (
          <div className="flex gap-2 items-end">
            <div>
              <label className="text-xs text-gray-500">Expiring within (days)</label>
              <input type="number" min={7} max={365} className="block border rounded px-2 py-1 text-sm mt-1 w-24"
                value={certDays} onChange={(e) => setCertDays(Number(e.target.value))} />
            </div>
            <button onClick={run} disabled={loading} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
              {loading ? "Loading…" : "Run"}
            </button>
          </div>
        )}

        {loading && <p className="text-gray-500 text-sm">Loading…</p>}

        {!!data && tab === "skill_gaps" && (() => {
          const rows = data as EmployeeSkillRow[];
          return (
            <div>
              <p className="text-sm text-gray-500 mb-2">{rows.length} skill gaps identified</p>
              <table className="w-full text-sm">
                <thead className="bg-gray-50"><tr>
                  {["Employee","Skill","Category","Current","Required"].map(h=><th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>)}
                </tr></thead>
                <tbody className="divide-y">
                  {rows.map(r => (
                    <tr key={r.employee_skill_id}>
                      <td className="px-3 py-2 font-medium">{r.employee_name ?? r.employee_id}</td>
                      <td className="px-3 py-2">{r.skill_name}</td>
                      <td className="px-3 py-2"><span className={`rounded-full px-2 py-0.5 text-xs ${CATEGORY_COLOR[r.skill_category]}`}>{r.skill_category}</span></td>
                      <td className="px-3 py-2">{r.current_level ? <span className={`rounded px-1 text-xs ${LEVEL_COLOR[r.current_level]}`}>{r.current_level}</span> : <span className="text-gray-400">None</span>}</td>
                      <td className="px-3 py-2">{r.required_level ? <span className={`rounded px-1 text-xs ${LEVEL_COLOR[r.required_level]}`}>{r.required_level}</span> : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.length === 0 && <p className="text-gray-400 text-center py-4 text-sm">No gaps found.</p>}
            </div>
          );
        })()}

        {!!data && tab === "completion" && (() => {
          const d = data as { total: number; completed: number; overdue: number; pending: number; completion_rate_pct: number };
          return (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "Total", value: d.total },
                { label: "Completed", value: d.completed, color: "text-green-700" },
                { label: "Overdue", value: d.overdue, color: "text-red-700" },
                { label: "Completion Rate", value: `${d.completion_rate_pct}%` },
              ].map(k => (
                <div key={k.label} className="bg-gray-50 rounded p-3 text-center">
                  <p className={`text-2xl font-bold ${k.color ?? "text-gray-900"}`}>{k.value}</p>
                  <p className="text-xs text-gray-500">{k.label}</p>
                </div>
              ))}
            </div>
          );
        })()}

        {!!data && tab === "cert_expiry" && (() => {
          const rows = data as { certification_id: string; employee_id: string; employee_name: string | null; certificate_name: string; expiry_date: string | null; days_to_expiry: number | null; status: string }[];
          return (
            <table className="w-full text-sm">
              <thead className="bg-gray-50"><tr>
                {["Employee","Certificate","Expiry","Days Left","Status"].map(h=><th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>)}
              </tr></thead>
              <tbody className="divide-y">
                {rows.map(r => (
                  <tr key={r.certification_id}>
                    <td className="px-3 py-2 font-medium">{r.employee_name ?? r.employee_id}</td>
                    <td className="px-3 py-2">{r.certificate_name}</td>
                    <td className="px-3 py-2 text-gray-600">{r.expiry_date ?? "—"}</td>
                    <td className={`px-3 py-2 font-semibold ${r.days_to_expiry != null && r.days_to_expiry <= 0 ? "text-red-600" : "text-yellow-700"}`}>
                      {r.days_to_expiry != null ? (r.days_to_expiry <= 0 ? "EXPIRED" : `${r.days_to_expiry}d`) : "—"}
                    </td>
                    <td className="px-3 py-2 capitalize">{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          );
        })()}

        {!!data && tab === "cost" && (() => {
          const rows = data as { training_id: string; training_name: string; cost_per_head: number; enrolled_count: number; total_cost: number }[];
          const total = rows.reduce((s, r) => s + r.total_cost, 0);
          return (
            <div>
              <p className="text-sm font-semibold text-gray-700 mb-2">Total Training Cost: KES {total.toLocaleString()}</p>
              <table className="w-full text-sm">
                <thead className="bg-gray-50"><tr>
                  {["Program","Cost/Head","Enrolled","Total Cost"].map(h=><th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>)}
                </tr></thead>
                <tbody className="divide-y">
                  {rows.map(r => (
                    <tr key={r.training_id}>
                      <td className="px-3 py-2 font-medium">{r.training_name}</td>
                      <td className="px-3 py-2 text-gray-600">KES {r.cost_per_head.toLocaleString()}</td>
                      <td className="px-3 py-2 text-center">{r.enrolled_count}</td>
                      <td className="px-3 py-2 font-semibold text-blue-700">KES {r.total_cost.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
