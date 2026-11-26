"use client";

import { EntityPicker } from "@/components/EntityPicker";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { mfApi, MaterialPickList, Reservation, ReservationStatus } from "@/lib/materialFlow";
import { wmsApi } from "@/lib/wms";
import { tx } from "@/lib/i18n/core";

const STATUS_COLORS: Record<ReservationStatus, string> = {
  ACTIVE: "bg-green-100 text-green-700",
  PARTIALLY_ISSUED: "bg-blue-100 text-blue-700",
  FULLY_ISSUED: "bg-gray-100 text-gray-700",
  EXPIRED: "bg-red-100 text-red-700",
  CANCELLED: "bg-red-50 text-red-500",
};

export default function ReservationsPage() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Reservation | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ production_order_id: "", notes: "" });
  const [lines, setLines] = useState([{ material_id: "", warehouse_id: "", staging_location_id: "", quantity_required: "", uom: "KG" }]);
  const [pickList, setPickList] = useState<MaterialPickList | null>(null);
  const [pickListError, setPickListError] = useState("");
  const [generatingPickList, setGeneratingPickList] = useState(false);

  const { data } = useQuery<Reservation[]>({
    queryKey: ["mf-reservations"],
    queryFn: () => mfApi.listReservations(),
  });
  const { data: locations = [] } = useQuery({
    queryKey: ["mf-staging-locations"],
    queryFn: () => wmsApi.listLocations(),
    select: (rows) => rows.filter((location) =>
      location.zone_type === "STAGING" && location.is_active && !location.is_blocked
    ),
  });

  const cancel = useMutation({
    mutationFn: (id: string) => mfApi.cancelReservation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mf-reservations"] }),
  });

  const create = useMutation({
    mutationFn: () =>
      mfApi.createReservation({
        ...form,
        lines: lines.map((l, i) => ({
          line_no: i + 1,
          item_type: "material",
          material_id: l.material_id,
          warehouse_id: l.warehouse_id,
          staging_location_id: l.staging_location_id || undefined,
          quantity_required: parseFloat(l.quantity_required),
          uom: l.uom,
        })),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mf-reservations"] });
      setShowCreate(false);
      setForm({ production_order_id: "", notes: "" });
      setLines([{ material_id: "", warehouse_id: "", staging_location_id: "", quantity_required: "", uom: "KG" }]);
    },
  });

  async function generatePickList(reservationId: string) {
    setGeneratingPickList(true);
    setPickListError("");
    try {
      setPickList(await mfApi.generatePickList(reservationId));
    } catch {
      setPickList(null);
      setPickListError(tx("No pick list is available. Check access, reservation status, and production-order status."));
    } finally {
      setGeneratingPickList(false);
    }
  }

  const resList = data || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a href="/dashboard/material-flow" className="text-sm text-indigo-600 hover:underline">{tx("← Dashboard")}</a>
          <h1 className="text-xl font-bold text-gray-900">{tx("Material Reservations")}</h1>
        </div>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700">
          {tx("+ New Reservation")}
        </button>
      </div>

      <div className="bg-white rounded-lg border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              {[tx("Reservation No"), tx("Production Order"), tx("Status"), tx("Lines"), tx("Expiry"), tx("Actions")].map((h) => (
                <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {resList.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs">{r.reservation_no}</td>
                <td className="px-4 py-2.5 font-mono text-xs">{r.production_order_id.slice(0, 8)}…</td>
                <td className="px-4 py-2.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[r.status]}`}>{r.status.replace("_", " ")}</span>
                </td>
                <td className="px-4 py-2.5 text-xs">{r.lines.length}</td>
                <td className="px-4 py-2.5 text-xs">{r.expiry_datetime ? new Date(r.expiry_datetime).toLocaleDateString() : "—"}</td>
                <td className="px-4 py-2.5 flex gap-2">
                  <button onClick={() => { setSelected(r); setPickList(null); setPickListError(""); }} className="text-xs text-indigo-600 hover:underline">{tx("View")}</button>
                  {r.status === "ACTIVE" && (
                    <button onClick={() => cancel.mutate(r.id)} className="text-xs text-red-500 hover:underline">{tx("Cancel")}</button>
                  )}
                </td>
              </tr>
            ))}
            {resList.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">{tx("No reservations found.")}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Detail Panel */}
      {selected && (
        <div className="bg-white rounded-lg border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">{tx("Reservation:")} {selected.reservation_no}</h2>
            <div className="flex items-center gap-3">
              <button
                onClick={() => generatePickList(selected.id)}
                disabled={generatingPickList}
                className="text-xs text-indigo-600 hover:underline disabled:opacity-50"
              >
                {generatingPickList ? tx("Generating…") : tx("Generate pick list")}
              </button>
              <button onClick={() => { setSelected(null); setPickList(null); }} className="text-xs text-gray-500 hover:text-gray-700">{tx("✕ Close")}</button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["#", tx("Material ID"), tx("Required"), tx("Reserved"), tx("Issued"), "UOM", tx("Quality")].map((h) => (
                    <th key={h} className="px-3 py-1.5 text-left text-xs font-medium text-gray-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {selected.lines.map((l) => (
                  <tr key={l.id}>
                    <td className="px-3 py-1.5 text-xs">{l.line_no}</td>
                    <td className="px-3 py-1.5 font-mono text-xs">{l.material_id?.slice(0, 8) || l.material_name || "—"}</td>
                    <td className="px-3 py-1.5 text-xs">{Number(l.quantity_required).toLocaleString()}</td>
                    <td className="px-3 py-1.5 text-xs">{Number(l.quantity_reserved).toLocaleString()}</td>
                    <td className="px-3 py-1.5 text-xs">{Number(l.quantity_issued).toLocaleString()}</td>
                    <td className="px-3 py-1.5 text-xs">{l.uom}</td>
                    <td className="px-3 py-1.5 text-xs">RELEASED</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {pickListError && <p role="alert" className="mt-3 text-sm text-red-600">{pickListError}</p>}
          {pickList && (
            <div className="mt-5 rounded-lg border border-indigo-100 bg-indigo-50/40 p-4">
              <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-gray-900">{tx("Pick list ·")} {pickList.production_order_no}</h3>
                  <p className="text-xs text-gray-600">{tx("Source:")} {pickList.warehouse_name} {tx("· Generated")} {new Date(pickList.generated_at).toLocaleString()}</p>
                </div>
                <span className="text-xs text-gray-500">{tx("Read-only from the active reservation")}</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-xs text-gray-600">
                      <th className="py-2 pr-3">{tx("Material")}</th>
                      <th className="py-2 pr-3">{tx("Lot")}</th>
                      <th className="py-2 pr-3">{tx("Expiry")}</th>
                      <th className="py-2 pr-3">{tx("Source location")}</th>
                      <th className="py-2 pr-3">{tx("Staging location")}</th>
                      <th className="py-2 pr-3 text-right">{tx("Pick quantity")}</th>
                      <th className="py-2">UOM</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {pickList.lines.map((line) => (
                      <tr key={`${line.material_id}:${line.lot_id ?? "bulk"}:${line.line_no}`}>
                        <td className="py-2 pr-3">
                          <div className="font-medium text-gray-800">{line.material_name}</div>
                          <div className="font-mono text-xs text-gray-500">{line.material_code}</div>
                        </td>
                        <td className="py-2 pr-3 font-mono text-xs">{line.lot_number || tx("Untracked lot")}</td>
                        <td className="py-2 pr-3 text-xs">{line.expiry_date ? new Date(line.expiry_date).toLocaleDateString() : "—"}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{line.source_location_code || tx("Unassigned")}</td>
                        <td className="py-2 pr-3 font-mono text-xs">{line.staging_location_code || tx("Unassigned")}</td>
                        <td className="py-2 pr-3 text-right font-semibold">{Number(line.quantity_to_pick).toLocaleString()}</td>
                        <td className="py-2 text-xs">{line.uom}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-[600px] max-h-[90vh] overflow-y-auto space-y-4">
            <h2 className="font-bold text-gray-900">{tx("New Material Reservation")}</h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{tx("Production order")}</label>
                <EntityPicker kind="production_order" label={tx("Production order")} value={form.production_order_id} onChange={(id) => setForm((f) => ({ ...f, production_order_id: id }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{tx("Notes")}</label>
                <input value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} className="w-full border rounded px-3 py-2 text-sm" placeholder={tx("Optional")} />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-700">{tx("Lines")}</h3>
                <button onClick={() => setLines((p) => [...p, { material_id: "", warehouse_id: "", staging_location_id: "", quantity_required: "", uom: "KG" }])} className="text-xs text-indigo-600 hover:underline">{tx("+ Add")}</button>
              </div>
              {lines.map((ln, i) => (
                <div key={i} className="grid grid-cols-5 gap-2 mb-2">
                  <EntityPicker kind="material" label={tx("Material")} value={ln.material_id} onChange={(id) => setLines((p) => p.map((l, idx) => idx === i ? { ...l, material_id: id } : l))} />
                  <EntityPicker kind="warehouse" label={tx("Warehouse")} value={ln.warehouse_id} onChange={(id) => setLines((p) => p.map((l, idx) => idx === i ? { ...l, warehouse_id: id, staging_location_id: "" } : l))} />
                  <select value={ln.staging_location_id} onChange={(e) => setLines((p) => p.map((l, idx) => idx === i ? { ...l, staging_location_id: e.target.value } : l))} className="border rounded px-2 py-1.5 text-xs">
                    <option value="">{tx("Automatic when unique")}</option>
                    {locations.filter((location) => location.warehouse_id === ln.warehouse_id).map((location) => (
                      <option key={location.id} value={location.id}>{location.code} · {location.name}</option>
                    ))}
                  </select>
                  <input type="number" value={ln.quantity_required} onChange={(e) => setLines((p) => p.map((l, idx) => idx === i ? { ...l, quantity_required: e.target.value } : l))} className="border rounded px-2 py-1.5 text-xs" placeholder={tx("Qty")} />
                  <select value={ln.uom} onChange={(e) => setLines((p) => p.map((l, idx) => idx === i ? { ...l, uom: e.target.value } : l))} className="border rounded px-2 py-1.5 text-xs">
                    {["KG", "L", "PCS", "CTN"].map((u) => <option key={u}>{u}</option>)}
                  </select>
                </div>
              ))}
              <p className="text-xs text-gray-500">{tx("Source location comes from the allocated stock row. If a warehouse has multiple active staging locations, select one; no location is guessed.")}</p>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50">{tx("Cancel")}</button>
              <button onClick={() => create.mutate()} disabled={!form.production_order_id} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {create.isPending ? tx("Saving…") : tx("Create Reservation")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
