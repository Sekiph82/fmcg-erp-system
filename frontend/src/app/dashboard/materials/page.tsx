"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { materialsApi, Material, MaterialCreate, MaterialType, UnitOfMeasure } from "@/lib/materials";
import { ImportModal } from "@/components/import/ImportModal";
import { RequirePermission } from "@/components/PermissionGuard";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";

const TYPE_LABELS: Record<MaterialType, string> = {
  RAW:          "Raw",
  PACKAGING:    "Packaging",
  SEMI_FINISHED:"Semi-Finished",
  CONSUMABLE:   "Consumable",
};

const TYPE_VARIANT: Record<MaterialType, "green" | "blue" | "yellow" | "gray"> = {
  RAW:          "green",
  PACKAGING:    "blue",
  SEMI_FINISHED:"yellow",
  CONSUMABLE:   "gray",
};

const UOM_OPTIONS: UnitOfMeasure[] = ["PCS","KG","G","L","ML","BOX","CARTON","PALLET"];
const TYPE_OPTIONS: MaterialType[]  = ["RAW","PACKAGING","SEMI_FINISHED","CONSUMABLE"];

const EMPTY: MaterialCreate = {
  code: "", name: "", material_type: "RAW", uom: "KG",
  description: "", reorder_point: 0, standard_cost: undefined,
  lead_time_days: 7, is_active: true,
};

