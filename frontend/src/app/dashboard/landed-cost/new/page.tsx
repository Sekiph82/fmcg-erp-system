"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  lcApi, LandedCostType, LCAllocationMethod, LCReferenceType,
  COST_TYPE_LABEL, ALLOC_METHOD_LABEL,
} from "@/lib/landed_cost";

const COST_TYPES = Object.keys(COST_TYPE_LABEL) as LandedCostType[];
const ALLOC_METHODS = Object.keys(ALLOC_METHOD_LABEL) as LCAllocationMethod[];
const REF_TYPES: LCReferenceType[] = ["MANUAL", "GRN", "SHIPMENT", "PO"];

interface CostLineForm {
  cost_type: LandedCostType;
  description: string;
  vendor_name: string;
  amount_fc: string;
  currency_code: string;
  exchange_rate: string;
  is_included_in_valuation: boolean;
  account_code: string;
}

const defaultLine = (): CostLineForm => ({
  cost_type: "FREIGHT_SEA",
  description: "",
  vendor_name: "",
  amount_fc: "",
  currency_code: "USD",
  exchange_rate: "1",
  is_included_in_valuation: true,
  account_code: "",
});

export default function NewLandedCostPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    reference_type: "MANUAL" as LCReferenceType,
    vendor_name: "",
    bill_no: "",
    bill_date: "",
    currency_code: "USD",
    exchange_rate: "1",
    allocation_method: "BY_VALUE" as LCAllocationMethod,
    notes: "",
  });

  const [lines, setLines] = useState<CostLineForm[]>([defaultLine()]);
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => lcApi.create(payload),
    onSuccess: (doc) => router.push(`/dashboard/landed-cost/${doc.id}`),
    onError: (e: Error) => setError(e.message),
  });

  function addLine() {
    setLines((prev) => [...prev, defaultLine()]);
  }

  function removeLine(i: number) {
    setLines((prev) => prev.filter((_, idx) => idx !== i));
  }

  function updateLine(i: number, field: keyof CostLineForm, value: string | boolean) {
    setLines((prev) => prev.map((l, idx) => idx === i ? { ...l, [field]: value } : l));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (lines.length === 0) { setError("Add at least one cost line."); return; }
    setError("");
    mutation.mutate({
      ...form,
      exchange_rate: parseFloat(form.exchange_rate) || 1,
      cost_lines: lines.map((l) => ({
        ...l,
        amount_fc: parseFloat(l.amount_fc) || 0,
        exchange_rate: parseFloat(l.exchange_rate) || 1,
      })),
      grn_links: [],
    });
  }

  return (
    <form onSubmit={handleSubmit} className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-gray-900">New Landed Cost Document</h1>

      {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>}

      {/* Header fields */}
      <div className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="font-semibold text-gray-700">Document Header</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Reference Type</label>
            <select
              className="border rounded-lg px-3 py-2 text-sm w-full"
              value={form.reference_type}
              onChange={(e) => setForm({ ...form, reference_type: e.target.value as LCReferenceType })}
            >
              {REF_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Vendor / Carrier Name</label>
            <input className="border rounded-lg px-3 py-2 text-sm w-full"
              value={form.vendor_name} onChange={(e) => setForm({ ...form, vendor_name: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Bill / Invoice No</label>
            <input className="border rounded-lg px-3 py-2 text-sm w-full"
              value={form.bill_no} onChange={(e) => setForm({ ...form, bill_no: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Bill Date</label>
            <input type="date" className="border rounded-lg px-3 py-2 text-sm w-full"
              value={form.bill_date} onChange={(e) => setForm({ ...form, bill_date: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Currency</label>
            <input className="border rounded-lg px-3 py-2 text-sm w-full uppercase"
              value={form.currency_code} maxLength={10}
              onChange={(e) => setForm({ ...form, currency_code: e.target.value.toUpperCase() })} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Exchange Rate (to Base)</label>
            <input type="number" step="any" className="border rounded-lg px-3 py-2 text-sm w-full"
              value={form.exchange_rate} onChange={(e) => setForm({ ...form, exchange_rate: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Allocation Method</label>
            <select className="border rounded-lg px-3 py-2 text-sm w-full"
              value={form.allocation_method}
              onChange={(e) => setForm({ ...form, allocation_method: e.target.value as LCAllocationMethod })}
            >
              {ALLOC_METHODS.map((m) => <option key={m} value={m}>{ALLOC_METHOD_LABEL[m]}</option>)}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs text-gray-500 mb-1">Notes</label>
            <input className="border rounded-lg px-3 py-2 text-sm w-full"
              value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>
      </div>

      {/* Cost lines */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-700">Cost Components</h2>
          <button type="button" onClick={addLine}
            className="text-xs px-3 py-1.5 border rounded-lg hover:bg-gray-50 text-blue-600">
            + Add Line
          </button>
        </div>

        {lines.map((line, i) => (
          <div key={i} className="border rounded-lg p-4 space-y-3 bg-gray-50">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Cost Type</label>
                <select className="border rounded px-2 py-1.5 text-sm w-full bg-white"
                  value={line.cost_type}
                  onChange={(e) => updateLine(i, "cost_type", e.target.value)}>
                  {COST_TYPES.map((t) => <option key={t} value={t}>{COST_TYPE_LABEL[t]}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Amount (FC)</label>
                <input type="number" step="any" className="border rounded px-2 py-1.5 text-sm w-full bg-white"
                  value={line.amount_fc}
                  onChange={(e) => updateLine(i, "amount_fc", e.target.value)} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Currency</label>
                <input className="border rounded px-2 py-1.5 text-sm w-full bg-white uppercase" maxLength={10}
                  value={line.currency_code}
                  onChange={(e) => updateLine(i, "currency_code", e.target.value.toUpperCase())} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Exchange Rate</label>
                <input type="number" step="any" className="border rounded px-2 py-1.5 text-sm w-full bg-white"
                  value={line.exchange_rate}
                  onChange={(e) => updateLine(i, "exchange_rate", e.target.value)} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Vendor / Agent</label>
                <input className="border rounded px-2 py-1.5 text-sm w-full bg-white"
                  value={line.vendor_name}
                  onChange={(e) => updateLine(i, "vendor_name", e.target.value)} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Description</label>
                <input className="border rounded px-2 py-1.5 text-sm w-full bg-white"
                  value={line.description}
                  onChange={(e) => updateLine(i, "description", e.target.value)} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Account Code</label>
                <input className="border rounded px-2 py-1.5 text-sm w-full bg-white"
                  value={line.account_code}
                  onChange={(e) => updateLine(i, "account_code", e.target.value)} />
              </div>
              <div className="flex items-end gap-3">
                <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                  <input type="checkbox" checked={line.is_included_in_valuation}
                    onChange={(e) => updateLine(i, "is_included_in_valuation", e.target.checked)} />
                  Include in valuation
                </label>
                {lines.length > 1 && (
                  <button type="button" onClick={() => removeLine(i)}
                    className="text-xs text-red-500 hover:underline ml-auto">
                    Remove
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {mutation.isPending ? "Creating…" : "Create Document"}
        </button>
        <button type="button" onClick={() => router.back()}
          className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </form>
  );
}
