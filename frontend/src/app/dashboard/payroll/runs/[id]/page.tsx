"use client";

import { useCallback, useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { payrollKeApi, PayrollRun, PayrollLine, Payslip, MONTH_NAMES, STATUS_COLORS, PayrollInsight } from "@/lib/payrollKe";
import { RequirePermission } from "@/components/PermissionGuard";
import { useAuth } from "@/context/AuthContext";

export default function PayrollRunDetailPage() {
  return (
    <RequirePermission permission="payroll_ke.view">
      <PayrollRunDetailContent />
    </RequirePermission>
  );
}

function PayrollRunDetailContent() {
  const { hasPermission } = useAuth();
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  const [run, setRun] = useState<PayrollRun | null>(null);
  const [lines, setLines] = useState<PayrollLine[]>([]);
  const [payslips, setPayslips] = useState<Payslip[]>([]);
  const [anomaly, setAnomaly] = useState<PayrollInsight | null>(null);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [tab, setTab] = useState<"lines" | "payslips" | "ai">("lines");

  const reload = useCallback(async () => {
    const [r, ls, ps] = await Promise.all([
      payrollKeApi.getRun(runId),
      payrollKeApi.getRunLines(runId),
      payrollKeApi.getRunPayslips(runId),
    ]);
    setRun(r);
    setLines(ls);
    setPayslips(ps);
  }, [runId]);

  useEffect(() => {
    reload().finally(() => setLoading(false));
  }, [runId, reload]);

  const handleCalculate = async () => {
    setCalculating(true);
    try {
      await payrollKeApi.calculateRun(runId);
      await reload();
    } finally {
      setCalculating(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      await payrollKeApi.approveRun(runId);
      await reload();
    } finally {
      setApproving(false);
    }
  };

  const handleAI = async () => {
    setAiLoading(true);
    try {
      setAnomaly(await payrollKeApi.aiAnomaly(runId));
      setTab("ai");
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) return <div className="p-6 text-gray-400">Loading…</div>;
  if (!run) return <div className="p-6 text-red-600">Run not found</div>;

  const fmt = (v: number) => `KES ${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
  const canCalculatePayroll = hasPermission("payroll_ke.create");
  const canApprovePayroll = hasPermission("payroll_ke.approve");

  return (
    <div className="p-6 space-y-6">
      <div>
        <button onClick={() => router.back()} className="text-sm text-blue-600 hover:underline mb-4 inline-block">← Back</button>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{run.run_no}</h1>
            <p className="text-sm text-gray-500">{MONTH_NAMES[run.period_month]} {run.period_year} · {run.period_start} – {run.period_end}</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[run.status]}`}>{run.status}</span>
            {canCalculatePayroll && (run.status === "DRAFT" || run.status === "CALCULATED") && (
              <button onClick={handleCalculate} disabled={calculating} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50">
                {calculating ? "Calculating…" : "Calculate Payroll"}
              </button>
            )}
            {canApprovePayroll && run.status === "CALCULATED" && (
              <button onClick={handleApprove} disabled={approving} className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg disabled:opacity-50">
                {approving ? "Approving…" : "Approve & Generate Payslips"}
              </button>
            )}
            {lines.length > 0 && (
              <button onClick={handleAI} disabled={aiLoading} className="px-3 py-2 text-sm bg-purple-600 text-white rounded-lg disabled:opacity-50">
                {aiLoading ? "Analyzing…" : "AI Anomaly Check"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        {[
          { label: "Employees", value: run.employee_count },
          { label: "Total Gross", value: fmt(run.total_gross), color: "text-gray-800" },
          { label: "PAYE", value: fmt(run.total_paye), color: "text-red-600" },
          { label: "NHIF", value: fmt(run.total_nhif), color: "text-orange-600" },
          { label: "NSSF", value: fmt(run.total_nssf), color: "text-yellow-600" },
          { label: "Net Payroll", value: fmt(run.total_net), color: "text-green-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-lg border p-3">
            <p className="text-xs text-gray-500">{k.label}</p>
            <p className={`text-sm font-bold mt-0.5 ${k.color || "text-gray-800"}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b flex gap-4">
        {(["lines", "payslips", "ai"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-2 text-sm font-medium capitalize border-b-2 -mb-px ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t === "lines" ? `Lines (${lines.length})` : t === "payslips" ? `Payslips (${payslips.length})` : "AI Analysis"}
          </button>
        ))}
      </div>

      {/* Lines */}
      {tab === "lines" && (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 text-gray-600 uppercase">
              <tr>
                <th className="px-3 py-2 text-left">Employee</th>
                <th className="px-3 py-2 text-right">Basic</th>
                <th className="px-3 py-2 text-right">Housing</th>
                <th className="px-3 py-2 text-right">Transport</th>
                <th className="px-3 py-2 text-right">Gross</th>
                <th className="px-3 py-2 text-right">NSSF</th>
                <th className="px-3 py-2 text-right">Taxable</th>
                <th className="px-3 py-2 text-right">PAYE</th>
                <th className="px-3 py-2 text-right">NHIF</th>
                <th className="px-3 py-2 text-right">AHL</th>
                <th className="px-3 py-2 text-right">Net</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {lines.length === 0 ? (
                <tr><td colSpan={11} className="px-3 py-6 text-center text-gray-400">No lines. Click &quot;Calculate Payroll&quot; to run computation.</td></tr>
              ) : (
                lines.map((l) => (
                  <tr key={l.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <p className="font-medium">{l.employee_name || "—"}</p>
                      <p className="text-gray-400">{l.employee_code}</p>
                    </td>
                    <td className="px-3 py-2 text-right">{Number(l.basic_salary).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">{Number(l.housing_allowance).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">{Number(l.transport_allowance).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right font-semibold">{Number(l.gross_salary).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-yellow-600">{Number(l.nssf_employee).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">{Number(l.taxable_income).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-red-600">{Number(l.paye_amount).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-orange-600">{Number(l.nhif_amount).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">{Number(l.housing_levy).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right font-bold text-green-600">{Number(l.net_salary).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Payslips */}
      {tab === "payslips" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {payslips.length === 0 ? (
            <div className="col-span-2 py-8 text-center text-gray-400">No payslips generated. Approve the payroll run to generate payslips.</div>
          ) : (
            payslips.map((s) => (
              <div key={s.id} className="bg-white rounded-lg border p-5">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <p className="font-semibold text-gray-900">{s.employee_name}</p>
                    <p className="text-xs text-gray-500">{s.employee_code} · {s.department}</p>
                    <p className="text-xs text-gray-400 mt-0.5">Payslip for {MONTH_NAMES[s.period_month || 0]} {s.period_year}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-green-600">KES {Number(s.net_salary || 0).toLocaleString()}</p>
                    <p className="text-xs text-gray-400">Net Pay</p>
                  </div>
                </div>
                {s.components_json && (
                  <div className="grid grid-cols-2 gap-3 border-t pt-3">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1">EARNINGS</p>
                      {Object.entries(s.components_json.earnings || {}).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-xs py-0.5">
                          <span className="text-gray-600">{k}</span>
                          <span className="font-medium">{Number(v).toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1">DEDUCTIONS</p>
                      {Object.entries(s.components_json.deductions || {}).filter(([, v]) => Number(v) > 0).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-xs py-0.5">
                          <span className="text-gray-600">{k}</span>
                          <span className="font-medium text-red-600">{Number(v).toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* AI */}
      {tab === "ai" && anomaly && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-5">
          <h3 className="font-semibold text-purple-800 mb-3">{anomaly.agent}</h3>
          <ul className="space-y-2">
            {anomaly.insights.map((i, idx) => (
              <li key={idx} className="text-sm text-purple-700">• {i}</li>
            ))}
          </ul>
          {anomaly.details && anomaly.details.length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs border-t pt-2">
                <thead><tr className="text-gray-500"><th className="text-left py-1">Employee</th><th className="text-left py-1">Issue</th></tr></thead>
                <tbody>
                  {anomaly.details.map((d, i) => (
                    <tr key={i} className="border-t">
                      <td className="py-1">{d.employee || "—"}</td>
                      <td className="py-1">{d.issue}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
