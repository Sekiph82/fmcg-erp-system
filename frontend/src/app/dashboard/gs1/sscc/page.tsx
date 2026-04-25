"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gs1Api, type SSCCPallet, statusColor } from "@/lib/gs1";

export default function SSCCPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [showAddLot, setShowAddLot] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [form, setForm] = useState({ pallet_id: "", warehouse_location: "", notes: "" });
  const [addLotForm, setAddLotForm] = useState({ lot_barcode_id: "", quantity: "" });

  const { data: pallets } = useQuery({
    queryKey: ["gs1-sscc", statusFilter],
    queryFn: () => gs1Api.listSSCC({ status: statusFilter || undefined, limit: 100 }),
  });

  const generate = useMutation({
    mutationFn: gs1Api.generateSSCC,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["gs1-sscc"] }); setShowForm(false); },
  });

  const addLot = useMutation({
    mutationFn: ({ ssccId, lot_barcode_id, quantity }: { ssccId: string; lot_barcode_id: string; quantity?: number }) =>
      gs1Api.addLotToSSCC(ssccId, lot_barcode_id, quantity),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["gs1-sscc"] }); setShowAddLot(null); setAddLotForm({ lot_barcode_id: "", quantity: "" }); },
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => gs1Api.updateSSCCStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["gs1-sscc"] }),
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">SSCC Pallet Tracking</h1>
          <p className="text-sm text-gray-500">Serial Shipping Container Codes — GS1 pallet identification</p>
        </div>
        <button onClick={() => setShowForm(true)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
          + Generate SSCC
        </button>
      </div>

      {/* SSCC structure explainer */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
        <p className="font-medium mb-1">SSCC Structure (18 digits)</p>
        <p className="font-mono">Extension(1) + Company Prefix(7) + Serial Reference(9) + Check Digit(1) = 18 digits total</p>
        <p className="mt-1">Encoded as GS1-128 with AI (00). Each SSCC is globally unique.</p>
      </div>

      {/* Generate Form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-gray-700">Generate New SSCC Pallet</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500">Pallet ID / Reference</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.pallet_id} onChange={(e) => setForm((p) => ({ ...p, pallet_id: e.target.value }))} placeholder="PLT-2024-001" />
            </div>
            <div>
              <label className="text-xs text-gray-500">Warehouse Location</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.warehouse_location} onChange={(e) => setForm((p) => ({ ...p, warehouse_location: e.target.value }))} placeholder="Zone A / Bay 3" />
            </div>
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => generate.mutate(form)} disabled={generate.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">
              {generate.isPending ? "Generating…" : "Generate SSCC"}
            </button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
          </div>
          {generate.isError && <p className="text-red-600 text-xs">{(generate.error as Error).message}</p>}
        </div>
      )}

      {/* Add Lot Modal */}
      {showAddLot && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-4 w-96 space-y-3">
            <h3 className="text-sm font-medium text-gray-900">Add Lot to SSCC Pallet</h3>
            <div>
              <label className="text-xs text-gray-500">Lot Barcode Record ID (UUID)</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={addLotForm.lot_barcode_id} onChange={(e) => setAddLotForm((p) => ({ ...p, lot_barcode_id: e.target.value }))} placeholder="barcode-record-uuid..." />
            </div>
            <div>
              <label className="text-xs text-gray-500">Quantity</label>
              <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={addLotForm.quantity} onChange={(e) => setAddLotForm((p) => ({ ...p, quantity: e.target.value }))} />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => addLot.mutate({ ssccId: showAddLot, lot_barcode_id: addLotForm.lot_barcode_id, quantity: addLotForm.quantity ? Number(addLotForm.quantity) : undefined })}
                disabled={addLot.isPending || !addLotForm.lot_barcode_id}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50"
              >
                {addLot.isPending ? "Adding…" : "Add Lot"}
              </button>
              <button onClick={() => setShowAddLot(null)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2">
        {["", "ACTIVE", "SHIPPED", "RECEIVED", "CANCELLED"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 text-xs rounded border ${statusFilter === s ? "bg-gray-900 text-white border-gray-900" : "bg-white hover:bg-gray-50"}`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Pallets Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["SSCC Code", "Pallet ID", "Status", "Lots", "Location", "Shipment Ref", "Label", "Created", "Actions"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {!pallets?.length && <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">No SSCC pallets found</td></tr>}
              {pallets?.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs font-medium">{p.sscc_code}</td>
                  <td className="px-3 py-2">{p.pallet_id || "—"}</td>
                  <td className="px-3 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${statusColor[p.status] ?? ""}`}>{p.status}</span>
                  </td>
                  <td className="px-3 py-2">{p.lot_count}</td>
                  <td className="px-3 py-2 text-gray-500">{p.warehouse_location || "—"}</td>
                  <td className="px-3 py-2 text-gray-500 text-xs">{p.shipment_reference || "—"}</td>
                  <td className="px-3 py-2">{p.label_printed ? <span className="text-green-600 text-xs">✓ Printed</span> : <span className="text-gray-400 text-xs">—</span>}</td>
                  <td className="px-3 py-2 text-gray-400 text-xs">{new Date(p.created_at).toLocaleDateString()}</td>
                  <td className="px-3 py-2">
                    <div className="flex gap-1">
                      <button onClick={() => setShowAddLot(p.id)} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded hover:bg-blue-100">+Lot</button>
                      {p.status === "ACTIVE" && (
                        <button onClick={() => updateStatus.mutate({ id: p.id, status: "SHIPPED" })} className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded hover:bg-purple-100">Ship</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
