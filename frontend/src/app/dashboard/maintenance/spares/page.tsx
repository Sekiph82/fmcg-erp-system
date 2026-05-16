"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { maintenanceApi, SparePart } from "@/lib/maintenance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { RequirePermission } from "@/components/PermissionGuard";

export default function SparesPage() {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [editPart, setEditPart] = useState<SparePart | null>(null);
  const [showUsage, setShowUsage] = useState(false);
  const [filterLow, setFilterLow] = useState(false);

  const { data: parts = [], isLoading } = useQuery({
    queryKey: ["maint-spares"],
    queryFn: () => maintenanceApi.listSpareParts(),
  });

  const { data: assets = [] } = useQuery({
    queryKey: ["maint-assets"],
    queryFn: () => maintenanceApi.listAssets(),
  });

  const createPart = useMutation({
    mutationFn: (data: object) => maintenanceApi.createSparePart(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-spares"] }); setShowNew(false); },
  });

  const updatePart = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => maintenanceApi.updateSparePart(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-spares"] }); setEditPart(null); },
  });

  const recordUsage = useMutation({
    mutationFn: (data: object) => maintenanceApi.recordSpareUsage(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-spares"] }); setShowUsage(false); },
  });

  const lowStock = parts.filter((p) => p.reorder_level != null && p.current_stock <= p.reorder_level!);
  const filtered = filterLow ? lowStock : parts;

  return (
    <RequirePermission permission="maintenance.view">
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Spare Parts</h1>
          <p className="text-sm text-gray-500 mt-1">Spare parts inventory and usage tracking</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowUsage(true)}>Record Usage</Button>
          <Button onClick={() => setShowNew(true)}>Add Part</Button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setFilterLow(!filterLow)}
          className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
            filterLow ? "bg-orange-500 text-white" : "bg-white border text-gray-600 hover:border-orange-300"
          }`}
        >
          Low Stock Only ({lowStock.length})
        </button>
        <span className="text-sm text-gray-500">{filtered.length} parts</span>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Part No</th>
                <th className="px-5 py-2 text-left">Name</th>
                <th className="px-5 py-2 text-left">Supplier</th>
                <th className="px-5 py-2 text-right">Stock</th>
                <th className="px-5 py-2 text-right">Reorder Lvl</th>
                <th className="px-5 py-2 text-right">Unit Cost</th>
                <th className="px-5 py-2 text-right">Lead Time</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((p) => {
                const isLow = p.reorder_level != null && p.current_stock <= p.reorder_level!;
                return (
                  <tr key={p.id} className={`hover:bg-gray-50 ${isLow ? "bg-orange-50" : ""}`}>
                    <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-700">{p.part_no}</td>
                    <td className="px-5 py-3">
                      <p className="font-medium text-gray-900">{p.name}</p>
                      {p.description && <p className="text-xs text-gray-400 truncate max-w-xs">{p.description}</p>}
                    </td>
                    <td className="px-5 py-3 text-gray-500">{p.supplier || "—"}</td>
                    <td className={`px-5 py-3 text-right font-semibold ${isLow ? "text-orange-600" : "text-gray-700"}`}>
                      {Number(p.current_stock).toLocaleString()} {p.unit}
                    </td>
                    <td className="px-5 py-3 text-right text-gray-500">
                      {p.reorder_level != null ? `${Number(p.reorder_level).toLocaleString()} ${p.unit}` : "—"}
                    </td>
                    <td className="px-5 py-3 text-right">{p.unit_cost != null ? `KES ${Number(p.unit_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "—"}</td>
                    <td className="px-5 py-3 text-right">{p.lead_time_days != null ? `${p.lead_time_days}d` : "—"}</td>
                    <td className="px-5 py-3">
                      {isLow ? <Badge label="Low Stock" variant="yellow" /> : <Badge label="OK" variant="green" />}
                    </td>
                    <td className="px-5 py-3">
                      <button className="text-xs text-indigo-600 hover:underline" onClick={() => setEditPart(p)}>Edit</button>
                    </td>
                  </tr>
                );
              })}
              {filtered.length === 0 && (
                <tr><td colSpan={9} className="px-5 py-8 text-center text-gray-400">No spare parts</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {showNew && (
        <SparePartModal
          title="Add Spare Part"
          onClose={() => setShowNew(false)}
          onSubmit={(d) => createPart.mutate(d)}
          loading={createPart.isPending}
        />
      )}
      {editPart && (
        <SparePartModal
          title="Edit Spare Part"
          initial={editPart}
          onClose={() => setEditPart(null)}
          onSubmit={(d) => updatePart.mutate({ id: editPart.id, data: d })}
          loading={updatePart.isPending}
        />
      )}
      {showUsage && (
        <RecordUsageModal
          parts={parts}
          assets={assets}
          onClose={() => setShowUsage(false)}
          onSubmit={(d) => recordUsage.mutate(d)}
          loading={recordUsage.isPending}
        />
      )}
    </div>
    </RequirePermission>
  );
}

