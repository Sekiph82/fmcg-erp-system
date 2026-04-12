"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { logisticsApi, IntlShipment, IntlShipmentStatus } from "@/lib/logistics";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const STATUS_FLOW: IntlShipmentStatus[] = [
  "DRAFT", "BOOKING_CONFIRMED", "CARGO_LOADED", "IN_TRANSIT",
  "ARRIVED_PORT", "CUSTOMS_HOLD", "CUSTOMS_CLEARED", "OUT_FOR_DELIVERY", "DELIVERED",
];

const statusBadge = (s: IntlShipmentStatus) => {
  if (s === "DELIVERED" || s === "CUSTOMS_CLEARED") return "green";
  if (s === "CUSTOMS_HOLD") return "red";
  if (["IN_TRANSIT", "CARGO_LOADED", "BOOKING_CONFIRMED"].includes(s)) return "blue";
  if (["ARRIVED_PORT", "OUT_FOR_DELIVERY"].includes(s)) return "yellow";
  return "gray";
};

export default function ShipmentsPage() {
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [editing, setEditing] = useState<IntlShipment | null>(null);
  const [filterStatus, setFilterStatus] = useState<IntlShipmentStatus | "ALL">("ALL");

  const { data: shipments = [], isLoading } = useQuery({
    queryKey: ["logistics-shipments"],
    queryFn: () => logisticsApi.listShipments(),
  });

  const createShipment = useMutation({
    mutationFn: (d: object) => logisticsApi.createShipment(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["logistics-shipments"] }); qc.invalidateQueries({ queryKey: ["logistics-dashboard"] }); setShowNew(false); },
  });

  const updateShipment = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => logisticsApi.updateShipment(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["logistics-shipments"] }); qc.invalidateQueries({ queryKey: ["logistics-dashboard"] }); setEditing(null); },
  });

  const filtered = filterStatus === "ALL" ? shipments : shipments.filter((s) => s.status === filterStatus);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Shipment Planning</h1>
          <p className="text-sm text-gray-500 mt-1">Turkey → Kenya international shipments</p>
        </div>
        <Button onClick={() => setShowNew(true)}>New Shipment</Button>
      </div>

      {/* Status filter */}
      <div className="flex flex-wrap gap-2">
        {(["ALL", ...STATUS_FLOW] as const).map((s) => {
          const count = s === "ALL" ? shipments.length : shipments.filter((x) => x.status === s).length;
          return (
            <button key={s} onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${filterStatus === s ? "bg-indigo-600 text-white" : "bg-white border text-gray-600 hover:border-indigo-300"}`}>
              {s.replace("_", " ")} ({count})
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        {isLoading ? <p className="px-5 py-8 text-center text-gray-400">Loading…</p> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-5 py-2 text-left">Shipment No</th>
                <th className="px-5 py-2 text-left">Mode</th>
                <th className="px-5 py-2 text-left">Origin</th>
                <th className="px-5 py-2 text-left">Carrier / Vessel</th>
                <th className="px-5 py-2 text-left">B/L</th>
                <th className="px-5 py-2 text-left">Departure</th>
                <th className="px-5 py-2 text-left">ETA</th>
                <th className="px-5 py-2 text-left">Incoterm</th>
                <th className="px-5 py-2 text-center">Ctrs</th>
                <th className="px-5 py-2 text-center">POs</th>
                <th className="px-5 py-2 text-left">Status</th>
                <th className="px-5 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs font-semibold text-indigo-700">{s.shipment_no}</td>
                  <td className="px-5 py-3"><Badge label={s.mode} variant={s.mode === "SEA" ? "blue" : s.mode === "AIR" ? "yellow" : "gray"} /></td>
                  <td className="px-5 py-3 text-gray-600">
                    <p>{s.origin_city || s.origin_country}</p>
                    <p className="text-xs text-gray-400">{s.origin_port}</p>
                  </td>
                  <td className="px-5 py-3">
                    <p className="text-gray-700">{s.carrier || "—"}</p>
                    <p className="text-xs text-gray-400">{s.vessel_name}</p>
                  </td>
                  <td className="px-5 py-3 font-mono text-xs">{s.bl_number || "—"}</td>
                  <td className="px-5 py-3 text-gray-500">{s.planned_departure || "—"}</td>
                  <td className="px-5 py-3">
                    {s.eta ? (
                      <span className={s.days_to_eta != null && s.days_to_eta < 0 ? "text-red-600 font-semibold" : s.days_to_eta != null && s.days_to_eta <= 7 ? "text-orange-500" : "text-gray-700"}>
                        {s.eta}
                        {s.days_to_eta != null && !s.ata && <span className="text-xs ml-1 text-gray-400">({s.days_to_eta}d)</span>}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-5 py-3 text-gray-500">{s.incoterm || "—"}</td>
                  <td className="px-5 py-3 text-center">{s.container_count ?? 0}</td>
                  <td className="px-5 py-3 text-center">{s.po_count ?? 0}</td>
                  <td className="px-5 py-3"><Badge label={s.status.replace(/_/g, " ")} variant={statusBadge(s.status)} /></td>
                  <td className="px-5 py-3">
                    <button className="text-xs text-indigo-600 hover:underline" onClick={() => setEditing(s)}>Edit</button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && <tr><td colSpan={12} className="px-5 py-8 text-center text-gray-400">No shipments</td></tr>}
            </tbody>
          </table>
        )}
      </div>

      {showNew && (
        <ShipmentModal title="New Shipment" onClose={() => setShowNew(false)}
          onSubmit={(d) => createShipment.mutate(d)} loading={createShipment.isPending} />
      )}
      {editing && (
        <ShipmentModal title="Edit Shipment" initial={editing} onClose={() => setEditing(null)}
          onSubmit={(d) => updateShipment.mutate({ id: editing.id, data: d })} loading={updateShipment.isPending} />
      )}
    </div>
  );
}

function ShipmentModal({ title, initial, onClose, onSubmit, loading }: {
  title: string; initial?: IntlShipment; onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const [form, setForm] = useState({
    shipment_no: initial?.shipment_no ?? "",
    mode: initial?.mode ?? "SEA",
    origin_country: initial?.origin_country ?? "Turkey",
    origin_city: initial?.origin_city ?? "Istanbul",
    origin_port: initial?.origin_port ?? "Port of Istanbul",
    destination_city: initial?.destination_city ?? "Mombasa",
    destination_port: initial?.destination_port ?? "Port of Mombasa",
    final_destination: initial?.final_destination ?? "",
    carrier: initial?.carrier ?? "",
    vessel_name: initial?.vessel_name ?? "",
    voyage_no: initial?.voyage_no ?? "",
    bl_number: initial?.bl_number ?? "",
    planned_departure: initial?.planned_departure ?? "",
    eta: initial?.eta ?? "",
    incoterm: initial?.incoterm ?? "CIF",
    currency: initial?.currency ?? "USD",
    freight_cost: initial?.freight_cost?.toString() ?? "",
    insurance_cost: initial?.insurance_cost?.toString() ?? "",
    total_cbm: initial?.total_cbm?.toString() ?? "",
    total_weight_kg: initial?.total_weight_kg?.toString() ?? "",
    forwarder: initial?.forwarder ?? "",
    status: initial?.status ?? "DRAFT",
    notes: initial?.notes ?? "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 overflow-y-auto py-8">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-6 space-y-4 my-auto">
        <h2 className="font-semibold text-lg">{title}</h2>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Shipment No</label>
            <input className="w-full border rounded px-3 py-2 text-sm disabled:bg-gray-50" value={form.shipment_no} onChange={(e) => set("shipment_no", e.target.value)} disabled={!!initial} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Mode</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.mode} onChange={(e) => set("mode", e.target.value)}>
              <option value="SEA">Sea</option>
              <option value="AIR">Air</option>
              <option value="ROAD">Road</option>
              <option value="RAIL">Rail</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.status} onChange={(e) => set("status", e.target.value)}>
              {STATUS_FLOW.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Origin Country</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.origin_country} onChange={(e) => set("origin_country", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Origin City</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.origin_city} onChange={(e) => set("origin_city", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Origin Port</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.origin_port} onChange={(e) => set("origin_port", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Carrier</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.carrier} onChange={(e) => set("carrier", e.target.value)} placeholder="e.g. MSC, Maersk" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Vessel Name</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.vessel_name} onChange={(e) => set("vessel_name", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Voyage No</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.voyage_no} onChange={(e) => set("voyage_no", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">B/L Number</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.bl_number} onChange={(e) => set("bl_number", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Planned Departure</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.planned_departure} onChange={(e) => set("planned_departure", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">ETA Mombasa</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={form.eta} onChange={(e) => set("eta", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Incoterm</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.incoterm} onChange={(e) => set("incoterm", e.target.value)}>
              {["EXW","FCA","FOB","CFR","CIF","CPT","CIP","DAP","DDP"].map((i) => <option key={i} value={i}>{i}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Currency</label>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.currency} onChange={(e) => set("currency", e.target.value)}>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="TRY">TRY</option>
              <option value="KES">KES</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Freight Cost</label>
            <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.freight_cost} onChange={(e) => set("freight_cost", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Insurance</label>
            <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.insurance_cost} onChange={(e) => set("insurance_cost", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Total CBM</label>
            <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.total_cbm} onChange={(e) => set("total_cbm", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Weight (kg)</label>
            <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.total_weight_kg} onChange={(e) => set("total_weight_kg", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Forwarder</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.forwarder} onChange={(e) => set("forwarder", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Final Destination</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.final_destination} onChange={(e) => set("final_destination", e.target.value)} placeholder="Warehouse / address" />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
          <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            ...form,
            freight_cost: form.freight_cost ? parseFloat(form.freight_cost) : undefined,
            insurance_cost: form.insurance_cost ? parseFloat(form.insurance_cost) : undefined,
            total_cbm: form.total_cbm ? parseFloat(form.total_cbm) : undefined,
            total_weight_kg: form.total_weight_kg ? parseFloat(form.total_weight_kg) : undefined,
            planned_departure: form.planned_departure || undefined,
            eta: form.eta || undefined,
          })}>Save</Button>
        </div>
      </div>
    </div>
  );
}
