"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { hrApi, PayrollPeriod, PayrollPeriodDetail, PayrollStatus, PaymentMethod } from "@/lib/hr";
import { RequirePermission } from "@/components/PermissionGuard";
import { Badge } from "@/components/ui/Badge";

const STATUS_VARIANT: Record<PayrollStatus, "yellow" | "green" | "blue" | "red"> = {
  DRAFT: "yellow",
  APPROVED: "green",
  PAID: "blue",
  CANCELLED: "red",
};

const METHOD_LABEL: Record<PaymentMethod, string> = {
  MPESA: "M-Pesa",
  BANK: "Bank",
  CASH: "Cash",
};

function NewPeriodForm({ onSave, onCancel }: { onSave: (d: { period_month: number; period_year: number; notes?: string }) => void; onCancel: () => void }) {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [notes, setNotes] = useState("");
  return (
    <div className="bg-white border rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-sm text-gray-800">New Payroll Period</h3>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="text-xs text-gray-500">Month</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].map((m, i) => (
              <option key={i + 1} value={i + 1}>{m}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Year</label>
          <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={year} onChange={(e) => setYear(Number(e.target.value))} />
        </div>
        <div>
          <label className="text-xs text-gray-500">Notes</label>
          <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <div className="flex gap-2">
        <button onClick={() => onSave({ period_month: month, period_year: year, notes: notes || undefined })} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm">Create</button>
        <button onClick={onCancel} className="px-3 py-1.5 border rounded text-sm">Cancel</button>
      </div>
    </div>
  );
}

function AddLineForm({ periodId, onSave, onCancel }: {
  periodId: string;
  onSave: (d: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const { data: employees = [] } = useQuery({ queryKey: ["hr-employees"], queryFn: () => hrApi.listEmployees() });
  const [form, setForm] = useState({
    employee_id: "", gross_pay: "", net_pay: "", payment_method: "", payment_reference: "",
  });
  const [components, setComponents] = useState('{"basic":0}');

  const f = (k: string) => ({
    value: (form as Record<string, string>)[k],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm((p) => ({ ...p, [k]: e.target.value })),
  });

  return (
    <div className="bg-white border rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-sm text-gray-800">Add Payroll Line</h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-gray-500">Employee</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("employee_id")}>
            <option value="">— select —</option>
            {employees.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.department})</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Payment Method</label>
          <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("payment_method")}>
            <option value="">— inherit from employee —</option>
            {["MPESA", "BANK", "CASH"].map((m) => <option key={m} value={m}>{METHOD_LABEL[m as PaymentMethod]}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500">Gross Pay (KES)</label>
          <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("gross_pay")} />
        </div>
        <div>
          <label className="text-xs text-gray-500">Net Pay (KES)</label>
          <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1" {...f("net_pay")} />
        </div>
        <div className="col-span-2">
          <label className="text-xs text-gray-500">Salary Components (JSON) — e.g. {`{"basic":50000,"transport":3000,"paye":-3000}`}</label>
          <textarea
            className="w-full border rounded px-2 py-1.5 text-sm mt-1 font-mono"
            rows={2}
            value={components}
            onChange={(e) => setComponents(e.target.value)}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => {
            let parsed: Record<string, number> | null = null;
            try { parsed = JSON.parse(components); } catch { /* ignore */ }
            onSave({
              employee_id: form.employee_id,
              gross_pay: Number(form.gross_pay) || 0,
              net_pay: Number(form.net_pay) || 0,
              payment_method: form.payment_method || undefined,
              salary_components: parsed,
            });
          }}
          disabled={!form.employee_id}
          className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm disabled:opacity-50"
        >Add</button>
        <button onClick={onCancel} className="px-3 py-1.5 border rounded text-sm">Cancel</button>
      </div>
    </div>
  );
}

function PeriodDetail({ period, onClose }: { period: PayrollPeriod; onClose: () => void }) {
  const qc = useQueryClient();
  const [showAddLine, setShowAddLine] = useState(false);

  const { data: detail } = useQuery({
    queryKey: ["hr-payroll-period", period.id],
    queryFn: () => hrApi.getPayrollPeriod(period.id),
  });

  const addLine = useMutation({
    mutationFn: (data: Record<string, unknown>) => hrApi.addPayrollLine(period.id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-payroll-period", period.id] }); setShowAddLine(false); },
  });

  const approveMutation = useMutation({
    mutationFn: () => hrApi.approvePayrollPeriod(period.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["hr-payroll-periods"] });
      qc.invalidateQueries({ queryKey: ["hr-payroll-period", period.id] });
    },
  });

  const MONTHS = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

  if (!detail) return <div className="p-6 text-sm text-gray-400">Loading...</div>;

  const totalGross = detail.lines.reduce((s, l) => s + l.gross_pay, 0);
  const totalNet = detail.lines.reduce((s, l) => s + l.net_pay, 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            {MONTHS[detail.period_month]} {detail.period_year}
          </h2>
          <div className="flex items-center gap-3 mt-1">
            <Badge label={detail.status} variant={STATUS_VARIANT[detail.status]} />
            <span className="text-xs text-gray-500">{detail.lines.length} employees</span>
            <span className="text-xs text-gray-500">Gross: KES {totalGross.toLocaleString()} · Net: KES {totalNet.toLocaleString()}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {detail.status === "DRAFT" && (
            <>
              <button onClick={() => setShowAddLine(true)} className="px-3 py-1.5 border rounded text-sm hover:bg-gray-50">+ Add Line</button>
              <button
                onClick={() => approveMutation.mutate()}
                className="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
              >Approve Period</button>
            </>
          )}
          <button onClick={onClose} className="px-3 py-1.5 border rounded text-sm hover:bg-gray-50">Close</button>
        </div>
      </div>

      {showAddLine && (
        <AddLineForm
          periodId={period.id}
          onSave={(d) => addLine.mutate(d)}
          onCancel={() => setShowAddLine(false)}
        />
      )}

      <div className="bg-white border rounded-lg overflow-hidden">
        {detail.lines.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No payroll lines yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Employee</th>
                <th className="px-4 py-2 text-left">Dept</th>
                <th className="px-4 py-2 text-right">Gross (KES)</th>
                <th className="px-4 py-2 text-right">Net (KES)</th>
                <th className="px-4 py-2 text-left">Method</th>
                <th className="px-4 py-2 text-left">Paid</th>
                <th className="px-4 py-2 text-left">Ref</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {detail.lines.map((line) => (
                <tr key={line.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{line.employee?.full_name ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{line.employee?.department ?? "—"}</td>
                  <td className="px-4 py-3 text-right font-mono">{line.gross_pay.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right font-mono font-medium">{line.net_pay.toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{line.payment_method ? METHOD_LABEL[line.payment_method] : "—"}</td>
                  <td className="px-4 py-3">
                    {line.is_paid
                      ? <span className="text-xs font-medium text-green-600">Paid</span>
                      : <span className="text-xs text-gray-400">Pending</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 font-mono">{line.payment_reference ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {detail.status === "APPROVED" && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm font-medium text-blue-800">Period Approved</p>
          <p className="text-xs text-blue-600 mt-1">
            To disburse payments, use the Finance &rarr; M-Pesa bulk payment flow or bank transfer.
            Export available via API: <code className="font-mono bg-blue-100 px-1 rounded">/api/v1/hr/payroll/periods/{"{id}"}/export</code>
          </p>
        </div>
      )}
    </div>
  );
}

function PayrollContent() {
  const qc = useQueryClient();
  const [showNewPeriod, setShowNewPeriod] = useState(false);
  const [selected, setSelected] = useState<PayrollPeriod | null>(null);

  const { data: periods = [], isLoading } = useQuery({
    queryKey: ["hr-payroll-periods"],
    queryFn: () => hrApi.listPayrollPeriods(),
  });

  const createPeriod = useMutation({
    mutationFn: hrApi.createPayrollPeriod,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["hr-payroll-periods"] }); setShowNewPeriod(false); },
  });

  const MONTHS = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

  if (selected) {
    return <PeriodDetail period={selected} onClose={() => setSelected(null)} />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Payroll</h1>
          <p className="text-sm text-gray-500 mt-1">Payroll periods · salary structure placeholder · export-ready</p>
        </div>
        <button onClick={() => setShowNewPeriod(true)} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">
          + New Period
        </button>
      </div>

      {showNewPeriod && (
        <NewPeriodForm
          onSave={(d) => createPeriod.mutate(d)}
          onCancel={() => setShowNewPeriod(false)}
        />
      )}

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 text-sm text-yellow-800">
        Payroll is a foundation scaffold. Salary computation, PAYE/NSSF/NHIF rules, and M-Pesa bulk disbursement
        are handled outside this module. Use <strong>Approve</strong> to lock a period, then export via Finance.
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400 text-center">Loading...</p>
        ) : periods.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No payroll periods yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Period</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Notes</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {periods.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{MONTHS[p.period_month]} {p.period_year}</td>
                  <td className="px-4 py-3">
                    <Badge label={p.status} variant={STATUS_VARIANT[p.status]} />
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{p.notes ?? ""}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => setSelected(p)} className="text-xs text-indigo-600 hover:underline">Open</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default function PayrollPage() {
  return (
    <RequirePermission permission="hr.view">
      <PayrollContent />
    </RequirePermission>
  );
}