function SparePartModal({ title, initial, onClose, onSubmit, loading }: { title: string; initial?: SparePart; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const [form, setForm] = useState({
    part_no: initial?.part_no ?? "",
    name: initial?.name ?? "",
    description: initial?.description ?? "",
    unit: initial?.unit ?? "pcs",
    current_stock: initial?.current_stock?.toString() ?? "0",
    reorder_level: initial?.reorder_level?.toString() ?? "",
    unit_cost: initial?.unit_cost?.toString() ?? "",
    supplier: initial?.supplier ?? "",
    lead_time_days: initial?.lead_time_days?.toString() ?? "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4">
        <h2 className="font-semibold text-lg">{title}</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Part No</label>
            <input className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50" value={form.part_no} onChange={(e) => set("part_no", e.target.value)} disabled={!!initial} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Unit</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.unit} onChange={(e) => set("unit", e.target.value)} placeholder="pcs, litre, kg…" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.description} onChange={(e) => set("description", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Current Stock</label>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.current_stock} onChange={(e) => set("current_stock", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reorder Level</label>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.reorder_level} onChange={(e) => set("reorder_level", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Unit Cost (KES)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.unit_cost} onChange={(e) => set("unit_cost", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Lead Time (days)</label>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.lead_time_days} onChange={(e) => set("lead_time_days", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Supplier</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.supplier} onChange={(e) => set("supplier", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            ...form,
            current_stock: parseFloat(form.current_stock) || 0,
            reorder_level: form.reorder_level ? parseFloat(form.reorder_level) : undefined,
            unit_cost: form.unit_cost ? parseFloat(form.unit_cost) : undefined,
            lead_time_days: form.lead_time_days ? parseInt(form.lead_time_days) : undefined,
          })}>Save</Button>
        </div>
      </div>
    </div>
  );
}

function RecordUsageModal({ parts, assets, onClose, onSubmit, loading }: {
  parts: SparePart[];
  assets: { id: string; name: string; asset_no: string }[];
  onClose: () => void;
  onSubmit: (d: object) => void;
  loading: boolean;
}) {
  const [form, setForm] = useState({ spare_part_id: "", asset_id: "", quantity_used: "", unit_cost: "", notes: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const selectedPart = parts.find((p) => p.id === form.spare_part_id);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">Record Spare Part Usage</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Spare Part</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.spare_part_id} onChange={(e) => set("spare_part_id", e.target.value)}>
              <option value="">Select part…</option>
              {parts.map((p) => <option key={p.id} value={p.id}>{p.part_no} — {p.name} (stock: {p.current_stock} {p.unit})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Asset</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.asset_id} onChange={(e) => set("asset_id", e.target.value)}>
              <option value="">Select asset…</option>
              {assets.map((a) => <option key={a.id} value={a.id}>{a.asset_no} — {a.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Quantity Used</label>
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" value={form.quantity_used} onChange={(e) => set("quantity_used", e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Unit Cost (KES)</label>
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" placeholder={selectedPart?.unit_cost?.toString()} value={form.unit_cost} onChange={(e) => set("unit_cost", e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            spare_part_id: form.spare_part_id,
            asset_id: form.asset_id,
            quantity_used: parseFloat(form.quantity_used) || 0,
            unit_cost: form.unit_cost ? parseFloat(form.unit_cost) : undefined,
            notes: form.notes || undefined,
          })}>Record</Button>
        </div>
      </div>
    </div>
  );
}
