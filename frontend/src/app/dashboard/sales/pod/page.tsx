"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { deliveryApi, ProofOfDelivery } from "@/lib/delivery";
import { salesApi } from "@/lib/sales";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

export default function PODPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    shipment_id: "",
    received_by: "",
    signature_text: "",
    notes: "",
    delivered_at: new Date().toISOString().slice(0, 16),
  });

  const { data: pods = [], isLoading } = useQuery({
    queryKey: ["pods"],
    queryFn: () => deliveryApi.listPods(),
  });

  const { data: shipments = [] } = useQuery({
    queryKey: ["shipments-dispatched"],
    queryFn: () => salesApi.listShipments({ status: "DISPATCHED" }),
  });

  const create = useMutation({
    mutationFn: () => deliveryApi.createPod({
      ...form,
      delivered_at: form.delivered_at ? new Date(form.delivered_at).toISOString() : undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pods"] });
      qc.invalidateQueries({ queryKey: ["shipments-dispatched"] });
      setOpen(false);
      setForm({ shipment_id: "", received_by: "", signature_text: "", notes: "", delivered_at: new Date().toISOString().slice(0, 16) });
    },
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Proof of Delivery</h1>
          <p className="text-sm text-gray-500 mt-1">Capture delivery confirmations from the field</p>
        </div>
        <Button onClick={() => setOpen(true)}>+ Record POD</Button>
      </div>

      {/* Dispatched shipments waiting for POD */}
      {shipments.length > 0 && (
        <div className="mb-6 rounded-xl border border-yellow-100 bg-yellow-50 p-4">
          <p className="text-sm font-semibold text-yellow-800 mb-2">
            ⏳ {shipments.length} dispatched shipment{shipments.length > 1 ? "s" : ""} awaiting confirmation
          </p>
          <div className="flex flex-wrap gap-2">
            {shipments.slice(0, 5).map((s) => (
              <button
                key={s.id}
                onClick={() => { setForm((f) => ({ ...f, shipment_id: s.id })); setOpen(true); }}
                className="rounded-lg bg-white border border-yellow-200 px-3 py-1.5 text-xs font-medium text-yellow-900 hover:bg-yellow-100"
              >
                {s.shipment_no} — {s.customer_name ?? "Customer"}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* POD list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : pods.length === 0 ? (
        <p className="text-gray-400 text-sm py-8 text-center">No proofs of delivery recorded.</p>
      ) : (
        <div className="space-y-3">
          {pods.map((pod) => (
            <div key={pod.id} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg">✅</span>
                    <p className="font-medium text-gray-900">
                      Shipment {pod.shipment_id.slice(0, 8)}…
                    </p>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Received by: <span className="font-medium">{pod.received_by ?? "—"}</span>
                    {pod.signature_text && <span> · Signature: "{pod.signature_text}"</span>}
                  </p>
                  {pod.notes && <p className="text-xs text-gray-400 mt-1">{pod.notes}</p>}
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">
                    {pod.delivered_at ? new Date(pod.delivered_at).toLocaleString() : "—"}
                  </p>
                  {pod.gps_lat && (
                    <p className="text-xs text-blue-500">
                      📍 {pod.gps_lat.toFixed(4)}, {pod.gps_lng?.toFixed(4)}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create POD Modal */}
      <Modal open={open} onClose={() => setOpen(false)} title="Record Proof of Delivery">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Shipment *</label>
            <select
              value={form.shipment_id}
              onChange={(e) => setForm((f) => ({ ...f, shipment_id: e.target.value }))}
              required
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select dispatched shipment…</option>
              {shipments.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.shipment_no} — {s.customer_name ?? "Customer"}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Received By"
              value={form.received_by}
              onChange={(e) => setForm((f) => ({ ...f, received_by: e.target.value }))}
              placeholder="Name of recipient"
            />
            <Input
              label="Signature / Confirmation"
              value={form.signature_text}
              onChange={(e) => setForm((f) => ({ ...f, signature_text: e.target.value }))}
              placeholder="Initials or confirmation code"
            />
          </div>
          <Input
            label="Delivered At"
            type="datetime-local"
            value={form.delivered_at}
            onChange={(e) => setForm((f) => ({ ...f, delivered_at: e.target.value }))}
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              rows={2}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Optional delivery notes"
            />
          </div>
          {create.error && <p className="text-sm text-red-600">Failed to record POD.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Confirm Delivery</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
