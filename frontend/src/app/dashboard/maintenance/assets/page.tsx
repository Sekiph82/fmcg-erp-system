"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { maintenanceApi, Asset, AssetStatus } from "@/lib/maintenance";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { RequirePermission } from "@/components/PermissionGuard";

const statusBadge = (s: AssetStatus) =>
  s === "ACTIVE" ? "green" : s === "UNDER_MAINTENANCE" ? "yellow" : s === "DECOMMISSIONED" ? "gray" : "blue";

export default function AssetsPage() {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [editAsset, setEditAsset] = useState<Asset | null>(null);
  const [filterStatus, setFilterStatus] = useState<AssetStatus | "ALL">("ALL");

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ["maint-assets"],
    queryFn: () => maintenanceApi.listAssets(),
  });

  const createAsset = useMutation({
    mutationFn: (data: object) => maintenanceApi.createAsset(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-assets"] }); setShowNew(false); },
  });

  const updateAsset = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => maintenanceApi.updateAsset(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["maint-assets"] }); setEditAsset(null); },
  });

  const filtered = filterStatus === "ALL" ? assets : assets.filter((a) => a.status === filterStatus);

  const lines = Array.from(new Set(assets.map((a) => a.line).filter(Boolean)));

  return (
    <RequirePermission permission="maintenance.view">
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Asset Register</h1>
          <p className="text-sm text-gray-500 mt-1">Machines, equipment and production lines</p>
        </div>
        <Button onClick={() => setShowNew(true)}>Add Asset</Button>
      </div>

      {/* Status filter */}
      <div className="flex gap-2">
        {(["ALL", "ACTIVE", "IDLE", "UNDER_MAINTENANCE", "DECOMMISSIONED"] as const).map((s) => {
          const count = s === "ALL" ? assets.length : assets.filter((a) => a.status === s).length;
          return (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                filterStatus === s ? "bg-indigo-600 text-white" : "bg-white border text-gray-600 hover:border-indigo-300"
              }`}
            >
              {s} ({count})
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading ? (
          <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Asset No</th>
                <th className="px-5 py-2 text-left">Name</th>
                <th className="px-5 py-2 text-left">Type</th>
                <th className="px-5 py-2 text-left">Line</th>
                <th className="px-5 py-2 text-left">Serial No</th>
                <th className="px-5 py-2 text-left">Install Date</th>
                <th className="px-5 py-2 text-left">Location</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-700">{a.asset_no}</td>
                  <td className="px-5 py-3 font-medium text-gray-900">{a.name}</td>
                  <td className="px-5 py-3 text-gray-600">{a.asset_type || "—"}</td>
                  <td className="px-5 py-3">{a.line || "—"}</td>
                  <td className="px-5 py-3 font-mono text-xs text-gray-500">{a.serial_no || "—"}</td>
                  <td className="px-5 py-3 text-gray-500">{a.install_date || "—"}</td>
                  <td className="px-5 py-3 text-gray-500">{a.location || "—"}</td>
                  <td className="px-5 py-3"><Badge label={a.status} variant={statusBadge(a.status)} /></td>
                  <td className="px-5 py-3">
                    <button className="text-xs text-indigo-600 hover:underline" onClick={() => setEditAsset(a)}>Edit</button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={9} className="px-5 py-8 text-center text-gray-400">No assets</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {showNew && (
        <AssetModal
          title="Add Asset"
          onClose={() => setShowNew(false)}
          onSubmit={(data) => createAsset.mutate(data)}
          loading={createAsset.isPending}
        />
      )}
      {editAsset && (
        <AssetModal
          title="Edit Asset"
          initial={editAsset}
          onClose={() => setEditAsset(null)}
          onSubmit={(data) => updateAsset.mutate({ id: editAsset.id, data })}
          loading={updateAsset.isPending}
        />
      )}
    </div>
    </RequirePermission>
  );
}

function AssetModal({ title, initial, onClose, onSubmit, loading }: {
  title: string;
  initial?: Asset;
  onClose: () => void;
  onSubmit: (d: object) => void;
  loading: boolean;
}) {
  const [form, setForm] = useState({
    asset_no: initial?.asset_no ?? "",
    name: initial?.name ?? "",
    asset_type: initial?.asset_type ?? "",
    line: initial?.line ?? "",
    serial_no: initial?.serial_no ?? "",
    manufacturer: initial?.manufacturer ?? "",
    model: initial?.model ?? "",
    install_date: initial?.install_date ?? "",
    warranty_expiry: initial?.warranty_expiry ?? "",
    location: initial?.location ?? "",
    status: initial?.status ?? "ACTIVE",
    notes: initial?.notes ?? "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4 my-8">
        <h2 className="font-semibold text-lg">{title}</h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            { key: "asset_no", label: "Asset No", disabled: !!initial },
            { key: "name", label: "Name" },
            { key: "asset_type", label: "Type" },
            { key: "line", label: "Production Line" },
            { key: "serial_no", label: "Serial No" },
            { key: "manufacturer", label: "Manufacturer" },
            { key: "model", label: "Model" },
            { key: "location", label: "Location" },
          ].map(({ key, label, disabled }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50"
                value={(form as Record<string, string>)[key]}
                onChange={(e) => set(key, e.target.value)}
                disabled={disabled}
              />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Install Date</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.install_date} onChange={(e) => set("install_date", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Warranty Expiry</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.warranty_expiry} onChange={(e) => set("warranty_expiry", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.status} onChange={(e) => set("status", e.target.value)}>
              <option value="ACTIVE">Active</option>
              <option value="IDLE">Idle</option>
              <option value="UNDER_MAINTENANCE">Under Maintenance</option>
              <option value="DECOMMISSIONED">Decommissioned</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit(form)}>Save</Button>
        </div>
      </div>
    </div>
  );
}
