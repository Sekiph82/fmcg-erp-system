"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { wmsApi, ZoneType } from "@/lib/wms";
import { warehousesApi } from "@/lib/warehouses";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const ZONE_TYPES: { value: ZoneType; label: string }[] = [
  { value: "RAW_MATERIAL", label: "Raw Material" },
  { value: "SEMI_FINISHED", label: "Semi-Finished" },
  { value: "FINISHED_GOODS", label: "Finished Goods" },
  { value: "QUARANTINE", label: "Quarantine" },
  { value: "RETURNS", label: "Returns" },
  { value: "STAGING", label: "Staging" },
];

const zoneVariant = (t: ZoneType) =>
  t === "QUARANTINE" ? "red"
  : t === "FINISHED_GOODS" ? "green"
  : t === "RETURNS" ? "red"
  : "blue";

type Tab = "zones" | "locations" | "quarantine";

export default function WMSPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [tab, setTab] = useState<Tab>("zones");
  const [warehouseFilter, setWarehouseFilter] = useState("");
  const [zoneModal, setZoneModal] = useState(false);
  const [locModal, setLocModal] = useState(false);
  const [quarModal, setQuarModal] = useState(false);
  const [releaseModal, setReleaseModal] = useState(false);

  const [zoneForm, setZoneForm] = useState({ warehouse_id: "", code: "", name: "", zone_type: "RAW_MATERIAL" as ZoneType, is_active: true });
  const [locForm, setLocForm] = useState({ zone_id: "", code: "", name: "", barcode: "", is_active: true, is_blocked: false });
  const [quarForm, setQuarForm] = useState({ warehouse_id: "", lot_number: "", reason: "", notes: "" });
  const [releaseForm, setReleaseForm] = useState({ warehouse_id: "", lot_number: "", notes: "" });

  const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses"], queryFn: () => warehousesApi.list(0, 100) });
  const { data: zones = [], isLoading: loadingZones } = useQuery({
    queryKey: ["wms-zones", warehouseFilter],
    queryFn: () => wmsApi.listZones(warehouseFilter ? { warehouse_id: warehouseFilter } : undefined),
  });
  const { data: locations = [], isLoading: loadingLocs } = useQuery({
    queryKey: ["wms-locations", warehouseFilter],
    queryFn: () => wmsApi.listLocations(warehouseFilter ? { warehouse_id: warehouseFilter } : undefined),
  });

  const whOpts = [{ value: "", label: "All Warehouses" }, ...warehouses.map((w) => ({ value: w.id, label: w.name }))];
  const zoneOpts = [{ value: "", label: "Select zone…" }, ...zones.map((z) => ({ value: z.id, label: `${z.code} — ${z.name}` }))];

  const createZone = useMutation({
    mutationFn: () => wmsApi.createZone({ ...zoneForm }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["wms-zones"] }); setZoneModal(false); toast("success", "Zone created", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const createLoc = useMutation({
    mutationFn: () => wmsApi.createLocation({ ...locForm, barcode: locForm.barcode || undefined }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["wms-locations"] }); setLocModal(false); toast("success", "Location created", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const quarantine = useMutation({
    mutationFn: () => wmsApi.quarantine({ warehouse_id: quarForm.warehouse_id, lot_number: quarForm.lot_number || undefined, reason: quarForm.reason, notes: quarForm.notes || undefined }),
    onSuccess: (r: { blocked_rows: number }) => { setQuarModal(false); toast("success", "Quarantined", `${r.blocked_rows} stock row(s) blocked.`); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const releaseQuar = useMutation({
    mutationFn: () => wmsApi.releaseQuarantine({ warehouse_id: releaseForm.warehouse_id, lot_number: releaseForm.lot_number || undefined, notes: releaseForm.notes || undefined }),
    onSuccess: (r: { released_rows: number }) => { setReleaseModal(false); toast("success", "Released", `${r.released_rows} stock row(s) unblocked.`); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const TABS = [
    { key: "zones" as Tab, label: "Zones" },
    { key: "locations" as Tab, label: "Locations / Bins" },
    { key: "quarantine" as Tab, label: "Quarantine" },
  ];

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Warehouse Management</h1>
          <p className="text-sm text-gray-500 mt-1">{zones.length} zones · {locations.length} locations</p>
        </div>
        <div className="flex gap-2">
          {tab === "zones" && <Button onClick={() => setZoneModal(true)}>+ New Zone</Button>}
          {tab === "locations" && <Button onClick={() => setLocModal(true)}>+ New Location</Button>}
          {tab === "quarantine" && (
            <>
              <Button variant="secondary" onClick={() => setReleaseModal(true)}>Release</Button>
              <Button onClick={() => setQuarModal(true)}>Quarantine Stock</Button>
            </>
          )}
        </div>
      </div>

      {/* Filter + tabs */}
      <div className="mb-4 flex gap-3 items-center">
        <Select options={whOpts} value={warehouseFilter} onChange={(e) => setWarehouseFilter(e.target.value)} className="w-52" />
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${tab === t.key ? "bg-white shadow-sm text-gray-900" : "text-gray-500 hover:text-gray-700"}`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Zones tab */}
      {tab === "zones" && (
        loadingZones ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div> :
        <Table
          keyField="id"
          data={zones}
          emptyMessage="No zones yet. Create zones to organise your warehouse."
          columns={[
            { header: "Code", accessor: "code", className: "font-mono text-xs font-medium" },
            { header: "Name", accessor: "name" },
            { header: "Type", accessor: (z) => <Badge label={z.zone_type.replace(/_/g, " ")} variant={zoneVariant(z.zone_type)} /> },
            { header: "Warehouse", accessor: (z) => z.warehouse_name ?? "—" },
            { header: "Locations", accessor: (z) => z.location_count },
            { header: "Status", accessor: (z) => <Badge label={z.is_active ? "Active" : "Inactive"} variant={z.is_active ? "green" : "red"} /> },
          ]}
        />
      )}

      {/* Locations tab */}
      {tab === "locations" && (
        loadingLocs ? <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div> :
        <Table
          keyField="id"
          data={locations}
          emptyMessage="No locations yet."
          columns={[
            { header: "Code", accessor: "code", className: "font-mono text-xs font-medium" },
            { header: "Name", accessor: "name" },
            { header: "Zone", accessor: (l) => l.zone_name ? `${l.zone_code} — ${l.zone_name}` : "—" },
            { header: "Type", accessor: (l) => l.zone_type ? <Badge label={l.zone_type.replace(/_/g, " ")} variant={zoneVariant(l.zone_type)} /> : null },
            { header: "Warehouse", accessor: (l) => l.warehouse_name ?? "—" },
            { header: "Barcode", accessor: (l) => l.barcode ? <span className="font-mono text-xs">{l.barcode}</span> : "—" },
            {
              header: "Status",
              accessor: (l) => (
                <div className="flex gap-1">
                  {l.is_blocked && <Badge label="Blocked" variant="red" />}
                  {!l.is_blocked && <Badge label={l.is_active ? "Active" : "Inactive"} variant={l.is_active ? "green" : "red"} />}
                </div>
              ),
            },
          ]}
        />
      )}

      {/* Quarantine tab */}
      {tab === "quarantine" && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6">
          <h2 className="font-semibold text-amber-900 mb-2">Quarantine / Blocked Stock</h2>
          <p className="text-sm text-amber-700 mb-4">
            Quarantined stock is blocked from issue and transfer. Use "Quarantine Stock" to block a lot, and "Release" to unblock it after inspection.
          </p>
          <p className="text-sm text-gray-600">
            Blocked stock rows appear in the Inventory summary with <strong>is_blocked = true</strong> and zero available quantity.
            All quarantine/release actions are audited as ADJUSTMENT movements in the ledger.
          </p>
        </div>
      )}

      {/* Zone Modal */}
      <Modal open={zoneModal} onClose={() => setZoneModal(false)} title="New Warehouse Zone">
        <form onSubmit={(e) => { e.preventDefault(); createZone.mutate(); }} className="space-y-4">
          <Select label="Warehouse *" options={[{ value: "", label: "Select…" }, ...warehouses.map((w) => ({ value: w.id, label: w.name }))]}
            value={zoneForm.warehouse_id} onChange={(e) => setZoneForm((f) => ({ ...f, warehouse_id: e.target.value }))} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Code *" value={zoneForm.code} onChange={(e) => setZoneForm((f) => ({ ...f, code: e.target.value }))} placeholder="e.g. RM-A" required />
            <Input label="Name *" value={zoneForm.name} onChange={(e) => setZoneForm((f) => ({ ...f, name: e.target.value }))} required />
          </div>
          <Select label="Zone Type *" options={ZONE_TYPES} value={zoneForm.zone_type}
            onChange={(e) => setZoneForm((f) => ({ ...f, zone_type: e.target.value as ZoneType }))} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setZoneModal(false)}>Cancel</Button>
            <Button type="submit" loading={createZone.isPending} disabled={!zoneForm.warehouse_id || !zoneForm.code || !zoneForm.name}>Create Zone</Button>
          </div>
        </form>
      </Modal>

      {/* Location Modal */}
      <Modal open={locModal} onClose={() => setLocModal(false)} title="New Storage Location">
        <form onSubmit={(e) => { e.preventDefault(); createLoc.mutate(); }} className="space-y-4">
          <Select label="Zone *" options={zoneOpts} value={locForm.zone_id} onChange={(e) => setLocForm((f) => ({ ...f, zone_id: e.target.value }))} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Code *" value={locForm.code} onChange={(e) => setLocForm((f) => ({ ...f, code: e.target.value }))} placeholder="e.g. A-01-01" required />
            <Input label="Name *" value={locForm.name} onChange={(e) => setLocForm((f) => ({ ...f, name: e.target.value }))} required />
          </div>
          <Input label="Barcode (for scanning)" value={locForm.barcode} onChange={(e) => setLocForm((f) => ({ ...f, barcode: e.target.value }))} placeholder="e.g. LOC-A0101" />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setLocModal(false)}>Cancel</Button>
            <Button type="submit" loading={createLoc.isPending} disabled={!locForm.zone_id || !locForm.code || !locForm.name}>Create Location</Button>
          </div>
        </form>
      </Modal>

      {/* Quarantine Modal */}
      <Modal open={quarModal} onClose={() => setQuarModal(false)} title="Quarantine Stock">
        <form onSubmit={(e) => { e.preventDefault(); quarantine.mutate(); }} className="space-y-4">
          <Select label="Warehouse *" options={[{ value: "", label: "Select…" }, ...warehouses.map((w) => ({ value: w.id, label: w.name }))]}
            value={quarForm.warehouse_id} onChange={(e) => setQuarForm((f) => ({ ...f, warehouse_id: e.target.value }))} />
          <Input label="Lot Number (optional)" value={quarForm.lot_number} onChange={(e) => setQuarForm((f) => ({ ...f, lot_number: e.target.value }))} placeholder="Leave blank to block all stock in warehouse" />
          <Input label="Reason *" value={quarForm.reason} onChange={(e) => setQuarForm((f) => ({ ...f, reason: e.target.value }))} placeholder="e.g. Failed QC, Contamination suspected" required />
          <Input label="Notes" value={quarForm.notes} onChange={(e) => setQuarForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-700">
            This will block the stock from issue and transfer. An audit trail movement will be recorded.
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setQuarModal(false)}>Cancel</Button>
            <Button type="submit" loading={quarantine.isPending} disabled={!quarForm.warehouse_id || !quarForm.reason}>Quarantine</Button>
          </div>
        </form>
      </Modal>

      {/* Release Modal */}
      <Modal open={releaseModal} onClose={() => setReleaseModal(false)} title="Release from Quarantine">
        <form onSubmit={(e) => { e.preventDefault(); releaseQuar.mutate(); }} className="space-y-4">
          <Select label="Warehouse *" options={[{ value: "", label: "Select…" }, ...warehouses.map((w) => ({ value: w.id, label: w.name }))]}
            value={releaseForm.warehouse_id} onChange={(e) => setReleaseForm((f) => ({ ...f, warehouse_id: e.target.value }))} />
          <Input label="Lot Number (optional)" value={releaseForm.lot_number} onChange={(e) => setReleaseForm((f) => ({ ...f, lot_number: e.target.value }))} />
          <Input label="Release Notes" value={releaseForm.notes} onChange={(e) => setReleaseForm((f) => ({ ...f, notes: e.target.value }))} placeholder="e.g. QC passed, cleared for use" />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setReleaseModal(false)}>Cancel</Button>
            <Button type="submit" loading={releaseQuar.isPending} disabled={!releaseForm.warehouse_id}>Release</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
