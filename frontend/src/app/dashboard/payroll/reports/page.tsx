"use client";

import { useCallback, useState, useEffect } from "react";
import { payrollKeApi, PayrollRun, MONTH_NAMES } from "@/lib/payrollKe";

export default function PayrollReportsPage() {
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [selectedRun, setSelectedRun] = useState("");
  const [tab, setTab] = useState<"paye" | "nhif" | "nssf" | "summary">("summary");
  const [reportData, setReportData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    payrollKeApi.listRuns().then((rs) => {
      const approved = rs.filter((r) => ["APPROVED", "PAID", "CALCULATED"].includes(r.status));
      setRuns(approved);
      if (approved.length > 0) setSelectedRun(approved[0].id);
    });
  }, []);

  const loadReport = useCallback(async () => {
    if (!selectedRun) return;
    setLoading(true);
    try {
      let data: any[] = [];
      if (tab === "paye") data = await payrollKeApi.payeReport(selectedRun);
      else if (tab === "nhif") data = await payrollKeApi.nhifReport(selectedRun);
      else if (tab === "nssf") data = await payrollKeApi.nssfReport(selectedRun);
      else data = await payrollKeApi.payrollSummary(selectedRun);
      setReportData(data);
    } finally {
      setLoading(false);
    }
  }, [selectedRun, tab]);

  useEffect(() => {
    if (!selectedRun) return;
    loadReport();
  }, [selectedRun, tab, loadReport]);

  const exportCSV = () => {
    if (!reportData.length) return;
    const keys = Object.keys(reportData[0]);
    const csv = [keys.join(","), ...reportData.map((r) => keys.map((k) => r[k] ?? "").join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kenya-payroll-${tab}-report.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const currentRun = runs.find((r) => r.id === selectedRun);

  const COLUMNS: Record<string, string[]> = {
    paye: ["employee_name", "employee_code", "tax_pin", "gross_salary", "taxable_income", "paye_amount", "personal_relief"],
    nhif: ["employee_name", "employee_code", "nhif_no", "gross_salary", "nhif_amount"],
    nssf: ["employee_name", "employee_code", "nssf_no", "gross_salary", "nssf_employee"],
    summary: ["employee_name", "employee_code", "department", "gross_salary", "total_deductions", "net_salary", "payment_method"],
  };

  const fmt = (k: string, v: any) => {
    if (typeof v === "number" && ["salary", "income", "amount", "deductions", "paye", "nhif", "nssf"].some((s) => k.includes(s))) {
      return `KES ${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    }
    return v ?? "—";
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Statutory Reports</h1>
          <p className="text-sm text-gray-500 mt-1">PAYE · NHIF · NSSF — Kenya Revenue Authority compliance</p>
        </div>
      </div>

      {/* Run selector */}
      <div className="flex gap-3 items-end flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Payroll Run</label>
          <select value={selectedRun} onChange={(e) => setSelectedRun(e.target.value)} className="border rounded-lg px-3 py-2 text-sm min-w-48">
            {runs.length === 0 ? <option value="">No approved runs</option> : (
              runs.map((r) => (
                <option key={r.id} value={r.id}>{r.run_no} — {MONTH_NAMES[r.period_month]} {r.period_year}</option>
              ))
            )}
          </select>
        </div>
        {currentRun && (
          <div className="text-sm text-gray-500">
            {currentRun.employee_count} employees · KES {Number(currentRun.total_net).toLocaleString()} net
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b flex gap-4">
        {(["summary", "paye", "nhif", "nssf"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-2 text-sm font-medium uppercase border-b-2 -mb-px ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t}
          </button>
        ))}
      </div>

      {/* Report info */}
      {tab === "paye" && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700">
          PAYE deducted must be remitted to KRA by the 9th of the following month via iTax. File P10 return monthly.
        </div>
      )}
      {tab === "nhif" && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700">
          NHIF contributions remitted to NHIF by the 9th of the following month. File monthly deduction schedules on the NHIF portal.
        </div>
      )}
      {tab === "nssf" && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700">
          NSSF contributions (employee + employer match) remitted by the 15th of the following month. Both tiers required under NSSF Act 2013.
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <div className="flex justify-end px-4 py-2 border-b">
          <button onClick={exportCSV} className="text-xs text-blue-600 hover:underline">Export CSV</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                {(COLUMNS[tab] || []).map((col) => (
                  <th key={col} className="px-4 py-3 text-left">{col.replace(/_/g, " ")}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
              ) : reportData.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No data. Select an approved payroll run and calculate first.</td></tr>
              ) : (
                reportData.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    {(COLUMNS[tab] || []).map((col) => (
                      <td key={col} className="px-4 py-2">{fmt(col, row[col])}</td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Totals */}
      {currentRun && reportData.length > 0 && tab !== "summary" && (
        <div className="bg-gray-50 rounded-lg border p-4 grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-500">Total PAYE</p>
            <p className="font-bold text-red-600">KES {Number(currentRun.total_paye).toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Total NHIF</p>
            <p className="font-bold text-orange-600">KES {Number(currentRun.total_nhif).toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Total NSSF</p>
            <p className="font-bold text-yellow-600">KES {Number(currentRun.total_nssf).toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
          </div>
        </div>
      )}
    </div>
  );
}