function MaterialForm({
  initial, onSave, onCancel, isPending,
}: {
  initial: MaterialCreate;
  onSave: (d: MaterialCreate) => void;
  onCancel: () => void;
  isPending: boolean;
}) {
  const [form, setForm] = useState<MaterialCreate>(initial);
  const set = <K extends keyof MaterialCreate>(k: K, v: MaterialCreate[K]) =>
    setForm((f) => ({ ...f, [k]: v }));
  const f = (k: keyof MaterialCreate) => ({
    value: String((form as unknown as Record<string, unknown>)[k] ?? ""),
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      set(k, e.target.value as never),
  });

  return (
    <div className="bg-white border rounded-xl p-6 space-y-4 shadow-sm">
      <h3 className="font-semibold text-gray-900">{initial.code ? "Edit Material" : "New Material"}</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Code *</label>
          <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="MAT001" {...f("code")} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Name *</label>
          <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Tomato Paste" {...f("name")} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Type *</label>
          <select className="w-full border rounded-lg px-3 py-2 text-sm" {...f("material_type")}>
            {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{TYPE_LABELS[t]}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Unit of Measure *</label>
          <select className="w-full border rounded-lg px-3 py-2 text-sm" {...f("uom")}>
            {UOM_OPTIONS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Standard Cost</label>
          <input type="number" step="0.01" className="w-full border rounded-lg px-3 py-2 text-sm"
            value={form.standard_cost ?? ""}
            onChange={(e) => set("standard_cost", e.target.value ? Number(e.target.value) : undefined)} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Lead Time (days)</label>
          <input type="number" min={0} className="w-full border rounded-lg px-3 py-2 text-sm"
            value={form.lead_time_days ?? ""}
            onChange={(e) => set("lead_time_days", Number(e.target.value))} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Reorder Point</label>
          <input type="number" min={0} className="w-full border rounded-lg px-3 py-2 text-sm"
            value={form.reorder_point ?? ""}
            onChange={(e) => set("reorder_point", Number(e.target.value))} />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Status</label>
          <select className="w-full border rounded-lg px-3 py-2 text-sm"
            value={form.is_active ? "ACTIVE" : "INACTIVE"}
            onChange={(e) => set("is_active", e.target.value === "ACTIVE")}>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
        <div className="col-span-2">
          <label className="block text-xs text-gray-500 mb-1">Description</label>
          <textarea className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} {...f("description")} />
        </div>
      </div>
      <div className="flex gap-3 pt-1">
        <button
          onClick={() => onSave(form)}
          disabled={!form.code || !form.name || isPending}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          {isPending ? "Saving…" : "Save Material"}
        </button>
        <button onClick={onCancel} className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </div>
  );
}

function MaterialsContent() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<MaterialType | "">("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Material | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: materials = [], isLoading } = useQuery({
    queryKey: ["materials"],
    queryFn: () => materialsApi.list(0, 500),
  });

  const createMutation = useMutation({
    mutationFn: (d: MaterialCreate) => materialsApi.create(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["materials"] }); setShowForm(false); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MaterialCreate> }) =>
      materialsApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["materials"] }); setEditing(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => materialsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["materials"] }); setDeletingId(null); },
  });

  const deletingMaterial = materials.find((m) => m.id === deletingId);

  const filtered = materials.filter((m) => {
    const matchSearch = !search
      || m.code.toLowerCase().includes(search.toLowerCase())
      || m.name.toLowerCase().includes(search.toLowerCase());
    const matchType = !typeFilter || m.material_type === typeFilter;
    return matchSearch && matchType;
  });

  const typeCounts = TYPE_OPTIONS.reduce<Record<string, number>>((acc, t) => {
    acc[t] = materials.filter((m) => m.material_type === t).length;
    return acc;
  }, {});

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Materials</h1>
          <p className="text-sm text-gray-500 mt-1">{materials.length} raw materials &amp; inputs</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal
            module="materials"
            onSuccess={() => qc.invalidateQueries({ queryKey: ["materials"] })}
          />
          <button
            onClick={() => { setShowForm(true); setEditing(null); }}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
          >
            + New Material
          </button>
        </div>
      </div>

      {/* Type summary tiles */}
      <div className="grid grid-cols-4 gap-3">
        {TYPE_OPTIONS.map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(typeFilter === t ? "" : t)}
            className={[
              "bg-white border rounded-xl px-4 py-3 text-center hover:border-indigo-300 transition-colors",
              typeFilter === t ? "border-indigo-400 ring-1 ring-indigo-300" : "",
            ].join(" ")}
          >
            <p className="text-xs text-gray-500">{TYPE_LABELS[t]}</p>
            <p className="text-xl font-bold mt-1">{typeCounts[t] ?? 0}</p>
          </button>
        ))}
      </div>

      {/* Form */}
      {(showForm || editing) && (
        <MaterialForm
          initial={editing ? {
            code: editing.code,
            name: editing.name,
            material_type: editing.material_type,
            uom: editing.uom,
            description: editing.description,
            reorder_point: editing.reorder_point,
            standard_cost: editing.standard_cost,
            lead_time_days: editing.lead_time_days,
            is_active: editing.is_active,
          } : EMPTY}
          onSave={(data) => {
            if (editing) {
              updateMutation.mutate({ id: editing.id, data });
            } else {
              createMutation.mutate(data);
            }
          }}
          onCancel={() => { setShowForm(false); setEditing(null); }}
          isPending={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <input
          placeholder="Search code or name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm w-56"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as MaterialType | "")}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Types</option>
          {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{TYPE_LABELS[t]}</option>)}
        </select>
        {(search || typeFilter) && (
          <button
            onClick={() => { setSearch(""); setTypeFilter(""); }}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white border rounded-xl overflow-hidden">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-400 text-center">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="p-6 text-sm text-gray-400 text-center">No materials found</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 text-left">Code</th>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">UOM</th>
                <th className="px-4 py-2 text-right">Std Cost</th>
                <th className="px-4 py-2 text-right">Lead Time</th>
                <th className="px-4 py-2 text-right">Reorder Pt.</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{m.code}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{m.name}</td>
                  <td className="px-4 py-3">
                    <Badge label={TYPE_LABELS[m.material_type]} variant={TYPE_VARIANT[m.material_type]} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">{m.uom}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">
                    {m.standard_cost != null ? m.standard_cost.toLocaleString() : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">{m.lead_time_days}d</td>
                  <td className="px-4 py-3 text-right text-gray-500">{m.reorder_point}</td>
                  <td className="px-4 py-3">
                    {m.is_active
                      ? <span className="text-xs font-medium text-green-600">Active</span>
                      : <span className="text-xs text-gray-400">Inactive</span>}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-3">
                      <button
                        onClick={() => { setEditing(m); setShowForm(false); }}
                        className="text-xs text-indigo-600 hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setDeletingId(m.id)}
                        className="text-xs text-red-500 hover:text-red-700 hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Delete Confirm Modal */}
      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title="Delete Material">
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete{" "}
          <span className="font-semibold text-gray-900">{deletingMaterial?.name}</span>{" "}
          <span className="font-mono text-xs text-gray-500">({deletingMaterial?.code})</span>?
          This action cannot be undone.
        </p>
        {deleteMutation.error && <p className="text-sm text-red-600 mb-3">Failed to delete material.</p>}
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeletingId(null)}>Cancel</Button>
          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={() => deletingId && deleteMutation.mutate(deletingId)}
          >
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}

export default function MaterialsPage() {
  return (
    <RequirePermission permission="materials.view">
      <MaterialsContent />
    </RequirePermission>
  );
}
