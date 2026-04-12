"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { logisticsApi, ShipmentContainer, ContainerStatus, ContainerType } from "@/lib/logistics";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const statusBadge = (s: ContainerStatus) =>
  s === "RELEASED" ? "green" : s === "CUSTOMS_HOLD" ? "red" : s === "IN_TRANSIT" ? "blue" : s === "AT_PORT" ? "yellow" : "gray";

const CONTAINER_STATUSES: ContainerStatus[] = ["EMPTY", "LOADING", "LOADED", "IN_TRANSIT", "AT_PORT", "CUSTOMS_HOLD", "RELEASED", "RETURNED"];

export default function ContainersPage() {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [editing, setEditing] = useState<ShipmentContainer | null>(null);
  const [filterStatus, setFilterStatus] = useState<ContainerStatus | "ALL">("ALL");

  const { data: containers = [], isLoading } = useQuery({
    queryKey: ["logistics-containers"],
    queryFn: () => logisticsApi.listContainers(),
  });

  const { data: shipments = [] } = useQuery({
    queryKey: ["logistics-shipments"],
    queryFn: () => logisticsApi.listShipments(),
  });

  const createContainer = useMutation({
    mutationFn: (d: object) => logisticsApi.createContainer(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["logistics-containers"] }); setShowNew(false); },
  });

  const updateContainer = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => logisticsApi.updateContainer(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["logistics-containers"] }); setEditing(null); },
  });

  const filtered = filterStatus === "ALL" ? containers : containers.filter((c) => c.status === filterStatus);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Container Tracking</h1>
          <p className="text-sm text-gray-500 mt-1">Track containers by number, seal, contents and status</p>
        </div>
        <Button onClick={() => setShowNew(true)}>Add Container</Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["ALL", ...CONTAINER_STATUSES] as const).map((s) => {
          const count = s === "ALL" ? containers.length : containers.filter((c) => c.status === s).length;
          return (
            <button key={s} onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${filterStatus === s ? "bg-indigo-600 text-white" : "bg-white border text-gray-600 hover:border-indigo-300"}`}>
              {s} ({count})
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading ? <p className="px-5 py-8 text-center text-gray-400">Loading…</p> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Container No</th>
                <th className="px-5 py-2 text-left">Seal No</th>
                <th className="px-5 py-2 text-left">Type</th>
                <th className="px-5 py-2 text-left">Shipment</th>
                <th className="px-5 py-2 text-right">Weight (kg)</th>
                <th className="px-5 py-2 text-right">CBM</th>
                <th className="px-5 py-2 text-left">Contents</th>
                <th className="px-5 py-2 text-left">Customs Release</th>
                <th className="px-5 py-2 text-right">Free Days</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-sm font-semibold text-indigo-700">{c.container_no}</td>
                  <td className="px-5 py-3 font-mono text-xs">{c.seal_no || "—"}</td>
                  <td className="px-5 py-3"><Badge label={c.container_type} variant="gray" /></td>
                  <td className="px-5 py-3 font-mono text-xs text-blue-700">{c.shipment_no || "—"}</td>
                  <td className="px-5 py-3 text-right">{c.gross_weight_kg != null ? Number(c.gross_weight_kg).toLocaleString() : "—"}</td>
                  <td className="px-5 py-3 text-right">{c.cbm != null ? Number(c.cbm).toFixed(2) : "—"}</td>
                  <td className="px-5 py-3 text-gray-600 max-w-xs truncate">{c.contents_summary || "—"}</td>
                  <td className="px-5 py-3 font-mono text-xs">{c.customs_release_no || "—"}</td>
                  <td className="px-5 py-3 text-right">{c.demurrage_free_days ?? "—"}</td>
                  <td className="px-5 py-3"><Badge label={c.status} variant={statusBadge(c.status)} /></td>
                  <td className="px-5 py-3">
                    <button className="text-xs text-indigo-600 hover:underline" onClick={() => setEditing(c)}>Edit</button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && <tr><td colSpan={11} className="px-5 py-8 text-center text-gray-400">No containers</td></tr>}
            </tbody>
          </table>
        )}
      </div>

      {showNew && (
        <ContainerModal title="Add Container" shipments={shipments}
          onClose={() => setShowNew(false)} onSubmit={(d) => createContainer.mutate(d)} loading={createContainer.isPending} />
      )}
      {editing && (
        <ContainerModal title="Edit Container" initial={editing} shipments={shipments}
          onClose={() => setEditing(null)} onSubmit={(d) => updateContainer.mutate({ id: editing.id, data: d })} loading={updateContainer.isPending} />
      )}
    </div>
  );
}

function ContainerModal({ title, initial, shipments, onClose, onSubmit, loading }: {
  title: string; initial?: ShipmentContainer; shipments: { id: string; shipment_no: string }[];
  onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const [form, setForm] = useState({
    shipment_id: initial?.shipment_id ?? "",
    container_no: initial?.container_no ?? "",
    seal_no: initial?.seal_no ?? "",
    container_type: initial?.container_type ?? "40FT_DRY",
    gross_weight_kg: initial?.gross_weight_kg?.toString() ?? "",
    cbm: initial?.cbm?.toString() ?? "",
    contents_summary: initial?.contents_summary ?? "",
    status: initial?.status ?? "LOADING",
    customs_release_no: initial?.customs_release_no ?? "",
    demurrage_free_days: initial?.demurrage_free_days?.toString() ?? "7",
    notes: initial?.notes ?? "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 space-y-4">
        <h2 className="font-semibold text-lg">{title}</h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Shipment</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.shipment_id} onChange={(e) => set("shipment_id", e.target.value)} disabled={!!initial}>
              <option value="">Select shipment…</option>
              {shipments.map((s) => <option key={s.id} value={s.id}>{s.shipment_no}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Container No</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono disabled:bg-gray-50" value={form.container_no} onChange={(e) => set("container_no", e.target.value)} disabled={!!initial} placeholder="e.g. MSCU1234567" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Seal No</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.seal_no} onChange={(e) => set("seal_no", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.container_type} onChange={(e) => set("container_type", e.target.value)}>
              <option value="20FT_DRY">20ft Dry</option>
              <option value="40FT_DRY">40ft Dry</option>
              <option value="40FT_HC">40ft High Cube</option>
              <option value="20FT_REEFER">20ft Reefer</option>
              <option value="LCL">LCL</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.status} onChange={(e) => set("status", e.target.value)}>
              {CONTAINER_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Gross Weight (kg)</label>
            <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.gross_weight_kg} onChange={(e) => set("gross_weight_kg", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">CBM</label>
            <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.cbm} onChange={(e) => set("cbm", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Customs Release No</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.customs_release_no} onChange={(e) => set("customs_release_no", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Demurrage Free Days</label>
            <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.demurrage_free_days} onChange={(e) => set("demurrage_free_days", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Contents Summary</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.contents_summary} onChange={(e) => set("contents_summary", e.target.value)} placeholder="e.g. 500 cartons detergent, 200 bags flour…" />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            ...form,
            gross_weight_kg: form.gross_weight_kg ? parseFloat(form.gross_weight_kg) : undefined,
            cbm: form.cbm ? parseFloat(form.cbm) : undefined,
            demurrage_free_days: form.demurrage_free_days ? parseInt(form.demurrage_free_days) : undefined,
          })}>Save</Button>
        </div>
      </div>
    </div>
  );
}
