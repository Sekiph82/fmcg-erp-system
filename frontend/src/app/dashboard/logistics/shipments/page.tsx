"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { logisticsApi, IntlShipment, IntlShipmentStatus, InventoryOwnerStatus, POLink } from "@/lib/logistics";
import { procurementApi, PO } from "@/lib/procurement";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";

const STATUS_FLOW: IntlShipmentStatus[] = [
  "DRAFT", "BOOKING_CONFIRMED", "CARGO_LOADED", "IN_TRANSIT",
  "ARRIVED_PORT", "CUSTOMS_HOLD", "CUSTOMS_CLEARED", "OUT_FOR_DELIVERY", "DELIVERED",
];
const OWNERSHIP_STATUS_FLOW: IntlShipmentStatus[] = [
  "CARGO_LOADED", "IN_TRANSIT", "ARRIVED_PORT", "CUSTOMS_HOLD",
  "CUSTOMS_CLEARED", "OUT_FOR_DELIVERY",
];
const SHIPMENT_STATUS_TRANSITIONS: Record<IntlShipmentStatus, IntlShipmentStatus[]> = {
  DRAFT: ["BOOKING_CONFIRMED", "CANCELLED"],
  BOOKING_CONFIRMED: ["CARGO_LOADED", "CANCELLED"],
  CARGO_LOADED: ["IN_TRANSIT"],
  IN_TRANSIT: ["ARRIVED_PORT"],
  ARRIVED_PORT: [],
  CUSTOMS_HOLD: [],
  CUSTOMS_CLEARED: ["OUT_FOR_DELIVERY"],
  OUT_FOR_DELIVERY: [],
  DELIVERED: [],
  CANCELLED: [],
};

const statusBadge = (s: IntlShipmentStatus) => {
  if (s === "DELIVERED" || s === "CUSTOMS_CLEARED") return "green";
  if (s === "CUSTOMS_HOLD") return "red";
  if (["IN_TRANSIT", "CARGO_LOADED", "BOOKING_CONFIRMED"].includes(s)) return "blue";
  if (["ARRIVED_PORT", "OUT_FOR_DELIVERY"].includes(s)) return "yellow";
  return "gray";
};

export default function ShipmentsPage() {
  const { hasPermission } = useAuth();
  const canEditShipment = hasPermission("logistics.edit");
  const qc = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [editing, setEditing] = useState<IntlShipment | null>(null);
  const [managingLinks, setManagingLinks] = useState<IntlShipment | null>(null);
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
                <th className="px-5 py-2 text-left">Actions</th>
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
                    <div className="flex flex-col items-start gap-1">
                      {canEditShipment && <button className="text-xs text-indigo-600 hover:underline" onClick={() => setEditing(s)}>Edit</button>}
                      <button className="text-xs text-indigo-600 hover:underline" onClick={() => setManagingLinks(s)}>View POs & containers</button>
                    </div>
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
      {managingLinks && (
        <ShipmentLinkageModal shipment={managingLinks} onClose={() => setManagingLinks(null)} />
      )}
    </div>
  );
}

