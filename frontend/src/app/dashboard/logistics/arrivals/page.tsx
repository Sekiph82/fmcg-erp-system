"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  logisticsApi, IntlShipment, ArrivalNotification, CustomsClearance, ClearanceStatus, ClearanceMilestone,
  ShipmentReceiptClosure, ShipmentReceiptGRNOption,
  LocalCostRecord, LocalCostType, LocalPaymentMethod, LocalCostStatus,
} from "@/lib/logistics";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";

const clearanceBadge = (s?: ClearanceStatus) => {
  if (!s) return "gray";
  if (s === "CLEARED") return "green";
  if (s === "HELD") return "red";
  if (s === "DUTY_PAID") return "yellow";
  return "blue";
};

const NEXT_CLEARANCE_STATUSES: Record<ClearanceStatus, ClearanceStatus[]> = {
  PENDING: ["DOCS_SUBMITTED", "HELD"],
  DOCS_SUBMITTED: ["UNDER_REVIEW", "HELD"],
  UNDER_REVIEW: ["EXAM_REQUESTED", "DUTY_ASSESSED", "HELD"],
  EXAM_REQUESTED: ["UNDER_REVIEW", "DUTY_ASSESSED", "HELD"],
  DUTY_ASSESSED: ["DUTY_PAID", "HELD"],
  DUTY_PAID: ["CLEARED", "HELD"],
  CLEARED: [],
  HELD: ["UNDER_REVIEW"],
};

