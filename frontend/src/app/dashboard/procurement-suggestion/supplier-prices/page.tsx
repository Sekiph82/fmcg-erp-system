"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { psApi, SupplierItemPriceOut, SupplierItemPriority, fmt } from "@/lib/procurement_suggestion";

const PRIORITY_OPTIONS: SupplierItemPriority[] = ["PRIMARY", "SECONDARY", "TERTIARY", "FALLBACK"];

function PriceForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<SupplierItemPriceOut>;
  onSave: (data: Partial<SupplierItemPriceOut>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    supplier_id: initial?.supplier_id ?? "",
    material_id: initial?.material_id ?? "",
    unit_price: initial?.unit_price ?? 0,
    currency: initial?.currency ?? "KES",
    moq: initial?.moq ?? 1,
    pack_size: initial?.pack_size ?? "",
    lead_time_days: initial?.lead_time_days ?? 0,
    buffer_days: initial?.buffer_days ?? 0,
    customs_days: initial?.customs_days ?? 0,
    priority: initial?.priority ?? "PRIMARY",
    reliability_score: initial?.reliability_score ?? "",
    contract_no: initial?.contract_no ?? "",
    is_active: initial?.is_active ?? true,
    valid_from: initial?.valid_from ?? "",
    valid_to: initial?.valid_to ?? "",
    notes: initial?.notes ?? "",
  });

  const set = (k: string, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...form,
      pack_size:        form.pack_size        ? Number(form.pack_size)        : undefined,
      reliability_score: form.reliability_score ? Number(form.reliability_score) : undefined,
      valid_from: form.valid_from || undefined,
      valid_to:   form.valid_to   || undefined,
    });
  };

  const field = (label: string, key: string, type = "text", extra?: React.InputHTMLAttributes<HTMLInputElement>) => (
    <div>
      <label className="text-xs text-gray-600 block mb-0.5">{label}</label>
      <input
        type={type}
        value={(form as Record<string, unknown>)[key] as string}
        onChange={(e) => set(key, e.target.value)}
        className="w-full border rounded px-2 py-1.5 text-sm"
        {...extra}
      />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {field("Supplier ID", "supplier_id")}
        {field("Material ID", "material_id")}
        {field("Unit Price", "unit_price", "number")}
        {field("Currency", "currency")}
        {field("MOQ", "moq", "number")}
        {field("Pack Size", "pack_size", "number")}
        {field("Lead Time Days", "lead_time_days", "number")}
        {field("Buffer Days", "buffer_days", "number")}
        {field("Customs Days", "customs_days", "number")}
        <div>
          <label className="text-xs text-gray-600 block mb-0.5">Priority</label>
          <select
            value={form.priority}
            onChange={(e) => set("priority", e.target.value)}
            className="w-full border rounded px-2 py-1.5 text-sm"
          >
            {PRIORITY_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        {field("Reliability Score (0-100)", "reliability_score", "number")}
        {field("Contract No", "contract_no")}
        {field("Valid From", "valid_from", "date")}
        {field("Valid To", "valid_to", "date")}
      </div>
      <div>
        <label className="text-xs text-gray-600">Notes</label>
        <textarea
          value={form.notes}
          onChange={(e) => set("notes", e.target.value)}
          rows={2}
          className="w-full border rounded px-2 py-1.5 text-sm mt-0.5 resize-none"
        />
      </div>
      <div className="flex items-center gap-2">
        <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} id="is_active" />
        <label htmlFor="is_active" className="text-sm text-gray-600">Active</label>
      </div>
      <div className="flex gap-2 pt-2">
        <button type="submit" className="flex-1 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
          {initial?.id ? "Update" : "Create"} Price
        </button>
        <button type="button" onClick={onCancel} className="flex-1 py-2 border rounded text-sm hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function SupplierPricesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<SupplierItemPriceOut | null>(null);

  const { data: prices, isLoading } = useQuery({
    queryKey: ["supplier-prices"],
    queryFn: () => psApi.listSupplierPrices(),
  });

  const create = useMutation({
    mutationFn: psApi.createSupplierPrice,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["supplier-prices"] }); setShowForm(false); },
  });

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<SupplierItemPriceOut> }) =>
      psApi.updateSupplierPrice(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["supplier-prices"] }); setEditing(null); },
  });

  const del = useMutation({
    mutationFn: psApi.deleteSupplierPrice,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["supplier-prices"] }),
  });

  const priorityBadge = (p: string) => ({
    PRIMARY:   "bg-blue-100 text-blue-700",
    SECONDARY: "bg-indigo-100 text-indigo-700",
    TERTIARY:  "bg-gray-100 text-gray-600",
    FALLBACK:  "bg-orange-100 text-orange-700",
  }[p] ?? "bg-gray-100 text-gray-600");

  return (
    <div className="p-6 space-y-4">
      {(showForm || editing) && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl shadow-xl overflow-y-auto max-h-[90vh]">
            <h2 className="font-semibold mb-4">{editing ? "Edit Supplier Price" : "Add Supplier Price"}</h2>
            <PriceForm
              initial={editing ?? undefined}
              onSave={(data) => {
                if (editing) {
                  update.mutate({ id: editing.id, payload: data });
                } else {
                  create.mutate(data as Parameters<typeof create.mutate>[0]);
                }
              }}
              onCancel={() => { setShowForm(false); setEditing(null); }}
            />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Supplier-Item Price Mappings</h1>
          <p className="text-sm text-gray-500">Define price, MOQ, lead time per supplier-material combination</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
        >
          + Add Price Mapping
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="text-left px-3 py-2">Material</th>
              <th className="text-left px-3 py-2">Supplier</th>
              <th className="text-left px-3 py-2">Priority</th>
              <th className="text-right px-3 py-2">Unit Price</th>
              <th className="text-right px-3 py-2">MOQ</th>
              <th className="text-right px-3 py-2">Lead Days</th>
              <th className="text-right px-3 py-2">Buffer</th>
              <th className="text-right px-3 py-2">Customs</th>
              <th className="text-right px-3 py-2">Reliability</th>
              <th className="text-left px-3 py-2">Contract</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-left px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={12} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>}
            {!isLoading && !prices?.length && (
              <tr><td colSpan={12} className="px-4 py-8 text-center text-gray-400">
                No price mappings yet. Add supplier-item prices to enable the procurement engine.
              </td></tr>
            )}
            {(prices ?? []).map((p) => (
              <tr key={p.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-3 py-2">
                  <p className="font-medium">{p.material_name ?? "—"}</p>
                  <p className="text-xs text-gray-400 font-mono">{p.material_code}</p>
                </td>
                <td className="px-3 py-2">{p.supplier_name ?? p.supplier_id}</td>
                <td className="px-3 py-2">
                  <span className={`px-1.5 py-0.5 rounded text-xs ${priorityBadge(p.priority)}`}>{p.priority}</span>
                </td>
                <td className="px-3 py-2 text-right font-mono">{p.currency} {fmt(p.unit_price)}</td>
                <td className="px-3 py-2 text-right">{fmt(p.moq, 0)}</td>
                <td className="px-3 py-2 text-right">{p.lead_time_days}d</td>
                <td className="px-3 py-2 text-right">{p.buffer_days}d</td>
                <td className="px-3 py-2 text-right">{p.customs_days}d</td>
                <td className="px-3 py-2 text-right">{p.reliability_score != null ? `${p.reliability_score}%` : "—"}</td>
                <td className="px-3 py-2 text-xs">{p.contract_no ?? "—"}</td>
                <td className="px-3 py-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {p.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-1">
                    <button onClick={() => setEditing(p)} className="text-blue-600 hover:underline text-xs">Edit</button>
                    <button
                      onClick={() => { if (confirm("Delete this price mapping?")) del.mutate(p.id); }}
                      className="text-red-500 hover:underline text-xs"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