function ShipmentLinkageModal({ shipment, onClose }: { shipment: IntlShipment; onClose: () => void }) {
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const canCreate = hasPermission("logistics.create");
  const canEdit = hasPermission("logistics.edit");
  const [selectedPoId, setSelectedPoId] = useState("");
  const [containerNo, setContainerNo] = useState("");
  const [containerType, setContainerType] = useState<"20FT_DRY" | "40FT_DRY" | "40FT_HC" | "20FT_REEFER" | "LCL">("40FT_DRY");
  const linksQuery = useQuery({
    queryKey: ["shipment-po-links", shipment.id],
    queryFn: () => logisticsApi.listPOLinks(shipment.id),
  });
  const ordersQuery = useQuery({
    queryKey: ["shipment-linkable-pos"],
    queryFn: () => procurementApi.listPOs(),
    enabled: canCreate,
  });
  const containersQuery = useQuery({
    queryKey: ["logistics-containers", shipment.id],
    queryFn: () => logisticsApi.listContainers({ shipment_id: shipment.id }),
  });
  const linkedIds = new Set((linksQuery.data ?? []).map((link) => link.po_id));
  const linkableOrders = (ordersQuery.data ?? []).filter((order) =>
    ["APPROVED", "ORDERED", "PARTIALLY_RECEIVED"].includes(order.status) && !linkedIds.has(order.id)
  );
  const addPo = useMutation({
    mutationFn: (po: PO) => logisticsApi.addPOLink(shipment.id, { po_id: po.id }),
    onSuccess: async () => {
      setSelectedPoId("");
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["shipment-po-links", shipment.id] }),
        qc.invalidateQueries({ queryKey: ["logistics-shipments"] }),
        qc.invalidateQueries({ queryKey: ["logistics-dashboard"] }),
      ]);
    },
  });
  const removePo = useMutation({
    mutationFn: (linkId: string) => logisticsApi.removePOLink(linkId),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["shipment-po-links", shipment.id] }),
        qc.invalidateQueries({ queryKey: ["logistics-shipments"] }),
        qc.invalidateQueries({ queryKey: ["logistics-dashboard"] }),
      ]);
    },
  });
  const addContainer = useMutation({
    mutationFn: () => logisticsApi.createContainer({
      shipment_id: shipment.id,
      container_no: containerNo.trim(),
      container_type: containerType,
    }),
    onSuccess: async () => {
      setContainerNo("");
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["logistics-containers", shipment.id] }),
        qc.invalidateQueries({ queryKey: ["logistics-containers"] }),
        qc.invalidateQueries({ queryKey: ["logistics-shipments"] }),
        qc.invalidateQueries({ queryKey: ["logistics-dashboard"] }),
      ]);
    },
  });
  const mutationError = addPo.error || removePo.error || addContainer.error;
  const errorMessage = mutationError instanceof Error ? mutationError.message : "Could not save the shipment linkage.";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/40 p-4" role="presentation">
      <section className="my-auto max-h-[90vh] w-full max-w-3xl space-y-5 overflow-y-auto rounded-xl bg-white p-6 shadow-xl" role="dialog" aria-modal="true" aria-labelledby="shipment-linkage-title">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="shipment-linkage-title" className="text-lg font-semibold">Purchase and container links</h2>
            <p className="text-sm text-gray-500">Shipment {shipment.shipment_no}</p>
          </div>
          <Button variant="secondary" onClick={onClose}>Close</Button>
        </div>
        {mutationError && <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{errorMessage}</p>}

        <section aria-labelledby="linked-orders-title" className="space-y-3">
          <h3 id="linked-orders-title" className="font-medium">Linked purchase orders</h3>
          {linksQuery.isLoading ? <p className="text-sm text-gray-500">Loading purchase-order links…</p> : linksQuery.isError ? (
            <p role="alert" className="text-sm text-red-700">Could not load purchase-order links.</p>
          ) : (linksQuery.data ?? []).length === 0 ? <p className="text-sm text-gray-500">No purchase orders are linked yet.</p> : (
            <ul className="divide-y rounded border">
              {(linksQuery.data ?? []).map((link) => (
                <li key={link.id} className="space-y-3 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-mono text-sm font-medium">{link.po_no || link.po_id}</p>
                      <p className="text-xs text-gray-500">{link.supplier_name || "Supplier not available"}</p>
                    </div>
                    {canEdit && <Button
                      variant="danger"
                      onClick={() => removePo.mutate(link.id)}
                      loading={removePo.isPending}
                      disabled={link.inventory_owner_status !== "UNCONFIRMED"}
                      title={link.inventory_owner_status !== "UNCONFIRMED" ? "Ownership history prevents unlinking this PO." : undefined}
                    >Unlink</Button>}
                  </div>
                  <ShipmentOwnershipPanel shipment={shipment} link={link} canEdit={canEdit} />
                </li>
              ))}
            </ul>
          )}
          {canCreate && <div className="flex flex-wrap gap-2">
            <label htmlFor="shipment-po-select" className="sr-only">Purchase order</label>
            <select id="shipment-po-select" className="min-w-64 flex-1 rounded border px-3 py-2 text-sm" value={selectedPoId} onChange={(event) => setSelectedPoId(event.target.value)} disabled={ordersQuery.isLoading || addPo.isPending}>
              <option value="">Select an approved or open purchase order…</option>
              {linkableOrders.map((order) => <option key={order.id} value={order.id}>{order.po_no} · {order.supplier_name || "Supplier"} · {order.status}</option>)}
            </select>
            <Button onClick={() => {
              const order = linkableOrders.find((candidate) => candidate.id === selectedPoId);
              if (order) addPo.mutate(order);
            }} loading={addPo.isPending} disabled={!selectedPoId || !linkableOrders.some((order) => order.id === selectedPoId)}>Link purchase order</Button>
          </div>}
          {ordersQuery.isError && <p role="alert" className="text-sm text-red-700">Could not load purchase orders. Check procurement access and try again.</p>}
          {!canCreate && <p className="text-xs text-gray-500">You have view-only access to shipment links.</p>}
          {canCreate && !ordersQuery.isLoading && !ordersQuery.isError && linkableOrders.length === 0 && <p className="text-xs text-gray-500">There are no unlinked approved or open purchase orders available.</p>}
        </section>

        <section aria-labelledby="linked-containers-title" className="space-y-3 border-t pt-4">
          <h3 id="linked-containers-title" className="font-medium">Containers on this shipment</h3>
          {containersQuery.isLoading ? <p className="text-sm text-gray-500">Loading containers…</p> : containersQuery.isError ? (
            <p role="alert" className="text-sm text-red-700">Could not load shipment containers.</p>
          ) : (containersQuery.data ?? []).length === 0 ? <p className="text-sm text-gray-500">No containers are linked yet.</p> : (
            <ul className="divide-y rounded border">
              {(containersQuery.data ?? []).map((container) => (
                <li key={container.id} className="flex items-center justify-between gap-3 p-3 text-sm">
                  <span className="font-mono font-medium">{container.container_no}</span>
                  <span className="text-gray-500">{container.container_type.replaceAll("_", " ")} · {container.status.replaceAll("_", " ")}</span>
                </li>
              ))}
            </ul>
          )}
          {canCreate && <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <label className="sr-only" htmlFor="shipment-container-no">Container number</label>
            <input id="shipment-container-no" className="rounded border px-3 py-2 text-sm font-mono" value={containerNo} onChange={(event) => setContainerNo(event.target.value)} placeholder="Container number" />
            <label className="sr-only" htmlFor="shipment-container-type">Container type</label>
            <select id="shipment-container-type" className="rounded border px-3 py-2 text-sm" value={containerType} onChange={(event) => setContainerType(event.target.value as typeof containerType)}>
              <option value="20FT_DRY">20 ft dry</option><option value="40FT_DRY">40 ft dry</option><option value="40FT_HC">40 ft high cube</option><option value="20FT_REEFER">20 ft reefer</option><option value="LCL">LCL</option>
            </select>
            <Button onClick={() => addContainer.mutate()} loading={addContainer.isPending} disabled={!containerNo.trim()}>Add container</Button>
          </div>}
        </section>
      </section>
    </div>
  );
}