export default function ArrivalsPage() {
  const { hasPermission } = useAuth();
  const canViewClearance = hasPermission("logistics.view");
  const canCreateClearance = hasPermission("logistics.create");
  const canEditClearance = hasPermission("logistics.edit");
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string>("");
  const [tab, setTab] = useState<"arrival" | "clearance" | "local_costs">("arrival");
  const [showNewClearance, setShowNewClearance] = useState(false);
  const [showNewCost, setShowNewCost] = useState(false);

  const { data: shipments = [] } = useQuery({
    queryKey: ["logistics-shipments"],
    queryFn: () => logisticsApi.listShipments(),
  });
  const selectedShipment = shipments.find((s) => s.id === selectedId);

  const { data: alerts = [] } = useQuery({
    queryKey: ["logistics-eta-alerts"],
    queryFn: () => logisticsApi.getEtaAlerts(21),
  });

  const { data: arrival, isLoading: arrLoading } = useQuery({
    queryKey: ["logistics-arrival", selectedId],
    queryFn: () => (selectedId ? logisticsApi.getArrival(selectedId).catch((error: unknown) => {
      if ((error as { response?: { status?: number } })?.response?.status === 404) return null;
      throw error;
    }) : null),
    enabled: !!selectedId,
  });

  const { data: receiptClosure = null, isLoading: receiptClosureLoading } = useQuery({
    queryKey: ["logistics-receipt-closure", selectedId],
    queryFn: () => (selectedId ? logisticsApi.getReceiptClosure(selectedId).catch((error: unknown) => {
      if ((error as { response?: { status?: number } })?.response?.status === 404) return null;
      throw error;
    }) : null),
    enabled: !!selectedId && canViewClearance,
  });

  const { data: receiptOptions = [], isLoading: receiptOptionsLoading, error: receiptOptionsError } = useQuery({
    queryKey: ["logistics-receipt-options", selectedId],
    queryFn: () => (selectedId ? logisticsApi.listReceiptOptions(selectedId) : []),
    enabled: !!selectedId && !!selectedShipment && selectedShipment.status === "OUT_FOR_DELIVERY" && canViewClearance,
  });

  const { data: clearance, isLoading: clLoading } = useQuery({
    queryKey: ["logistics-clearance", selectedId],
    queryFn: () => (selectedId ? logisticsApi.getClearance(selectedId).catch(() => null) : null),
    enabled: !!selectedId && tab === "clearance",
  });

  const { data: clearanceMilestones = [], isLoading: milestonesLoading } = useQuery({
    queryKey: ["logistics-clearance-milestones", selectedId],
    queryFn: () => logisticsApi.listClearanceMilestones(selectedId),
    enabled: !!selectedId && tab === "clearance" && !!clearance,
  });

  const updateArrival = useMutation({
    mutationFn: (data: object) => logisticsApi.updateArrival(selectedId, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["logistics-arrival"] }); qc.invalidateQueries({ queryKey: ["logistics-dashboard"] }); },
  });

  const closeReceipt = useMutation({
    mutationFn: (grnIds: string[]) => logisticsApi.closeReceipt(selectedId, grnIds),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["logistics-receipt-closure", selectedId] }),
        qc.invalidateQueries({ queryKey: ["logistics-receipt-options", selectedId] }),
        qc.invalidateQueries({ queryKey: ["logistics-arrival", selectedId] }),
        qc.invalidateQueries({ queryKey: ["logistics-shipments"] }),
        qc.invalidateQueries({ queryKey: ["logistics-dashboard"] }),
      ]);
    },
  });

  const createClearance = useMutation({
    mutationFn: (data: object) => logisticsApi.createClearance(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["logistics-clearance"] }); setShowNewClearance(false); },
  });

  const updateClearance = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => logisticsApi.updateClearance(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["logistics-clearance"] }),
  });

  const recordClearanceMilestone = useMutation({
    mutationFn: (data: object) => logisticsApi.recordClearanceMilestone(selectedId, data),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["logistics-clearance", selectedId] }),
        qc.invalidateQueries({ queryKey: ["logistics-clearance-milestones", selectedId] }),
        qc.invalidateQueries({ queryKey: ["logistics-arrival", selectedId] }),
        qc.invalidateQueries({ queryKey: ["logistics-shipments"] }),
        qc.invalidateQueries({ queryKey: ["logistics-dashboard"] }),
      ]);
    },
  });

  const { data: localCostSummary, isLoading: lcLoading } = useQuery({
    queryKey: ["local-costs", selectedId],
    queryFn: () => (selectedId ? logisticsApi.listLocalCosts(selectedId) : null),
    enabled: !!selectedId && tab === "local_costs",
  });

  const createCost = useMutation({
    mutationFn: (data: object) => logisticsApi.createLocalCost(selectedId, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["local-costs", selectedId] }); setShowNewCost(false); },
  });

  const updateCost = useMutation({
    mutationFn: ({ id, data }: { id: string; data: object }) => logisticsApi.updateLocalCost(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["local-costs", selectedId] }),
  });

  const deleteCost = useMutation({
    mutationFn: (id: string) => logisticsApi.deleteLocalCost(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["local-costs", selectedId] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Arrival & Customs Clearance</h1>
        <p className="text-sm text-gray-500 mt-1">ETA alerts, port events and KRA customs clearance</p>
      </div>

      {/* ETA alerts */}
      {alerts.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm font-semibold text-amber-800 mb-2">Upcoming arrivals — next 21 days</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-amber-700 font-semibold border-b border-amber-200">
                  <th className="text-left py-1 pr-4">Shipment</th>
                  <th className="text-left pr-4">Vessel</th>
                  <th className="text-left pr-4">B/L</th>
                  <th className="text-left pr-4">ETA</th>
                  <th className="text-right pr-4">Days</th>
                  <th className="text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((s) => (
                  <tr key={s.id} className="border-b border-amber-100">
                    <td className="py-1.5 pr-4 font-mono font-semibold text-indigo-700">{s.shipment_no}</td>
                    <td className="pr-4 text-amber-800">{s.vessel_name || s.carrier || "—"}</td>
                    <td className="pr-4 font-mono">{s.bl_number || "—"}</td>
                    <td className="pr-4 font-semibold">{s.eta}</td>
                    <td className={`pr-4 text-right font-bold ${s.days_to_eta != null && s.days_to_eta <= 5 ? "text-red-600" : "text-amber-700"}`}>
                      {s.days_to_eta != null ? `${s.days_to_eta}d` : "—"}
                    </td>
                    <td>{s.status.replace(/_/g, " ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Shipment selector */}
      <div className="flex items-center gap-3">
        <label htmlFor="arrival-shipment-selector" className="text-sm font-medium text-gray-600">Shipment:</label>
        <select id="arrival-shipment-selector" className="border rounded px-3 py-2 text-sm min-w-72" value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
          <option value="">Select shipment to manage…</option>
          {shipments.map((s) => <option key={s.id} value={s.id}>{s.shipment_no} — {s.vessel_name || s.carrier} — ETA: {s.eta || "?"}</option>)}
        </select>
      </div>

      {selectedId && (
        <>
          {/* Tabs */}
          <div className="flex gap-1 border-b">
            {([
              { key: "arrival", label: "Arrival Events" },
              { key: "clearance", label: "Customs Clearance (KRA)" },
              { key: "local_costs", label: "Local Costs & Payments" },
            ] as const).map(({ key, label }) => (
              <button key={key} onClick={() => setTab(key)}
                className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${tab === key ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
                {label}
              </button>
            ))}
          </div>

          {/* Arrival tab */}
          {tab === "arrival" && (
            <div className="bg-white rounded-lg border">
              <div className="px-5 py-3 border-b font-semibold text-gray-800">
                Arrival — {selectedShipment?.shipment_no}
              </div>
              {arrLoading ? <p className="px-5 py-8 text-center text-gray-400">Loading…</p> : arrival ? (
                <ArrivalForm arrival={arrival} onSave={(d) => updateArrival.mutate(d)} loading={updateArrival.isPending} />
              ) : <p className="px-5 py-5 text-center text-gray-400">No arrival timeline has been recorded yet.</p>}
              {canViewClearance && selectedShipment && (
                <ReceiptClosurePanel
                  shipmentStatus={selectedShipment.status}
                  closure={receiptClosure}
                  options={receiptOptions}
                  loading={receiptClosureLoading || receiptOptionsLoading}
                  canEdit={canEditClearance}
                  optionsError={receiptOptionsError instanceof Error ? receiptOptionsError.message : ""}
                  saving={closeReceipt.isPending}
                  saveError={closeReceipt.error instanceof Error ? closeReceipt.error.message : ""}
                  onClose={(grnIds) => closeReceipt.mutate(grnIds)}
                />
              )}
            </div>
          )}

          {/* Local Costs tab */}
          {tab === "local_costs" && (
            <div className="bg-white rounded-lg border">
              <div className="px-5 py-3 border-b flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-gray-800">Local Logistics Costs — {selectedShipment?.shipment_no}</h2>
                  <p className="text-xs text-gray-400 mt-0.5">Kenya-side transport, clearing fees, port handling — M-Pesa supported</p>
                </div>
                <Button onClick={() => setShowNewCost(true)}>+ Add Cost</Button>
              </div>
              {lcLoading ? (
                <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
              ) : localCostSummary ? (
                <LocalCostsPanel
                  summary={localCostSummary}
                  onMarkPaid={(id, ref, phone) => updateCost.mutate({ id, data: { payment_status: "PAID", mpesa_reference: ref || undefined, mpesa_phone: phone || undefined, paid_date: new Date().toISOString().split("T")[0] } })}
                  onDelete={(id) => { if (confirm("Delete this cost record?")) deleteCost.mutate(id); }}
                  saving={updateCost.isPending || deleteCost.isPending}
                />
              ) : (
                <p className="px-5 py-8 text-center text-gray-400">No cost records yet — click &quot;+ Add Cost&quot; to start</p>
              )}
            </div>
          )}

          {/* Clearance tab */}
          {tab === "clearance" && (
            <div className="bg-white rounded-lg border">
              <div className="px-5 py-3 border-b flex items-center justify-between">
                <h2 className="font-semibold text-gray-800">KRA Customs Clearance — {selectedShipment?.shipment_no}</h2>
                {!clearance && canCreateClearance && <Button onClick={() => setShowNewClearance(true)}>Open Clearance</Button>}
                {clearance && <Badge label={clearance.status} variant={clearanceBadge(clearance.status)} />}
              </div>
              {!canViewClearance ? <p className="px-5 py-8 text-center text-gray-500">You need logistics.view permission to see customs clearance.</p> : clLoading ? <p className="px-5 py-8 text-center text-gray-400">Loading…</p> : clearance ? (
                <ClearanceForm
                  clearance={clearance}
                  milestones={clearanceMilestones}
                  milestonesLoading={milestonesLoading}
                  canEdit={canEditClearance}
                  onSave={(d) => updateClearance.mutate({ id: clearance.id, data: d })}
                  onRecordMilestone={(d) => recordClearanceMilestone.mutateAsync(d)}
                  loading={updateClearance.isPending}
                  milestoneSaving={recordClearanceMilestone.isPending}
                  milestoneError={recordClearanceMilestone.error instanceof Error ? recordClearanceMilestone.error.message : ""}
                />
              ) : (
                <p className="px-5 py-8 text-center text-gray-400">{canCreateClearance ? "No clearance record — click \"Open Clearance\" to start" : "No clearance record. You need logistics.create permission to open one."}</p>
              )}
            </div>
          )}
        </>
      )}

      {!selectedId && (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">Select a shipment to manage arrival and customs clearance</div>
      )}

      {showNewClearance && selectedId && (
        <NewClearanceModal shipmentId={selectedId}
          onClose={() => setShowNewClearance(false)}
          onSubmit={(d) => createClearance.mutate(d)} loading={createClearance.isPending} />
      )}
      {showNewCost && selectedId && (
        <NewLocalCostModal
          onClose={() => setShowNewCost(false)}
          onSubmit={(d) => createCost.mutate(d)}
          loading={createCost.isPending}
        />
      )}
    </div>
  );
}

function ArrivalForm({ arrival, onSave, loading }: { arrival: ArrivalNotification; onSave: (d: object) => void; loading: boolean }) {
  const { hasPermission } = useAuth();
  const canEdit = hasPermission("logistics.edit");
  const [form, setForm] = useState({
    eta_revised: arrival.eta_revised ?? "",
    ata: arrival.ata ?? "",
    port_discharge_date: arrival.port_discharge_date ?? "",
    notes: arrival.notes ?? "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const events = [
    { key: "eta_revised", label: "Revised ETA", done: !!arrival.eta_revised },
    { key: "ata", label: "Actual Arrival at Port (ATA)", done: !!arrival.ata },
    { key: "port_discharge_date", label: "Port Discharge / Released", done: !!arrival.port_discharge_date },
    { key: "customs_clearance_date", label: "Customs Cleared", done: !!arrival.customs_clearance_date },
    { key: "delivery_date", label: "Delivered to Warehouse", done: !!arrival.delivery_date },
  ];

  return (
    <div className="p-5 space-y-4">
      {/* Timeline */}
      <div className="flex items-center gap-0 mb-4">
        {events.map((e, i) => (
          <div key={e.key} className="flex items-center flex-1">
            <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${e.done ? "bg-green-500 text-white" : "bg-gray-200 text-gray-400"}`}>
              {e.done ? "✓" : i + 1}
            </div>
            <div className="flex-1 text-center px-1">
              <p className={`text-xs ${e.done ? "text-green-600 font-medium" : "text-gray-400"}`}>{e.label}</p>
            </div>
            {i < events.length - 1 && <div className={`h-0.5 w-4 flex-shrink-0 ${e.done ? "bg-green-400" : "bg-gray-200"}`} />}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {events.filter(({ key }) => key !== "delivery_date").map(({ key, label }) => (
          <div key={key}>
            <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
            <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={key === "customs_clearance_date" ? arrival.customs_clearance_date ?? "" : (form as Record<string, string>)[key]} disabled={!canEdit || key === "customs_clearance_date"} onChange={(e) => set(key, e.target.value)} />
          </div>
        ))}
        <div>
          <label htmlFor="arrival-delivery-date" className="block text-xs font-medium text-gray-600 mb-1">Delivered to Warehouse</label>
          <input id="arrival-delivery-date" type="date" className="w-full border rounded px-3 py-2 text-sm bg-gray-50" value={arrival.delivery_date ?? ""} disabled readOnly />
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
        <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
      </div>
      {canEdit && <div className="flex justify-end">
        <Button loading={loading} onClick={() => onSave(
          Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v || undefined]))
        )}>Save Arrival</Button>
      </div>}
    </div>
  );
}

function ReceiptClosurePanel({
  shipmentStatus, closure, options, loading, canEdit, optionsError, saving, saveError, onClose,
}: {
  shipmentStatus: IntlShipment["status"];
  closure: ShipmentReceiptClosure | null;
  options: ShipmentReceiptGRNOption[];
  loading: boolean;
  canEdit: boolean;
  optionsError: string;
  saving: boolean;
  saveError: string;
  onClose: (grnIds: string[]) => void;
}) {
  const [selectedGRNs, setSelectedGRNs] = useState<string[]>([]);
  useEffect(() => setSelectedGRNs([]), [options]);

  const toggleGRN = (id: string) => {
    setSelectedGRNs((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
  };

  return (
    <section aria-labelledby="receipt-closure-heading" className="m-5 rounded-lg border bg-slate-50 p-4">
      <h3 id="receipt-closure-heading" className="font-semibold text-gray-800">Kenya warehouse receipt closure</h3>
      <p className="mt-1 text-xs text-gray-500">A shipment closes only against posted GRNs linked to its purchase orders. Closing records the GRN references, operator, and system time.</p>
      {loading ? <p className="mt-3 text-sm text-gray-500">Loading receipt records…</p> : closure ? (
        <div className="mt-3 space-y-2">
          <p className="text-sm font-medium text-green-700">Shipment receipt closed on {new Date(closure.closed_at).toLocaleString()} by {closure.closed_by_name || "recorded user"}.</p>
          <ul className="list-disc pl-5 text-sm text-gray-700">
            {closure.grns.map((grn) => (
              <li key={grn.id}>{grn.grn_no} · PO {grn.po_no} · {grn.received_date} · {grn.warehouse_name || "warehouse"}</li>
            ))}
          </ul>
        </div>
      ) : shipmentStatus !== "OUT_FOR_DELIVERY" ? (
        <p className="mt-3 text-sm text-gray-600">Receipt closure becomes available after customs clearance and dispatch to the warehouse.</p>
      ) : optionsError ? (
        <p role="alert" className="mt-3 text-sm text-red-700">Could not load posted GRNs: {optionsError}</p>
      ) : options.length === 0 ? (
        <p className="mt-3 text-sm text-gray-600">No unused posted GRNs are linked to this shipment yet. Post a warehouse receipt in Procurement first.</p>
      ) : (
        <>
          <div className="mt-3 space-y-2">
            {options.map((grn) => (
              <label key={grn.id} className="flex items-start gap-2 rounded border bg-white p-2 text-sm">
                <input type="checkbox" checked={selectedGRNs.includes(grn.id)} onChange={() => toggleGRN(grn.id)} disabled={!canEdit || saving} />
                <span>{grn.grn_no} · PO {grn.po_no} · {grn.received_date} · {grn.warehouse_name || "warehouse"}</span>
              </label>
            ))}
          </div>
          {saveError && <p role="alert" className="mt-3 text-sm text-red-700">Receipt closure was not saved: {saveError}</p>}
          {canEdit && <div className="mt-3 flex justify-end">
            <Button loading={saving} disabled={selectedGRNs.length === 0 || saving} onClick={() => onClose(selectedGRNs)}>
              Close receipt with selected GRNs
            </Button>
          </div>}
          {!canEdit && <p className="mt-3 text-sm text-gray-500">You need logistics.edit permission to close the receipt.</p>}
        </>
      )}
    </section>
  );
}

function ClearanceForm({
  clearance, milestones, milestonesLoading, canEdit, onSave, onRecordMilestone,
  loading, milestoneSaving, milestoneError,
}: {
  clearance: CustomsClearance;
  milestones: ClearanceMilestone[];
  milestonesLoading: boolean;
  canEdit: boolean;
  onSave: (d: object) => void;
  onRecordMilestone: (d: object) => Promise<unknown>;
  loading: boolean;
  milestoneSaving: boolean;
  milestoneError: string;
}) {
  const [form, setForm] = useState({
    entry_no: clearance.entry_no ?? "",
    agent_name: clearance.agent_name ?? "",
    cif_value_usd: clearance.cif_value_usd?.toString() ?? "",
    import_duty: clearance.import_duty?.toString() ?? "",
    vat: clearance.vat?.toString() ?? "",
    idf_fee: clearance.idf_fee?.toString() ?? "",
    railway_development_levy: clearance.railway_development_levy?.toString() ?? "",
    other_charges: clearance.other_charges?.toString() ?? "",
    total_taxes_kes: clearance.total_taxes_kes?.toString() ?? "",
    kra_pin: clearance.kra_pin ?? "",
    notes: clearance.notes ?? "",
  });
  const [nextStatus, setNextStatus] = useState<ClearanceStatus | "">(NEXT_CLEARANCE_STATUSES[clearance.status][0] ?? "");
  const [sourceReference, setSourceReference] = useState("");
  const [milestoneNotes, setMilestoneNotes] = useState("");
  useEffect(() => {
    setNextStatus(NEXT_CLEARANCE_STATUSES[clearance.status][0] ?? "");
  }, [clearance.status]);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const numFields = ["cif_value_usd", "import_duty", "vat", "idf_fee", "railway_development_levy", "other_charges", "total_taxes_kes"];
  const autoTotal = ["import_duty", "vat", "idf_fee", "railway_development_levy", "other_charges"]
    .reduce((s, k) => s + (parseFloat((form as Record<string,string>)[k]) || 0), 0);

  return (
    <div className="p-5 space-y-4">
      <section aria-labelledby="clearance-timeline-heading" className="rounded-lg border bg-slate-50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 id="clearance-timeline-heading" className="font-semibold text-gray-800">Clearance milestone history</h3>
            <p className="text-xs text-gray-500">Manual evidence references are recorded with the operator and system time; no customs authority integration is implied.</p>
          </div>
          <Badge label={clearance.status.replace(/_/g, " ")} variant={clearanceBadge(clearance.status)} />
        </div>
        {milestonesLoading ? <p className="mt-3 text-sm text-gray-500">Loading milestone history…</p> : milestones.length === 0 ? (
          <p className="mt-3 text-sm text-gray-500">No milestone history is available. Current recorded status: <strong>{clearance.status.replace(/_/g, " ")}</strong>. Existing status may predate history capture.</p>
        ) : (
          <ol className="mt-3 divide-y rounded border bg-white">
            {milestones.map((event) => (
              <li key={event.id} className="grid gap-1 p-3 text-sm md:grid-cols-[1fr_1fr_2fr]">
                <span><strong>{event.previous_status.replace(/_/g, " ")}</strong> → <strong>{event.new_status.replace(/_/g, " ")}</strong></span>
                <span className="text-gray-600">{new Date(event.effective_at).toLocaleString()} · {event.changed_by_name || event.changed_by_id}</span>
                <span className="text-gray-600">Ref: <span className="font-mono">{event.source_reference}</span>{event.notes ? ` · ${event.notes}` : ""}</span>
              </li>
            ))}
          </ol>
        )}
        {canEdit && NEXT_CLEARANCE_STATUSES[clearance.status].length > 0 && (
          <div className="mt-4 grid gap-3 border-t pt-4 md:grid-cols-4">
            <div>
              <label htmlFor="clearance-next-status" className="mb-1 block text-xs font-medium text-gray-600">Next milestone</label>
              <select id="clearance-next-status" className="w-full rounded border px-3 py-2 text-sm" value={nextStatus} onChange={(event) => setNextStatus(event.target.value as ClearanceStatus | "")}>
                {NEXT_CLEARANCE_STATUSES[clearance.status].map((candidate) => <option key={candidate} value={candidate}>{candidate.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="clearance-source-reference" className="mb-1 block text-xs font-medium text-gray-600">Supporting reference</label>
              <input id="clearance-source-reference" className="w-full rounded border px-3 py-2 text-sm font-mono" value={sourceReference} maxLength={200} onChange={(event) => setSourceReference(event.target.value)} placeholder="e.g. entered filing / receipt ref" required />
            </div>
            <div>
              <label htmlFor="clearance-milestone-notes" className="mb-1 block text-xs font-medium text-gray-600">Notes{nextStatus === "HELD" ? " (hold reason required)" : " (optional)"}</label>
              <input id="clearance-milestone-notes" className="w-full rounded border px-3 py-2 text-sm" value={milestoneNotes} maxLength={2000} onChange={(event) => setMilestoneNotes(event.target.value)} />
            </div>
            <div className="flex items-end">
              <Button loading={milestoneSaving} disabled={!nextStatus || !sourceReference.trim() || (nextStatus === "HELD" && !milestoneNotes.trim())} onClick={async () => {
                if (!nextStatus || !sourceReference.trim()) return;
                try {
                  await onRecordMilestone({ new_status: nextStatus, source_reference: sourceReference, notes: milestoneNotes || undefined });
                  setSourceReference("");
                  setMilestoneNotes("");
                } catch {
                  // Keep the reference and notes visible for retry after the inline error is shown.
                }
              }}>Record milestone</Button>
            </div>
          </div>
        )}
        {!canEdit && <p className="mt-3 text-xs text-gray-500">View-only access: logistics.edit permission is required to record milestones.</p>}
        {milestoneError && <p role="alert" className="mt-3 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">{milestoneError}</p>}
      </section>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">IDF / Entry No</label>
          <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.entry_no} disabled={!canEdit} onChange={(e) => set("entry_no", e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Clearing Agent</label>
          <input className="w-full border rounded px-3 py-2 text-sm" value={form.agent_name} disabled={!canEdit} onChange={(e) => set("agent_name", e.target.value)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">KRA PIN</label>
          <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.kra_pin} disabled={!canEdit} onChange={(e) => set("kra_pin", e.target.value)} />
        </div>
        <div className="rounded border bg-gray-50 p-2 text-sm">
          <span className="block text-xs text-gray-500">Submitted</span>{clearance.submission_date || "Not recorded"}
        </div>
        <div className="rounded border bg-gray-50 p-2 text-sm">
          <span className="block text-xs text-gray-500">Examination requested</span>{clearance.examination_date || "Not recorded"}
        </div>
        <div className="rounded border bg-gray-50 p-2 text-sm">
          <span className="block text-xs text-gray-500">Clearance recorded</span>{clearance.clearance_date || "Not recorded"}
        </div>
      </div>

      <div className="border-t pt-4">
        <p className="text-xs font-semibold text-gray-600 mb-3 uppercase tracking-wide">Landed Cost & Duties (KES)</p>
        <div className="grid grid-cols-4 gap-3">
          {[
            { key: "cif_value_usd", label: "CIF Value (USD)" },
            { key: "import_duty", label: "Import Duty" },
            { key: "vat", label: "VAT (16%)" },
            { key: "idf_fee", label: "IDF Fee" },
            { key: "railway_development_levy", label: "Railway Dev. Levy" },
            { key: "other_charges", label: "Other Charges" },
          ].map(({ key, label }) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
              <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={(form as Record<string,string>)[key]} disabled={!canEdit} onChange={(e) => set(key, e.target.value)} />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Total Taxes (KES)</label>
            <input type="number" className="w-full border rounded px-3 py-2 text-sm font-semibold" value={form.total_taxes_kes || autoTotal.toFixed(2)} disabled={!canEdit} onChange={(e) => set("total_taxes_kes", e.target.value)} />
            <p className="text-xs text-gray-400 mt-0.5">Auto: {autoTotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
          </div>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
        <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} disabled={!canEdit} onChange={(e) => set("notes", e.target.value)} />
      </div>
      {canEdit && <div className="flex justify-end">
        <Button loading={loading} onClick={() => onSave({
          ...form,
          ...Object.fromEntries(numFields.map((k) => [k, (form as Record<string,string>)[k] ? parseFloat((form as Record<string,string>)[k]) : undefined])),
        })}>Save Clearance</Button>
      </div>}
    </div>
  );
}

// ── Local Costs Panel ──────────────────────────────────────────────────────────

const COST_TYPE_LABELS: Record<LocalCostType, string> = {
  TRANSPORT: "Transport",
  CLEARING_FEE: "Clearing Fee",
  PORT_HANDLING: "Port Handling",
  WAREHOUSE_HANDLING: "Warehouse Handling",
  FUMIGATION: "Fumigation",
  INSPECTION_FEE: "Inspection Fee",
  OTHER: "Other",
};

const statusBadge = (s: LocalCostStatus) =>
  s === "PAID" ? "bg-emerald-100 text-emerald-700" : s === "DISPUTED" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700";

const methodIcon: Record<LocalPaymentMethod, string> = {
  MPESA: "📱",
  BANK: "🏦",
  CASH: "💵",
};

function LocalCostsPanel({
  summary, onMarkPaid, onDelete, saving,
}: {
  summary: ReturnType<typeof import("@/lib/logistics")["logisticsApi"]["listLocalCosts"]> extends Promise<infer T> ? T : never;
  onMarkPaid: (id: string, ref: string, phone: string) => void;
  onDelete: (id: string) => void;
  saving: boolean;
}) {
  const [markingId, setMarkingId] = useState<string | null>(null);
  const [ref, setRef] = useState("");
  const [phone, setPhone] = useState("");

  return (
    <div className="p-5 space-y-4">
      {/* Summary bar */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-gray-50 border p-3 text-center">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total</p>
          <p className="text-xl font-bold text-gray-900">KES {summary.total_kes.toLocaleString()}</p>
        </div>
        <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-3 text-center">
          <p className="text-xs text-emerald-600 uppercase tracking-wide">Paid</p>
          <p className="text-xl font-bold text-emerald-700">KES {summary.paid_kes.toLocaleString()}</p>
        </div>
        <div className="rounded-lg bg-amber-50 border border-amber-100 p-3 text-center">
          <p className="text-xs text-amber-600 uppercase tracking-wide">Pending</p>
          <p className="text-xl font-bold text-amber-700">KES {summary.pending_kes.toLocaleString()}</p>
        </div>
      </div>

      {/* Cost rows */}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase">
            <th className="px-3 py-2 text-left">Type</th>
            <th className="px-3 py-2 text-left">Description</th>
            <th className="px-3 py-2 text-left">Vendor</th>
            <th className="px-3 py-2 text-right">Amount (KES)</th>
            <th className="px-3 py-2 text-center">Method</th>
            <th className="px-3 py-2 text-left">M-Pesa Ref</th>
            <th className="px-3 py-2 text-center">Status</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y">
          {summary.by_type.length === 0 && (
            <tr><td colSpan={8} className="px-3 py-8 text-center text-gray-400">No cost records</td></tr>
          )}
          {summary.by_type.map((c) => (
            <>
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-3 py-2.5 font-medium text-gray-800">{COST_TYPE_LABELS[c.cost_type]}</td>
                <td className="px-3 py-2.5 text-gray-600">{c.description}</td>
                <td className="px-3 py-2.5 text-gray-500">{c.vendor_name || "—"}</td>
                <td className="px-3 py-2.5 text-right font-semibold">{c.amount_kes.toLocaleString()}</td>
                <td className="px-3 py-2.5 text-center text-lg">{methodIcon[c.payment_method]}</td>
                <td className="px-3 py-2.5 font-mono text-xs text-gray-500">
                  {c.mpesa_reference ? (
                    <span className="bg-green-50 text-green-700 px-1.5 py-0.5 rounded">{c.mpesa_reference}</span>
                  ) : "—"}
                </td>
                <td className="px-3 py-2.5 text-center">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${statusBadge(c.payment_status)}`}>
                    {c.payment_status}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex gap-2 justify-end">
                    {c.payment_status !== "PAID" && (
                      <button className="text-xs text-emerald-600 hover:underline" onClick={() => setMarkingId(markingId === c.id ? null : c.id)}>
                        Mark Paid
                      </button>
                    )}
                    <button className="text-xs text-red-400 hover:underline" onClick={() => onDelete(c.id)}>Del</button>
                  </div>
                </td>
              </tr>
              {markingId === c.id && (
                <tr key={`${c.id}-mark`} className="bg-emerald-50">
                  <td colSpan={8} className="px-3 py-2">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-medium text-gray-600">M-Pesa ref:</span>
                      <input className="border rounded px-2 py-1 text-xs w-36" placeholder="Receipt no." value={ref} onChange={(e) => setRef(e.target.value)} />
                      <span className="text-xs font-medium text-gray-600">Phone:</span>
                      <input className="border rounded px-2 py-1 text-xs w-32" placeholder="07XXXXXXXX" value={phone} onChange={(e) => setPhone(e.target.value)} />
                      <button
                        disabled={saving}
                        className="text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 px-3 py-1 rounded disabled:opacity-50"
                        onClick={() => { onMarkPaid(c.id, ref, phone); setMarkingId(null); setRef(""); setPhone(""); }}
                      >
                        Confirm Payment
                      </button>
                      <button className="text-xs text-gray-400 hover:underline" onClick={() => setMarkingId(null)}>Cancel</button>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NewLocalCostModal({ onClose, onSubmit, loading }: { onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const [form, setForm] = useState({
    cost_type: "TRANSPORT" as LocalCostType,
    description: "",
    vendor_name: "",
    amount_kes: "",
    payment_method: "MPESA" as LocalPaymentMethod,
    mpesa_phone: "",
    notes: "",
  });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h2 className="font-semibold text-lg">Add Local Logistics Cost</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Cost Type</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.cost_type} onChange={(e) => set("cost_type", e.target.value)}>
                {(Object.keys(COST_TYPE_LABELS) as LocalCostType[]).map((k) => (
                  <option key={k} value={k}>{COST_TYPE_LABELS[k]}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Payment Method</label>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.payment_method} onChange={(e) => set("payment_method", e.target.value)}>
                <option value="MPESA">📱 M-Pesa</option>
                <option value="BANK">🏦 Bank Transfer</option>
                <option value="CASH">💵 Cash</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.description} onChange={(e) => set("description", e.target.value)} placeholder="e.g. Mombasa–Nairobi truck, SGR rail freight" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Vendor / Service Provider</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.vendor_name} onChange={(e) => set("vendor_name", e.target.value)} placeholder="Company or person name" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Amount (KES)</label>
              <input type="number" className="w-full border rounded px-3 py-2 text-sm" value={form.amount_kes} onChange={(e) => set("amount_kes", e.target.value)} />
            </div>
          </div>
          {form.payment_method === "MPESA" && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">M-Pesa Phone (optional)</label>
              <input className="w-full border rounded px-3 py-2 text-sm" value={form.mpesa_phone} onChange={(e) => set("mpesa_phone", e.target.value)} placeholder="07XXXXXXXX" />
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={2} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({
            cost_type: form.cost_type,
            description: form.description,
            vendor_name: form.vendor_name || undefined,
            amount_kes: parseFloat(form.amount_kes),
            payment_method: form.payment_method,
            mpesa_phone: form.mpesa_phone || undefined,
            notes: form.notes || undefined,
          })}>Save</Button>
        </div>
      </div>
    </div>
  );
}

function NewClearanceModal({ shipmentId, onClose, onSubmit, loading }: { shipmentId: string; onClose: () => void; onSubmit: (d: object) => void; loading: boolean }) {
  const [form, setForm] = useState({ agent_name: "", entry_no: "", kra_pin: "" });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h2 className="font-semibold text-lg">Open Customs Clearance</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Clearing Agent</label>
            <input className="w-full border rounded px-3 py-2 text-sm" value={form.agent_name} onChange={(e) => set("agent_name", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">IDF / Entry No</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.entry_no} onChange={(e) => set("entry_no", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">KRA PIN</label>
            <input className="w-full border rounded px-3 py-2 text-sm font-mono" value={form.kra_pin} onChange={(e) => set("kra_pin", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={loading} onClick={() => onSubmit({ shipment_id: shipmentId, ...form })}>Create</Button>
        </div>
      </div>
    </div>
  );
}
