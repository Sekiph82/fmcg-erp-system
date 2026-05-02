"use client";

import React, { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { integrationApi } from "@/lib/utilityIntegration";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line,
} from "recharts";
import {
  billingApi,
  downloadBillsCsv,
  downloadAllocationsCsv,
  UTILITY_TYPE_LABELS,
  UTILITY_TYPE_COLORS,
  BILL_STATUS_LABELS,
  BILL_STATUS_COLORS,
  TARIFF_TYPE_LABELS,
  ALLOCATION_METHOD_LABELS,
  TARGET_TYPE_LABELS,
  type UtilityBill,
  type UtilityTariff,
  type UtilityAllocation,
  type BillCreate,
  type BillUpdate,
  type TariffCreate,
  type TariffUpdate,
  type AllocationCreate,
  type AllocationUpdate,
  type AllocationEngineRequest,
  type AllocationEngineTarget,
  type BillStatus,
  type UtilityTypeBilling,
  type AllocationMethod,
  type TargetType,
  type TariffType,
} from "@/lib/utilityBilling";

// ── Utility components ────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: BillStatus }) {
  const bg = BILL_STATUS_COLORS[status] ?? "#6b7280";
  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-semibold text-white"
      style={{ background: bg }}
    >
      {BILL_STATUS_LABELS[status] ?? status}
    </span>
  );
}

function UtilityBadge({ type }: { type: string }) {
  const color = UTILITY_TYPE_COLORS[type as UtilityTypeBilling] ?? "#9ca3af";
  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: color + "22", color }}
    >
      {UTILITY_TYPE_LABELS[type as UtilityTypeBilling] ?? type}
    </span>
  );
}