function ShipmentOwnershipPanel({ shipment, link, canEdit }: {
  shipment: IntlShipment;
  link: POLink;
  canEdit: boolean;
}) {
  const qc = useQueryClient();
  const [newOwner, setNewOwner] = useState<Exclude<InventoryOwnerStatus, "UNCONFIRMED"> | "">("");
  const [sourceReference, setSourceReference] = useState("");
  const [notes, setNotes] = useState("");
  const ownershipQuery = useQuery({
    queryKey: ["shipment-ownership-events", shipment.id, link.id],
    queryFn: () => logisticsApi.listShipmentOwnershipEvents(shipment.id, link.id),
  });
  const recordOwnership = useMutation({
    mutationFn: () => logisticsApi.recordShipmentOwnership(shipment.id, link.id, {
      new_owner: newOwner as Exclude<InventoryOwnerStatus, "UNCONFIRMED">,
      source_reference: sourceReference.trim(),
      notes: notes.trim() || undefined,
    }),
    onSuccess: async () => {
      setSourceReference("");
      setNotes("");
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["shipment-po-links", shipment.id] }),
        qc.invalidateQueries({ queryKey: ["shipment-ownership-events", shipment.id, link.id] }),
      ]);
    },
  });
  const ownerLabel = (owner: InventoryOwnerStatus) => owner.replaceAll("_", " ");
  const canRecordNow = OWNERSHIP_STATUS_FLOW.includes(shipment.status);

  return (
    <div className="space-y-2 rounded bg-gray-50 p-3" aria-label={`Inventory ownership for ${link.po_no || link.po_id}`}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium">Inventory owner:</span>
        <Badge label={ownerLabel(link.inventory_owner_status)} variant={link.inventory_owner_status === "UNCONFIRMED" ? "yellow" : "blue"} />
      </div>
      <p className="text-xs text-gray-600">Ownership stays unconfirmed until a source reference is entered. Incoterm does not set ownership automatically.</p>
      {ownershipQuery.isLoading ? <p className="text-xs text-gray-500">Loading ownership history…</p> : ownershipQuery.isError ? (
        <p role="alert" className="text-xs text-red-700">Could not load ownership history.</p>
      ) : (ownershipQuery.data ?? []).length > 0 ? (
        <ol className="space-y-1 text-xs text-gray-600" aria-label="Ownership history">
          {(ownershipQuery.data ?? []).map((event) => (
            <li key={event.id}>
              {ownerLabel(event.previous_owner)} → {ownerLabel(event.new_owner)} · {event.source_reference} · {new Date(event.effective_at).toLocaleString()}
              {event.changed_by_name ? ` · ${event.changed_by_name}` : ""}
            </li>
          ))}
        </ol>
      ) : <p className="text-xs text-gray-500">No ownership changes recorded.</p>}
      {canEdit && canRecordNow && (
        <div className="grid gap-2 sm:grid-cols-[minmax(8rem,0.8fr)_minmax(12rem,1fr)_minmax(12rem,1fr)_auto]">
          <label className="sr-only" htmlFor={`ownership-owner-${link.id}`}>New inventory owner</label>
          <select id={`ownership-owner-${link.id}`} className="rounded border px-2 py-2 text-xs" value={newOwner} onChange={(event) => setNewOwner(event.target.value as typeof newOwner)} disabled={recordOwnership.isPending}>
            <option value="">Select documented owner…</option>
            <option value="SUPPLIER_OWNED">Supplier owned</option>
            <option value="BUYER_OWNED">Buyer owned</option>
          </select>
          <label className="sr-only" htmlFor={`ownership-reference-${link.id}`}>Source document reference</label>
          <input id={`ownership-reference-${link.id}`} className="min-w-0 rounded border px-2 py-2 text-xs" value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} maxLength={200} placeholder="Contract / document reference" />
          <label className="sr-only" htmlFor={`ownership-notes-${link.id}`}>Ownership notes</label>
          <input id={`ownership-notes-${link.id}`} className="min-w-0 rounded border px-2 py-2 text-xs" value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={2000} placeholder="Optional notes" />
          <Button onClick={() => { if (newOwner && sourceReference.trim()) recordOwnership.mutate(); }} loading={recordOwnership.isPending} disabled={!newOwner || !sourceReference.trim() || recordOwnership.isPending}>Record owner</Button>
        </div>
      )}
      {canEdit && !canRecordNow && <p className="text-xs text-gray-500">Ownership can be recorded after cargo is loaded and before delivery.</p>}
      {recordOwnership.isError && <p role="alert" className="text-xs text-red-700">Could not record ownership. Verify the shipment status and document reference, then retry.</p>}
      {!canEdit && <p className="text-xs text-gray-500">You have view-only access to ownership history.</p>}
    </div>
  );
}

function ShipmentModal({ title, initial, onClose, onSubmit, loading }: {
  title: string; initial?: IntlShipment; onClose: () => void; onSubmit: (d: object) => void; loading: boolean;
}) {
  const statusOptions = initial
    ? [initial.status, ...SHIPMENT_STATUS_TRANSITIONS[initial.status]]
    : ["DRAFT" as IntlShipmentStatus];
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
              {statusOptions.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
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
