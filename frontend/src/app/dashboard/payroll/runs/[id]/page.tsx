"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RequirePermission } from "@/components/PermissionGuard";
import { useAuth } from "@/context/AuthContext";
import { payrollKeApi, MONTH_NAMES, STATUS_COLORS } from "@/lib/payrollKe";

const kes = (v: unknown) => `KES ${Number(v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function errorText(e: unknown): string {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof d === "string" ? d : "The action failed.";
}

function PayrollRunDetail({ id }: { id: string }) {
  const qc = useQueryClient();
  const { hasPermission } = useAuth();
  const canCalculate = hasPermission("payroll_ke.create");
  const canApprove = hasPermission("payroll_ke.approve");

  const { data: run, isLoading, isError } = useQuery({ queryKey: ["ke-run", id], queryFn: () => payrollKeApi.getRun(id) });
  const { data: lines = [] } = useQuery({ queryKey: ["ke-run-lines", id], queryFn: () => payrollKeApi.getRunLines(id), enabled: !!run });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["ke-run", id] });
    qc.invalidateQueries({ queryKey: ["ke-run-lines", id] });
    qc.invalidateQueries({ queryKey: ["ke-runs"] });
  };
  const calculate = useMutation({ mutationFn: () => payrollKeApi.calculateRun(id), onSuccess: refresh });
  const approve = useMutation({ mutationFn: () => payrollKeApi.approveRun(id), onSuccess: refresh });

  if (isLoading) return <div className="p-6 text-sm text-gray-500">Loading payroll run…</div>;
  if (isError || !run) return <div className="p-6 text-sm text-red-600">Payroll run not found.</div>;

  // employer's own statutory cost (NSSF employer, housing levy employer, NITA): on top of gross, never deducted
  const employerOf = (l: { components_json?: unknown }) =>
    Number(((l.components_json as { employer?: { total?: number } } | undefined)?.employer?.total) ?? 0);
  const employerTotal = lines.reduce((s, l) => s + employerOf(l), 0);
  const totals: [string, unknown][] = [
    ["Gross", run.total_gross], ["PAYE", run.total_paye], ["NSSF", run.total_nssf],
    ["SHIF / NHIF", run.total_nhif], ["Housing levy", run.total_housing_levy], ["Net pay", run.total_net],
    ["Employer contributions", employerTotal], ["Total cost to company", Number(run.total_gross) + employerTotal],
  ];
  const actionError = calculate.error || approve.error;

  return (
    <div className="p-4 md:p-6 space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/dashboard/payroll" className="text-xs text-blue-600 hover:underline">← Kenya Payroll</Link>
          <h1 className="text-xl font-semibold mt-1">
            {run.run_no} · {MONTH_NAMES[run.period_month]} {run.period_year}
          </h1>
          <p className="text-sm text-gray-500">
            {run.period_start} – {run.period_end} · {run.employee_count} employees
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[run.status] ?? ""}`}>{run.status}</span>
          {canCalculate && (run.status === "DRAFT" || run.status === "CALCULATED") && (
            <button type="button" onClick={() => calculate.mutate()} disabled={calculate.isPending}
              className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50">
              {calculate.isPending ? "Calculating…" : run.status === "DRAFT" ? "Calculate" : "Recalculate"}
            </button>
          )}
          {canApprove && run.status === "CALCULATED" && (
            <button type="button" onClick={() => { if (confirm("Approve this payroll run? It is locked afterwards.")) approve.mutate(); }}
              disabled={approve.isPending}
              className="px-3 py-2 text-sm bg-green-600 text-white rounded-lg disabled:opacity-50">
              {approve.isPending ? "Approving…" : "Approve"}
            </button>
          )}
        </div>
      </div>
      {actionError && <p className="text-sm text-red-600">{errorText(actionError)}</p>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {totals.map(([label, v]) => (
          <div key={label} className="border rounded-lg p-3 bg-white">
            <div className="text-xs text-gray-500">{label}</div>
            <div className="text-sm font-semibold mt-1">{kes(v)}</div>
          </div>
        ))}
      </div>

      <div className="border rounded-lg bg-white overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500">
            <tr>
              {["Employee", "Basic", "Allowances", "Gross", "NSSF", "PAYE", "SHIF/NHIF", "Housing levy", "Other ded.", "Net", "Employer contrib.", "Cost to company"].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.length === 0 && (
              <tr><td colSpan={12} className="px-3 py-6 text-center text-gray-400">
                {run.status === "DRAFT" ? "Not calculated yet." : "No employees in this run."}
              </td></tr>
            )}
            {lines.map((l) => (
              <tr key={l.id} className="border-t">
                <td className="px-3 py-2 whitespace-nowrap">{l.employee_code} — {l.employee_name}</td>
                <td className="px-3 py-2">{kes(l.basic_salary)}</td>
                <td className="px-3 py-2">{kes(Number(l.housing_allowance) + Number(l.transport_allowance) + Number(l.other_allowances) + Number(l.overtime_pay))}</td>
                <td className="px-3 py-2">{kes(l.gross_salary)}</td>
                <td className="px-3 py-2">{kes(l.nssf_employee)}</td>
                <td className="px-3 py-2">{kes(l.paye_amount)}</td>
                <td className="px-3 py-2">{kes(l.nhif_amount)}</td>
                <td className="px-3 py-2">{kes(l.housing_levy)}</td>
                <td className="px-3 py-2">{kes(l.other_deductions)}</td>
                <td className="px-3 py-2 font-medium">{kes(l.net_salary)}</td>
                <td className="px-3 py-2">{kes(employerOf(l))}</td>
                <td className="px-3 py-2 font-medium">{kes(Number(l.gross_salary) + employerOf(l))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {run.notes && <p className="text-sm text-gray-600">Notes: {run.notes}</p>}
    </div>
  );
}

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <RequirePermission permission="payroll_ke.view">
      <PayrollRunDetail id={id} />
    </RequirePermission>
  );
}