function KpiCard({
  label, value, unit, sub, highlight,
}: { label: string; value: string | number; unit?: string; sub?: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? "border-amber-400 bg-amber-50 dark:bg-amber-950/20" : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"}`}>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">
        {value}<span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>
      </p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function fmt(n?: number | null, dp = 2) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

// ── Post to GL Modal ──────────────────────────────────────────────────────────

function PostToGLModal({
  bill,
  onClose,
  onSuccess,
}: {
  bill: UtilityBill;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}) {
  const qc = useQueryClient();
  const [debitAccountId, setDebitAccountId] = useState("");
  const [creditAccountId, setCreditAccountId] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      integrationApi.postBillToGL(bill.id, {
        debit_account_id: debitAccountId,
        credit_account_id: creditAccountId,
      }),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["bills"] });
      qc.invalidateQueries({ queryKey: ["billing-kpis"] });
      onSuccess(`Bill posted to GL: ${result.entry_no}`);
      onClose();
    },
  });

  const inputCls =
    "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelCls = "block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Post Bill to GL</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">
            &times;
          </button>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Bill <strong>{bill.bill_no}</strong> — {bill.provider_name ?? bill.utility_type} &mdash;{" "}
            <strong>
              {bill.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} {bill.currency_code}
            </strong>
          </p>
          <div>
            <label className={labelCls}>Debit Account ID *</label>
            <input
              className={inputCls}
              placeholder="UUID of the debit account"
              value={debitAccountId}
              onChange={e => setDebitAccountId(e.target.value)}
              required
            />
          </div>
          <div>
            <label className={labelCls}>Credit Account ID *</label>
            <input
              className={inputCls}
              placeholder="UUID of the credit account"
              value={creditAccountId}
              onChange={e => setCreditAccountId(e.target.value)}
              required
            />
          </div>
          {mut.isError && (
            <p className="text-xs text-red-600 dark:text-red-400">
              {mut.error instanceof Error ? mut.error.message : "Failed to post bill to GL."}
            </p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              onClick={() => mut.mutate()}
              disabled={mut.isPending || !debitAccountId.trim() || !creditAccountId.trim()}
              className="px-4 py-2 text-sm rounded-lg bg-violet-600 hover:bg-violet-700 text-white disabled:opacity-50"
            >
              {mut.isPending ? "Posting…" : "Post to GL"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

type Tab = "bills" | "tariffs" | "allocations" | "reports";

// ════════════════════════════════════════════════════════════════════════════
// Bill modal
// ════════════════════════════════════════════════════════════════════════════

function BillModal({
  initial, onClose, onSave,
}: {
  initial?: UtilityBill | null;
  onClose: () => void;
  onSave: (data: BillCreate | BillUpdate) => Promise<void>;
}) {
  const editing = !!initial;
  const [form, setForm] = useState<Partial<BillCreate>>({
    utility_type:        (initial?.utility_type ?? "ELECTRICITY") as UtilityTypeBilling,
    provider_name:       initial?.provider_name ?? "",
    tariff_code:         initial?.tariff_code ?? "",
    bill_reference:      initial?.bill_reference ?? "",
    billing_period_from: initial?.billing_period_from ?? "",
    billing_period_to:   initial?.billing_period_to ?? "",
    invoice_date:        initial?.invoice_date ?? "",
    due_date:            initial?.due_date ?? "",
    consumption_quantity: initial?.consumption_quantity ?? undefined,
    consumption_unit:    initial?.consumption_unit ?? "",
    unit_rate:           initial?.unit_rate ?? undefined,
    base_charge:         initial?.base_charge ?? undefined,
    energy_charge:       initial?.energy_charge ?? undefined,
    demand_charge:       initial?.demand_charge ?? undefined,
    fixed_charge:        initial?.fixed_charge ?? undefined,
    surcharge_amount:    initial?.surcharge_amount ?? undefined,
    tax_amount:          initial?.tax_amount ?? undefined,
    total_amount:        initial?.total_amount ?? 0,
    currency_code:       initial?.currency_code ?? "USD",
    status:              (initial?.status ?? "RECEIVED") as BillStatus,
    payment_date:        initial?.payment_date ?? "",
    document_ref:        initial?.document_ref ?? "",
    notes:               initial?.notes ?? "",
  });
  const [saving, setSaving] = useState(false);

  const set = (k: keyof typeof form, v: unknown) => setForm(p => ({ ...p, [k]: v }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form as BillCreate);
      onClose();
    } finally {
      setSaving(false);
    }
  }

  const inputCls = "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelCls = "block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {editing ? "Edit Bill" : "New Utility Bill"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 grid grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Utility Type *</label>
            <select className={inputCls} value={form.utility_type}
              onChange={e => set("utility_type", e.target.value)} required>
              {Object.entries(UTILITY_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Provider / Supplier</label>
            <input className={inputCls} value={form.provider_name ?? ""}
              onChange={e => set("provider_name", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Bill Reference</label>
            <input className={inputCls} value={form.bill_reference ?? ""}
              onChange={e => set("bill_reference", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Tariff Code</label>
            <input className={inputCls} value={form.tariff_code ?? ""}
              onChange={e => set("tariff_code", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Period From *</label>
            <input type="date" className={inputCls} value={form.billing_period_from ?? ""}
              onChange={e => set("billing_period_from", e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Period To *</label>
            <input type="date" className={inputCls} value={form.billing_period_to ?? ""}
              onChange={e => set("billing_period_to", e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Invoice Date</label>
            <input type="date" className={inputCls} value={form.invoice_date ?? ""}
              onChange={e => set("invoice_date", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Due Date</label>
            <input type="date" className={inputCls} value={form.due_date ?? ""}
              onChange={e => set("due_date", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Consumption Qty</label>
            <input type="number" step="any" className={inputCls}
              value={form.consumption_quantity ?? ""}
              onChange={e => set("consumption_quantity", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Consumption Unit</label>
            <input className={inputCls} placeholder="kWh / m³ / kg"
              value={form.consumption_unit ?? ""}
              onChange={e => set("consumption_unit", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Unit Rate</label>
            <input type="number" step="any" className={inputCls}
              value={form.unit_rate ?? ""}
              onChange={e => set("unit_rate", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Base Charge</label>
            <input type="number" step="any" className={inputCls}
              value={form.base_charge ?? ""}
              onChange={e => set("base_charge", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Energy Charge</label>
            <input type="number" step="any" className={inputCls}
              value={form.energy_charge ?? ""}
              onChange={e => set("energy_charge", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Demand Charge</label>
            <input type="number" step="any" className={inputCls}
              value={form.demand_charge ?? ""}
              onChange={e => set("demand_charge", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Fixed Charge</label>
            <input type="number" step="any" className={inputCls}
              value={form.fixed_charge ?? ""}
              onChange={e => set("fixed_charge", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Surcharge</label>
            <input type="number" step="any" className={inputCls}
              value={form.surcharge_amount ?? ""}
              onChange={e => set("surcharge_amount", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Tax Amount</label>
            <input type="number" step="any" className={inputCls}
              value={form.tax_amount ?? ""}
              onChange={e => set("tax_amount", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Total Amount *</label>
            <input type="number" step="any" className={inputCls}
              value={form.total_amount ?? ""}
              onChange={e => set("total_amount", +e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Currency</label>
            <input className={inputCls} value={form.currency_code ?? "USD"}
              onChange={e => set("currency_code", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Status</label>
            <select className={inputCls} value={form.status}
              onChange={e => set("status", e.target.value)}>
              {Object.entries(BILL_STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Payment Date</label>
            <input type="date" className={inputCls} value={form.payment_date ?? ""}
              onChange={e => set("payment_date", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Document Reference</label>
            <input className={inputCls} value={form.document_ref ?? ""}
              onChange={e => set("document_ref", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Notes</label>
            <textarea className={inputCls} rows={2} value={form.notes ?? ""}
              onChange={e => set("notes", e.target.value)} />
          </div>
          <div className="col-span-2 flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50">
              {saving ? "Saving…" : editing ? "Update Bill" : "Create Bill"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Tariff modal
// ════════════════════════════════════════════════════════════════════════════

function TariffModal({
  initial, onClose, onSave,
}: {
  initial?: UtilityTariff | null;
  onClose: () => void;
  onSave: (data: TariffCreate | TariffUpdate) => Promise<void>;
}) {
  const editing = !!initial;
  const [form, setForm] = useState<Partial<TariffCreate>>({
    tariff_code:   initial?.tariff_code ?? "",
    name:          initial?.name ?? "",
    description:   initial?.description ?? "",
    utility_type:  (initial?.utility_type ?? "ELECTRICITY") as UtilityTypeBilling,
    tariff_type:   (initial?.tariff_type ?? "FLAT") as TariffType,
    effective_from: initial?.effective_from ?? "",
    effective_to:   initial?.effective_to ?? "",
    unit:          initial?.unit ?? "kWh",
    currency_code: initial?.currency_code ?? "USD",
    base_rate:     initial?.base_rate ?? 0,
    peak_rate:     initial?.peak_rate ?? undefined,
    offpeak_rate:  initial?.offpeak_rate ?? undefined,
    demand_rate:   initial?.demand_rate ?? undefined,
    fixed_charge:  initial?.fixed_charge ?? undefined,
    tax_rate_pct:  initial?.tax_rate_pct ?? undefined,
    tax_rule:      initial?.tax_rule ?? "",
    is_active:     initial?.is_active ?? true,
    notes:         initial?.notes ?? "",
  });
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof form, v: unknown) => setForm(p => ({ ...p, [k]: v }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form as TariffCreate);
      onClose();
    } finally {
      setSaving(false);
    }
  }

  const inputCls = "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelCls = "block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {editing ? "Edit Tariff" : "New Tariff"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 grid grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Tariff Code *</label>
            <input className={inputCls} value={form.tariff_code ?? ""}
              onChange={e => set("tariff_code", e.target.value)} required disabled={editing} />
          </div>
          <div>
            <label className={labelCls}>Name *</label>
            <input className={inputCls} value={form.name ?? ""}
              onChange={e => set("name", e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Utility Type *</label>
            <select className={inputCls} value={form.utility_type}
              onChange={e => set("utility_type", e.target.value)} required>
              {Object.entries(UTILITY_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Tariff Type</label>
            <select className={inputCls} value={form.tariff_type}
              onChange={e => set("tariff_type", e.target.value)}>
              {Object.entries(TARIFF_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Valid From *</label>
            <input type="date" className={inputCls} value={form.effective_from ?? ""}
              onChange={e => set("effective_from", e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Valid To</label>
            <input type="date" className={inputCls} value={form.effective_to ?? ""}
              onChange={e => set("effective_to", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Unit *</label>
            <input className={inputCls} placeholder="kWh / m³ / kg"
              value={form.unit ?? ""} onChange={e => set("unit", e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Currency</label>
            <input className={inputCls} value={form.currency_code ?? "USD"}
              onChange={e => set("currency_code", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Base Rate ($/unit) *</label>
            <input type="number" step="any" className={inputCls}
              value={form.base_rate ?? 0}
              onChange={e => set("base_rate", +e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Peak Rate</label>
            <input type="number" step="any" className={inputCls}
              value={form.peak_rate ?? ""}
              onChange={e => set("peak_rate", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Off-Peak Rate</label>
            <input type="number" step="any" className={inputCls}
              value={form.offpeak_rate ?? ""}
              onChange={e => set("offpeak_rate", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Demand Rate ($/kW)</label>
            <input type="number" step="any" className={inputCls}
              value={form.demand_rate ?? ""}
              onChange={e => set("demand_rate", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Fixed Charge</label>
            <input type="number" step="any" className={inputCls}
              value={form.fixed_charge ?? ""}
              onChange={e => set("fixed_charge", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Tax Rate %</label>
            <input type="number" step="any" className={inputCls}
              value={form.tax_rate_pct ?? ""}
              onChange={e => set("tax_rate_pct", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Tax Rule</label>
            <input className={inputCls} value={form.tax_rule ?? ""}
              onChange={e => set("tax_rule", e.target.value)} />
          </div>
          <div className="flex items-center gap-2 pt-4">
            <input type="checkbox" id="is_active" checked={form.is_active ?? true}
              onChange={e => set("is_active", e.target.checked)} />
            <label htmlFor="is_active" className="text-sm text-gray-700 dark:text-gray-300">Active</label>
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Notes</label>
            <textarea className={inputCls} rows={2} value={form.notes ?? ""}
              onChange={e => set("notes", e.target.value)} />
          </div>
          <div className="col-span-2 flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50">
              {saving ? "Saving…" : editing ? "Update Tariff" : "Create Tariff"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Allocation modal
// ════════════════════════════════════════════════════════════════════════════

function AllocationModal({
  initial, onClose, onSave,
}: {
  initial?: UtilityAllocation | null;
  onClose: () => void;
  onSave: (data: AllocationCreate | AllocationUpdate) => Promise<void>;
}) {
  const editing = !!initial;
  const [form, setForm] = useState<Partial<AllocationCreate>>({
    utility_type:        (initial?.utility_type ?? "ELECTRICITY") as UtilityTypeBilling,
    allocation_date:     initial?.allocation_date ?? "",
    period_start:        initial?.period_start ?? "",
    period_end:          initial?.period_end ?? "",
    allocation_method:   (initial?.allocation_method ?? "METERED") as AllocationMethod,
    target_type:         (initial?.target_type ?? undefined) as TargetType | undefined,
    target_id:           initial?.target_id ?? "",
    target_name:         initial?.target_name ?? "",
    department:          initial?.department ?? "",
    production_line:     initial?.production_line ?? "",
    machine_ref:         initial?.machine_ref ?? "",
    batch_no:            initial?.batch_no ?? "",
    source_cost:         initial?.source_cost ?? undefined,
    allocation_basis:    initial?.allocation_basis ?? undefined,
    allocation_basis_unit: initial?.allocation_basis_unit ?? "",
    allocated_quantity:  initial?.allocated_quantity ?? undefined,
    quantity_unit:       initial?.quantity_unit ?? "",
    total_cost:          initial?.total_cost ?? 0,
    allocated_cost:      initial?.allocated_cost ?? 0,
    currency_code:       initial?.currency_code ?? "USD",
    bill_id:             initial?.bill_id ?? "",
    notes:               initial?.notes ?? "",
  });
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof form, v: unknown) => setForm(p => ({ ...p, [k]: v }));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form as AllocationCreate);
      onClose();
    } finally {
      setSaving(false);
    }
  }

  const inputCls = "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelCls = "block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {editing ? "Edit Allocation" : "New Allocation"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 grid grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Utility Type *</label>
            <select className={inputCls} value={form.utility_type}
              onChange={e => set("utility_type", e.target.value)} required>
              {Object.entries(UTILITY_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Allocation Date *</label>
            <input type="date" className={inputCls} value={form.allocation_date ?? ""}
              onChange={e => set("allocation_date", e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Period From</label>
            <input type="date" className={inputCls} value={form.period_start ?? ""}
              onChange={e => set("period_start", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Period To</label>
            <input type="date" className={inputCls} value={form.period_end ?? ""}
              onChange={e => set("period_end", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Method *</label>
            <select className={inputCls} value={form.allocation_method}
              onChange={e => set("allocation_method", e.target.value)} required>
              {Object.entries(ALLOCATION_METHOD_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Target Type</label>
            <select className={inputCls} value={form.target_type ?? ""}
              onChange={e => set("target_type", e.target.value || undefined)}>
              <option value="">— Select —</option>
              {Object.entries(TARGET_TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelCls}>Target ID</label>
            <input className={inputCls} value={form.target_id ?? ""}
              onChange={e => set("target_id", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Target Name</label>
            <input className={inputCls} value={form.target_name ?? ""}
              onChange={e => set("target_name", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Department</label>
            <input className={inputCls} value={form.department ?? ""}
              onChange={e => set("department", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Production Line</label>
            <input className={inputCls} value={form.production_line ?? ""}
              onChange={e => set("production_line", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Machine Ref</label>
            <input className={inputCls} value={form.machine_ref ?? ""}
              onChange={e => set("machine_ref", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Batch No</label>
            <input className={inputCls} value={form.batch_no ?? ""}
              onChange={e => set("batch_no", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Source Cost</label>
            <input type="number" step="any" className={inputCls}
              value={form.source_cost ?? ""}
              onChange={e => set("source_cost", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Allocation Basis Value</label>
            <input type="number" step="any" className={inputCls}
              value={form.allocation_basis ?? ""}
              onChange={e => set("allocation_basis", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Basis Unit</label>
            <input className={inputCls} placeholder="hours / % / m²"
              value={form.allocation_basis_unit ?? ""}
              onChange={e => set("allocation_basis_unit", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Allocated Qty</label>
            <input type="number" step="any" className={inputCls}
              value={form.allocated_quantity ?? ""}
              onChange={e => set("allocated_quantity", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div>
            <label className={labelCls}>Quantity Unit</label>
            <input className={inputCls} value={form.quantity_unit ?? ""}
              onChange={e => set("quantity_unit", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Total Cost *</label>
            <input type="number" step="any" className={inputCls}
              value={form.total_cost ?? 0}
              onChange={e => set("total_cost", +e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Allocated Cost *</label>
            <input type="number" step="any" className={inputCls}
              value={form.allocated_cost ?? 0}
              onChange={e => set("allocated_cost", +e.target.value)} required />
          </div>
          <div>
            <label className={labelCls}>Currency</label>
            <input className={inputCls} value={form.currency_code ?? "USD"}
              onChange={e => set("currency_code", e.target.value)} />
          </div>
          <div>
            <label className={labelCls}>Linked Bill ID</label>
            <input className={inputCls} value={form.bill_id ?? ""}
              onChange={e => set("bill_id", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className={labelCls}>Notes</label>
            <textarea className={inputCls} rows={2} value={form.notes ?? ""}
              onChange={e => set("notes", e.target.value)} />
          </div>
          <div className="col-span-2 flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50">
              {saving ? "Saving…" : editing ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Engine modal
// ════════════════════════════════════════════════════════════════════════════

function EngineModal({
  bills,
  onClose,
  onRun,
}: {
  bills: UtilityBill[];
  onClose: () => void;
  onRun: (req: AllocationEngineRequest) => Promise<void>;
}) {
  const [billId, setBillId] = useState(bills[0]?.id ?? "");
  const [method, setMethod] = useState<AllocationMethod>("PROPORTIONAL");
  const [allocationDate, setAllocationDate] = useState(new Date().toISOString().slice(0, 10));
  const [targets, setTargets] = useState<AllocationEngineTarget[]>([
    { target_type: "DEPARTMENT", target_id: "", basis_value: 100, basis_unit: "%" },
  ]);
  const [running, setRunning] = useState(false);

  function addTarget() {
    setTargets(t => [...t, { target_type: "DEPARTMENT", target_id: "", basis_value: 0, basis_unit: "%" }]);
  }
  function removeTarget(i: number) {
    setTargets(t => t.filter((_, idx) => idx !== i));
  }
  function updateTarget(i: number, k: keyof AllocationEngineTarget, v: unknown) {
    setTargets(t => t.map((row, idx) => idx === i ? { ...row, [k]: v } : row));
  }

  async function handleRun() {
    if (!billId) return;
    setRunning(true);
    try {
      await onRun({
        bill_id: billId,
        allocation_method: method,
        allocation_date: allocationDate,
        targets,
      });
      onClose();
    } finally {
      setRunning(false);
    }
  }

  const inputCls = "rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Run Allocation Engine</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">&times;</button>
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Bill *</label>
              <select className={inputCls + " w-full"} value={billId}
                onChange={e => setBillId(e.target.value)}>
                {bills.map(b => (
                  <option key={b.id} value={b.id}>{b.bill_no} — {b.provider_name ?? b.utility_type}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Method *</label>
              <select className={inputCls + " w-full"} value={method}
                onChange={e => setMethod(e.target.value as AllocationMethod)}>
                {Object.entries(ALLOCATION_METHOD_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Allocation Date *</label>
              <input type="date" className={inputCls + " w-full"} value={allocationDate}
                onChange={e => setAllocationDate(e.target.value)} />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Allocation Targets</h3>
              <button onClick={addTarget}
                className="text-xs text-blue-600 hover:underline">+ Add Target</button>
            </div>
            <div className="space-y-2">
              {targets.map((t, i) => (
                <div key={i} className="grid grid-cols-5 gap-2 items-center">
                  <select className={inputCls} value={t.target_type}
                    onChange={e => updateTarget(i, "target_type", e.target.value as TargetType)}>
                    {Object.entries(TARGET_TYPE_LABELS).map(([k, v]) => (
                      <option key={k} value={k}>{v}</option>
                    ))}
                  </select>
                  <input className={inputCls} placeholder="Target ID"
                    value={t.target_id} onChange={e => updateTarget(i, "target_id", e.target.value)} />
                  <input className={inputCls} placeholder="Name"
                    value={t.target_name ?? ""} onChange={e => updateTarget(i, "target_name", e.target.value)} />
                  <input type="number" step="any" className={inputCls} placeholder="Basis value"
                    value={t.basis_value} onChange={e => updateTarget(i, "basis_value", +e.target.value)} />
                  <div className="flex items-center gap-1">
                    <input className={inputCls + " flex-1"} placeholder="Unit"
                      value={t.basis_unit ?? ""} onChange={e => updateTarget(i, "basis_unit", e.target.value)} />
                    {targets.length > 1 && (
                      <button onClick={() => removeTarget(i)}
                        className="text-red-400 hover:text-red-600 text-lg leading-none">&times;</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600">Cancel</button>
            <button onClick={handleRun} disabled={running || !billId}
              className="px-4 py-2 text-sm rounded-lg bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-50">
              {running ? "Running…" : "Run Engine"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// Main page
// ════════════════════════════════════════════════════════════════════════════

export default function UtilityBillingPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("bills");

  // Filters
  const [utilityType, setUtilityType] = useState("");
  const [billStatus, setBillStatus]   = useState("");
  const [dateFrom, setDateFrom]       = useState("");
  const [dateTo, setDateTo]           = useState("");
  const [reportGroupBy, setReportGroupBy] = useState("target_type");

  // Modals
  const [billModal, setBillModal]       = useState<{ open: boolean; item?: UtilityBill | null }>({ open: false });
  const [tariffModal, setTariffModal]   = useState<{ open: boolean; item?: UtilityTariff | null }>({ open: false });
  const [allocModal, setAllocModal]     = useState<{ open: boolean; item?: UtilityAllocation | null }>({ open: false });
  const [engineModal, setEngineModal]   = useState(false);
  const [glModal, setGlModal]           = useState<{ open: boolean; bill?: UtilityBill }>({ open: false });

  // Toast
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  function showToast(message: string, type: "success" | "error" = "success") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4500);
  }

  // ── Queries ───────────────────────────────────────────────────────────────
  const kpiQ = useQuery({
    queryKey: ["billing-kpis", utilityType, dateFrom, dateTo],
    queryFn: () => billingApi.kpis({
      utility_type: utilityType as UtilityTypeBilling || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
  });

  const billsQ = useQuery({
    queryKey: ["bills", utilityType, billStatus, dateFrom, dateTo],
    queryFn: () => billingApi.listBills({
      utility_type: utilityType as UtilityTypeBilling || undefined,
      status: billStatus as BillStatus || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
  });

  const tariffsQ = useQuery({
    queryKey: ["tariffs", utilityType],
    queryFn: () => billingApi.listTariffs({
      utility_type: utilityType as UtilityTypeBilling || undefined,
    }),
  });

  const allocQ = useQuery({
    queryKey: ["allocations", utilityType, dateFrom, dateTo],
    queryFn: () => billingApi.listAllocations({
      utility_type: utilityType as UtilityTypeBilling || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
  });

  const reportQ = useQuery({
    queryKey: ["alloc-report", reportGroupBy, utilityType, dateFrom, dateTo],
    queryFn: () => billingApi.report({
      group_by: reportGroupBy,
      utility_type: utilityType || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
    enabled: tab === "reports",
  });

  // ── Mutations ─────────────────────────────────────────────────────────────
  const invalidate = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["bills"] });
    qc.invalidateQueries({ queryKey: ["billing-kpis"] });
    qc.invalidateQueries({ queryKey: ["tariffs"] });
    qc.invalidateQueries({ queryKey: ["allocations"] });
    qc.invalidateQueries({ queryKey: ["alloc-report"] });
  }, [qc]);

  const billMut = useMutation({
    mutationFn: async ({ id, data }: { id?: string; data: BillCreate | BillUpdate }) =>
      id ? billingApi.updateBill(id, data as BillUpdate) : billingApi.createBill(data as BillCreate),
    onSuccess: invalidate,
  });
  const deleteBillMut = useMutation({
    mutationFn: (id: string) => billingApi.deleteBill(id),
    onSuccess: invalidate,
  });

  const tariffMut = useMutation({
    mutationFn: async ({ id, data }: { id?: string; data: TariffCreate | TariffUpdate }) =>
      id ? billingApi.updateTariff(id, data as TariffUpdate) : billingApi.createTariff(data as TariffCreate),
    onSuccess: invalidate,
  });
  const deleteTariffMut = useMutation({
    mutationFn: (id: string) => billingApi.deleteTariff(id),
    onSuccess: invalidate,
  });

  const allocMut = useMutation({
    mutationFn: async ({ id, data }: { id?: string; data: AllocationCreate | AllocationUpdate }) =>
      id ? billingApi.updateAllocation(id, data as AllocationUpdate) : billingApi.createAllocation(data as AllocationCreate),
    onSuccess: invalidate,
  });
  const deleteAllocMut = useMutation({
    mutationFn: (id: string) => billingApi.deleteAllocation(id),
    onSuccess: invalidate,
  });
  const engineMut = useMutation({
    mutationFn: (req: AllocationEngineRequest) => billingApi.runEngine(req),
    onSuccess: invalidate,
  });

  const kpi = kpiQ.data;
  const bills = billsQ.data ?? [];
  const tariffs = tariffsQ.data ?? [];
  const allocations = allocQ.data ?? [];
  const report = reportQ.data;

  // Chart data — cost by utility type
  const billsByType: Record<string, number> = {};
  bills.forEach(b => {
    billsByType[b.utility_type] = (billsByType[b.utility_type] ?? 0) + b.total_amount;
  });
  const pieData = Object.entries(billsByType).map(([k, v]) => ({
    name: UTILITY_TYPE_LABELS[k as UtilityTypeBilling] ?? k,
    value: v,
    fill: UTILITY_TYPE_COLORS[k as UtilityTypeBilling] ?? "#9ca3af",
  }));

  const tabCls = (t: Tab) =>
    `px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
      tab === t
        ? "bg-blue-600 text-white"
        : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
    }`;

  const thCls = "px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide";
  const tdCls = "px-3 py-2 text-sm text-gray-700 dark:text-gray-200";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Utility Billing & Cost Allocation</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage bills, tariffs, and allocate costs to departments, lines, machines, and batches.
          </p>
        </div>
        <div className="flex gap-2">
          {tab === "bills" && (
            <>
              <button onClick={() => downloadBillsCsv({ utility_type: utilityType, status: billStatus })}
                className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800">
                Export CSV
              </button>
              <button onClick={() => setBillModal({ open: true })}
                className="px-3 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700">
                + Add Bill
              </button>
            </>
          )}
          {tab === "tariffs" && (
            <button onClick={() => setTariffModal({ open: true })}
              className="px-3 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700">
              + Add Tariff
            </button>
          )}
          {tab === "allocations" && (
            <>
              <button onClick={() => downloadAllocationsCsv({ utility_type: utilityType })}
                className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800">
                Export CSV
              </button>
              <button onClick={() => setEngineModal(true)}
                className="px-3 py-2 text-sm rounded-lg bg-purple-600 text-white hover:bg-purple-700">
                Run Engine
              </button>
              <button onClick={() => setAllocModal({ open: true })}
                className="px-3 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700">
                + Manual
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <select
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm"
          value={utilityType} onChange={e => setUtilityType(e.target.value)}>
          <option value="">All Utilities</option>
          {Object.entries(UTILITY_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        {tab === "bills" && (
          <select
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm"
            value={billStatus} onChange={e => setBillStatus(e.target.value)}>
            <option value="">All Statuses</option>
            {Object.entries(BILL_STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        )}
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        <span className="text-gray-400 text-xs">to</span>
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm" />
        <button onClick={() => { setUtilityType(""); setBillStatus(""); setDateFrom(""); setDateTo(""); }}
          className="text-xs text-blue-600 hover:underline">Clear</button>
      </div>

      {/* KPI cards — always visible */}
      {kpi && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <KpiCard label="Total Bills" value={kpi.total_bills} />
          <KpiCard label="Total Billed" value={fmt(kpi.total_billed_amount)} unit={kpi.currency_code} />
          <KpiCard label="Total Tax" value={fmt(kpi.total_tax_amount)} unit={kpi.currency_code} />
          <KpiCard label="Total Consumption" value={fmt(kpi.total_consumption)} unit={kpi.consumption_unit ?? ""} />
          <KpiCard label="Avg Unit Rate" value={fmt(kpi.avg_unit_rate, 4)} />
          <KpiCard
            label="Unpaid / Overdue"
            value={fmt(kpi.unpaid_amount)}
            unit={kpi.currency_code}
            sub={`${kpi.overdue_count} overdue · ${kpi.disputed_count} disputed`}
            highlight={kpi.overdue_count > 0}
          />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2">
        {(["bills", "tariffs", "allocations", "reports"] as Tab[]).map(t => (
          <button key={t} className={tabCls(t)} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* ── Bills tab ── */}
      {tab === "bills" && (
        <div className="space-y-6">
          {/* Cost by utility type pie */}
          {pieData.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Total Billed by Utility Type</h3>
              <div className="flex gap-6 items-center">
                <ResponsiveContainer width={260} height={220}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={60} outerRadius={90}>
                      {pieData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                    </Pie>
                    <Tooltip formatter={(v: unknown) => fmt(v as number | null | undefined)} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-col gap-1.5">
                  {pieData.map((d, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className="w-3 h-3 rounded-full inline-block" style={{ background: d.fill }} />
                      <span className="text-gray-700 dark:text-gray-300">{d.name}</span>
                      <span className="text-gray-500 ml-2">{fmt(d.value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Bills table */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700/50">
                <tr>
                  {["Bill No", "Utility", "Provider", "Period", "Consumption", "Total Amount", "Status", "Due Date", ""].map(h => (
                    <th key={h} className={thCls}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {bills.map(b => (
                  <tr key={b.id}
                    className={`hover:bg-gray-50 dark:hover:bg-gray-700/30 ${b.status === "OVERDUE" ? "bg-red-50 dark:bg-red-950/10" : ""}`}>
                    <td className={tdCls + " font-mono text-xs"}>{b.bill_no}</td>
                    <td className={tdCls}><UtilityBadge type={b.utility_type} /></td>
                    <td className={tdCls}>{b.provider_name ?? "—"}</td>
                    <td className={tdCls + " text-xs"}>
                      {b.billing_period_from} → {b.billing_period_to}
                    </td>
                    <td className={tdCls + " text-xs"}>
                      {b.consumption_quantity != null ? `${fmt(b.consumption_quantity)} ${b.consumption_unit ?? ""}` : "—"}
                    </td>
                    <td className={tdCls + " font-semibold"}>
                      {fmt(b.total_amount)} {b.currency_code}
                    </td>
                    <td className={tdCls}><StatusBadge status={b.status} /></td>
                    <td className={tdCls + " text-xs"}>{b.due_date ?? "—"}</td>
                    <td className={tdCls}>
                      <div className="flex gap-2 items-center">
                        {b.status === "VERIFIED" && (
                          <button
                            onClick={() => setGlModal({ open: true, bill: b })}
                            title="Post to GL"
                            className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 hover:bg-violet-200 dark:hover:bg-violet-800"
                          >
                            {/* Document / bank icon */}
                            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                                d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                            Post GL
                          </button>
                        )}
                        <button onClick={() => setBillModal({ open: true, item: b })}
                          className="text-xs text-blue-600 hover:underline">Edit</button>
                        <button onClick={() => { if (confirm("Delete this bill?")) deleteBillMut.mutate(b.id); }}
                          className="text-xs text-red-500 hover:underline">Del</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {bills.length === 0 && (
                  <tr><td colSpan={9} className="text-center py-10 text-gray-400">No bills found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tariffs tab ── */}
      {tab === "tariffs" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                {["Code", "Name", "Utility", "Type", "Valid From", "Valid To", "Base Rate", "Peak", "Off-Peak", "Tax %", "Active", ""].map(h => (
                  <th key={h} className={thCls}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {tariffs.map(t => (
                <tr key={t.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className={tdCls + " font-mono text-xs font-semibold"}>{t.tariff_code}</td>
                  <td className={tdCls}>{t.name}</td>
                  <td className={tdCls}><UtilityBadge type={t.utility_type} /></td>
                  <td className={tdCls + " text-xs"}>{TARIFF_TYPE_LABELS[t.tariff_type as TariffType] ?? t.tariff_type}</td>
                  <td className={tdCls + " text-xs"}>{t.effective_from}</td>
                  <td className={tdCls + " text-xs"}>{t.effective_to ?? "Open"}</td>
                  <td className={tdCls}>{fmt(t.base_rate, 4)}/{t.unit}</td>
                  <td className={tdCls + " text-xs"}>{t.peak_rate != null ? fmt(t.peak_rate, 4) : "—"}</td>
                  <td className={tdCls + " text-xs"}>{t.offpeak_rate != null ? fmt(t.offpeak_rate, 4) : "—"}</td>
                  <td className={tdCls + " text-xs"}>{t.tax_rate_pct != null ? `${t.tax_rate_pct}%` : "—"}</td>
                  <td className={tdCls}>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${t.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {t.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className={tdCls}>
                    <div className="flex gap-2">
                      <button onClick={() => setTariffModal({ open: true, item: t })}
                        className="text-xs text-blue-600 hover:underline">Edit</button>
                      <button onClick={() => { if (confirm("Delete this tariff?")) deleteTariffMut.mutate(t.id); }}
                        className="text-xs text-red-500 hover:underline">Del</button>
                    </div>
                  </td>
                </tr>
              ))}
              {tariffs.length === 0 && (
                <tr><td colSpan={12} className="text-center py-10 text-gray-400">No tariffs found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Allocations tab ── */}
      {tab === "allocations" && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                {["Alloc No", "Utility", "Date", "Method", "Target", "Dept / Line", "Source Cost", "Allocated Cost", "Approved", ""].map(h => (
                  <th key={h} className={thCls}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {allocations.map(a => (
                <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className={tdCls + " font-mono text-xs"}>{a.allocation_no}</td>
                  <td className={tdCls}><UtilityBadge type={a.utility_type} /></td>
                  <td className={tdCls + " text-xs"}>{a.allocation_date}</td>
                  <td className={tdCls + " text-xs"}>{ALLOCATION_METHOD_LABELS[a.allocation_method as AllocationMethod] ?? a.allocation_method}</td>
                  <td className={tdCls + " text-xs"}>
                    <div className="font-medium">{a.target_name ?? a.target_id ?? "—"}</div>
                    <div className="text-gray-400">{TARGET_TYPE_LABELS[a.target_type as TargetType] ?? a.target_type ?? ""}</div>
                  </td>
                  <td className={tdCls + " text-xs"}>
                    {a.department && <div>{a.department}</div>}
                    {a.production_line && <div className="text-gray-400">{a.production_line}</div>}
                  </td>
                  <td className={tdCls + " text-xs"}>{a.source_cost != null ? `${fmt(a.source_cost)} ${a.currency_code}` : "—"}</td>
                  <td className={tdCls + " font-semibold"}>{fmt(a.allocated_cost)} {a.currency_code}</td>
                  <td className={tdCls}>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${a.is_approved ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                      {a.is_approved ? "Approved" : "Pending"}
                    </span>
                  </td>
                  <td className={tdCls}>
                    <div className="flex gap-2">
                      {!a.is_approved && (
                        <button onClick={() => allocMut.mutate({ id: a.id, data: { is_approved: true } })}
                          className="text-xs text-green-600 hover:underline">Approve</button>
                      )}
                      <button onClick={() => setAllocModal({ open: true, item: a })}
                        className="text-xs text-blue-600 hover:underline">Edit</button>
                      <button onClick={() => { if (confirm("Delete allocation?")) deleteAllocMut.mutate(a.id); }}
                        className="text-xs text-red-500 hover:underline">Del</button>
                    </div>
                  </td>
                </tr>
              ))}
              {allocations.length === 0 && (
                <tr><td colSpan={10} className="text-center py-10 text-gray-400">No allocations found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Reports tab ── */}
      {tab === "reports" && (
        <div className="space-y-6">
          <div className="flex items-center gap-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Group By:</label>
            {(["target_type", "department", "production_line", "machine_ref", "batch_no"] as const).map(g => (
              <button key={g}
                onClick={() => setReportGroupBy(g)}
                className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${reportGroupBy === g ? "bg-blue-600 text-white" : "border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"}`}>
                {g.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase())}
              </button>
            ))}
          </div>

          {report && (
            <div className="space-y-6">
              {/* Bar chart */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
                  Allocated Cost by {reportGroupBy.replace("_", " ")}
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={report.rows.slice(0, 20).map(r => ({
                      name: r.target_name ?? r.target_id ?? r.target_type ?? "—",
                      cost: Number(r.allocated_cost),
                      fill: UTILITY_TYPE_COLORS[r.utility_type as UtilityTypeBilling] ?? "#60a5fa",
                    }))}
                    layout="vertical" margin={{ left: 120, right: 20, top: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => fmt(v, 0)} />
                    <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={115} />
                    <Tooltip formatter={(v: unknown) => [fmt(v as number | null | undefined), "Allocated Cost"]} />
                    <Bar dataKey="cost" radius={[0, 4, 4, 0]}>
                      {report.rows.slice(0, 20).map((r, i) => (
                        <Cell key={i} fill={UTILITY_TYPE_COLORS[r.utility_type as UtilityTypeBilling] ?? "#60a5fa"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Report table */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                    Cost Detail — Grand Total: {fmt(Number(report.grand_total))}
                  </h3>
                </div>
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      {["Target", "Target Name", "Utility", "Allocated Cost", "Qty", "Unit", "Cost/Unit", "Records"].map(h => (
                        <th key={h} className={thCls}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {report.rows.map((r, i) => (
                      <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                        <td className={tdCls + " text-xs font-mono"}>{r.target_type ?? "—"}</td>
                        <td className={tdCls}>{r.target_name ?? r.target_id ?? "—"}</td>
                        <td className={tdCls}>{r.utility_type ? <UtilityBadge type={r.utility_type} /> : "—"}</td>
                        <td className={tdCls + " font-semibold"}>{fmt(Number(r.allocated_cost))}</td>
                        <td className={tdCls + " text-xs"}>{r.allocated_quantity != null ? fmt(Number(r.allocated_quantity)) : "—"}</td>
                        <td className={tdCls + " text-xs"}>{r.quantity_unit ?? "—"}</td>
                        <td className={tdCls + " text-xs"}>{r.cost_per_unit != null ? fmt(Number(r.cost_per_unit), 4) : "—"}</td>
                        <td className={tdCls + " text-center"}>{r.record_count}</td>
                      </tr>
                    ))}
                    {report.rows.length === 0 && (
                      <tr><td colSpan={8} className="text-center py-10 text-gray-400">No data.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {billModal.open && (
        <BillModal
          initial={billModal.item}
          onClose={() => setBillModal({ open: false })}
          onSave={async data => { await billMut.mutateAsync({ id: billModal.item?.id, data }); }}
        />
      )}
      {tariffModal.open && (
        <TariffModal
          initial={tariffModal.item}
          onClose={() => setTariffModal({ open: false })}
          onSave={async data => { await tariffMut.mutateAsync({ id: tariffModal.item?.id, data }); }}
        />
      )}
      {allocModal.open && (
        <AllocationModal
          initial={allocModal.item}
          onClose={() => setAllocModal({ open: false })}
          onSave={async data => { await allocMut.mutateAsync({ id: allocModal.item?.id, data }); }}
        />
      )}
      {engineModal && (
        <EngineModal
          bills={bills}
          onClose={() => setEngineModal(false)}
          onRun={async req => { await engineMut.mutateAsync(req); }}
        />
      )}
      {glModal.open && glModal.bill && (
        <PostToGLModal
          bill={glModal.bill}
          onClose={() => setGlModal({ open: false })}
          onSuccess={msg => showToast(msg, "success")}
        />
      )}
      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-[100] flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white ${toast.type === "success" ? "bg-green-600" : "bg-red-600"}`}>
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)} className="font-bold text-white/80 hover:text-white">&times;</button>
        </div>
      )}
    </div>
  );
}
