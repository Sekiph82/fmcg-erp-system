"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { useState, useEffect } from "react";
import { payrollKeApi, PayrollRun, STATUS_COLORS, MONTH_NAMES, PayrollInsight } from "@/lib/payrollKe";
import Link from "next/link";
import { RequirePermission } from "@/components/PermissionGuard";
import { useAuth } from "@/context/AuthContext";

function PayrollDashboardLegacy() {
  return (
    <RequirePermission permission="payroll_ke.view">
      <PayrollDashboardContent />
    </RequirePermission>
  );
}

function PayrollDashboardContent() {
  const { hasPermission } = useAuth();
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [compliance, setCompliance] = useState<PayrollInsight | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [seedMsg, setSeedMsg] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({
    period_month: new Date().getMonth() + 1,
    period_year: new Date().getFullYear(),
    notes: "",
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    payrollKeApi.listRuns().then(setRuns).finally(() => setLoading(false));
  }, []);

  const handleSeed = async () => {
    const res = await payrollKeApi.seedRates(2024);
    setSeedMsg(res.message);
  };

  const handleCompliance = async () => {
    setAiLoading(true);
    try {
      setCompliance(await payrollKeApi.aiCompliance());
    } finally {
      setAiLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const year = createForm.period_year;
      const month = createForm.period_month;
      const startDay = new Date(year, month - 1, 1).toISOString().split("T")[0];
      const endDay = new Date(year, month, 0).toISOString().split("T")[0];
      await payrollKeApi.createRun({
        period_month: month,
        period_year: year,
        period_start: startDay,
        period_end: endDay,
        notes: createForm.notes || undefined,
      });
      setShowCreate(false);
      const updated = await payrollKeApi.listRuns();
      setRuns(updated);
    } finally {
      setCreating(false);
    }
  };

  const latest = runs[0];
  const totalNet = runs.filter((r) => r.status === "APPROVED" || r.status === "PAID")
    .reduce((s, r) => s + r.total_net, 0);
  const canCreatePayroll = hasPermission("payroll_ke.create");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kenya Payroll</h1>
          <p className="text-sm text-gray-500 mt-1">PAYE · NHIF · NSSF · AHL — Finance Act 2023/2024</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link href="/dashboard/payroll/profiles" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">Payroll Profiles</Link>
          <Link href="/dashboard/payroll/reports" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">Reports</Link>
          {canCreatePayroll && (
            <button onClick={handleSeed} className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg">Seed 2024 Rates</button>
          )}
          <button onClick={handleCompliance} disabled={aiLoading} className="px-3 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50">
            {aiLoading ? "Checking…" : "Compliance Check"}
          </button>
          {canCreatePayroll && (
            <button onClick={() => setShowCreate(true)} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              + New Payroll Run
            </button>
          )}
        </div>
      </div>

      {seedMsg && <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2 text-sm text-green-700">{seedMsg}</div>}

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Runs", value: runs.length },
          { label: "Latest Employees", value: latest?.employee_count ?? "—", color: "text-blue-600" },
          { label: "Latest Net Payroll", value: latest ? `KES ${Number(latest.total_net).toLocaleString()}` : "—", color: "text-green-600" },
          { label: "YTD Net Paid", value: `KES ${totalNet.toLocaleString()}`, color: "text-purple-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-xl font-bold mt-1 ${k.color || "text-gray-800"}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Compliance AI */}
      {compliance && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-purple-800 mb-2">{compliance.agent}</h3>
          <ul className="space-y-1">
            {compliance.insights.map((i, idx) => (
              <li key={idx} className="text-xs text-purple-700">• {i}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Runs table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Run No</th>
              <th className="px-4 py-3 text-left">Period</th>
              <th className="px-4 py-3 text-right">Employees</th>
              <th className="px-4 py-3 text-right">Gross</th>
              <th className="px-4 py-3 text-right">PAYE</th>
              <th className="px-4 py-3 text-right">NHIF</th>
              <th className="px-4 py-3 text-right">NSSF</th>
              <th className="px-4 py-3 text-right">Net</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : runs.length === 0 ? (
              <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No payroll runs yet. Seed rates first, then create a run.</td></tr>
            ) : (
              runs.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs font-semibold">{r.run_no}</td>
                  <td className="px-4 py-2">{MONTH_NAMES[r.period_month]} {r.period_year}</td>
                  <td className="px-4 py-2 text-right">{r.employee_count}</td>
                  <td className="px-4 py-2 text-right">{Number(r.total_gross).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-red-600">{Number(r.total_paye).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-orange-600">{Number(r.total_nhif).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right text-yellow-600">{Number(r.total_nssf).toLocaleString()}</td>
                  <td className="px-4 py-2 text-right font-semibold text-green-600">{Number(r.total_net).toLocaleString()}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[r.status]}`}>{r.status}</span>
                  </td>
                  <td className="px-4 py-2">
                    <Link href={`/dashboard/payroll/runs/${r.id}`} className="text-blue-600 hover:underline text-xs">Open</Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Run Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-semibold mb-4">New Payroll Run</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Month *</label>
                  <select required value={createForm.period_month} onChange={(e) => setCreateForm({ ...createForm, period_month: parseInt(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm">
                    {MONTH_NAMES.slice(1).map((m, i) => (<option key={i + 1} value={i + 1}>{m}</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Year *</label>
                  <input required type="number" value={createForm.period_year} onChange={(e) => setCreateForm({ ...createForm, period_year: parseInt(e.target.value) })} className="w-full border rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Notes</label>
                <textarea value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
              </div>
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 py-2 border rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={creating} className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50">
                  {creating ? "Creating…" : "Create Run"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

const PayrollProfilesPage = dynamic(() => import("@/app/dashboard/payroll/profiles/page"), { ssr: false });
const PayrollReportsPage  = dynamic(() => import("@/app/dashboard/payroll/reports/page"),  { ssr: false });

export default function PayrollDashboard() {
  const tabs = [
    { key: "overview",  label: "Overview",  permission: "payroll_ke.view", content: <PayrollDashboardContent /> },
    { key: "profiles",  label: "Profiles",  permission: "payroll_ke.view", content: <PayrollProfilesPage /> },
    { key: "reports",   label: "Reports",   permission: "payroll_ke.view", content: <PayrollReportsPage /> },
  ];
  return (
    <ModuleWorkspace
      title="Kenya Payroll"
      description="Payroll runs, employee profiles, PAYE, NHIF, NSSF, reports"
      permission="payroll_ke.view"
      tabs={tabs}
      defaultTab="overview"
    />
  );
}
