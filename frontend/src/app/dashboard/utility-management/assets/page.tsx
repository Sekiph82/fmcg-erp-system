"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  utilityManagementApi,
  UtilityAsset,
  UtilityAssetCreate,
  UtilityAssetUpdate,
  UtilityAssetCategory,
  UtilityType,
  UtilityAssetStatus,
  LifecycleStatus,
  CriticalityLevel,
  UTILITY_TYPE_OPTIONS,
  UTILITY_TYPE_LABELS,
  ASSET_STATUS_OPTIONS,
  ASSET_STATUS_LABELS,
  LIFECYCLE_STATUS_OPTIONS,
  LIFECYCLE_STATUS_LABELS,
  CRITICALITY_OPTIONS,
  CRITICALITY_LABELS,
  downloadAuthenticatedCsv,
} from "@/lib/utilityManagement";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { ImportModal } from "@/components/import/ImportModal";
import { RequirePermission } from "@/components/PermissionGuard";

// ── Helpers ────────────────────────────────────────────────────────────────────

const EMPTY_CREATE: UtilityAssetCreate = {
  asset_no: "",
  name: "",
  category_id: "",
  utility_type: "ELECTRICITY",
  status: "ACTIVE",
  is_active: true,
};

function statusVariant(s: UtilityAssetStatus): "green" | "yellow" | "red" | "gray" {
  if (s === "ACTIVE") return "green";
  if (s === "IDLE") return "yellow";
  if (s === "UNDER_MAINTENANCE") return "yellow";
  return "gray";
}

function criticalityVariant(c: CriticalityLevel | null): "red" | "yellow" | "blue" | "gray" {
  if (!c) return "gray";
  if (c === "CRITICAL") return "red";
  if (c === "HIGH") return "yellow";
  if (c === "MEDIUM") return "blue";
  return "gray";
}

// ── Form section component ────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="col-span-2 border-t border-gray-100 pt-4 pb-1">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
        {children}
      </h3>
    </div>
  );
}

// ── Detail view ───────────────────────────────────────────────────────────────

function AssetDetailView({ asset, onClose }: { asset: UtilityAsset; onClose: () => void }) {
  const rows: [string, string | null | undefined][] = [
    ["Asset Code", asset.asset_no],
    ["Name", asset.name],
    ["Category", asset.category_name ? `${asset.category_name} (${asset.category_code})` : asset.category_code],
    ["Utility Type", UTILITY_TYPE_LABELS[asset.utility_type]],
    ["Operating Status", ASSET_STATUS_LABELS[asset.status]],
    ["Lifecycle Status", asset.lifecycle_status ? LIFECYCLE_STATUS_LABELS[asset.lifecycle_status] : null],
    ["Criticality", asset.criticality_level ? CRITICALITY_LABELS[asset.criticality_level] : null],
    ["Subsystem", asset.subsystem],
    ["Location", asset.location],
    ["Department", asset.department],
    ["Building/Area", asset.building_area],
    ["Line ID", asset.line_id],
    ["Machine ID", asset.machine_id],
    ["Parent Asset", asset.parent_asset_no],
    ["Manufacturer", asset.manufacturer],
    ["Model", asset.equipment_model],
    ["Serial No.", asset.serial_no],
    ["Install/Commission Date", asset.install_date],
    ["Warranty Expiry", asset.warranty_expiry],
    ["Rated Capacity", asset.rated_capacity ? `${asset.rated_capacity} ${asset.capacity_unit ?? ""}`.trim() : null],
    ["Rated Power", asset.rated_power ? `${asset.rated_power} ${asset.rated_power_unit ?? ""}`.trim() : null],
    ["Flow Capacity", asset.flow_capacity ? String(asset.flow_capacity) : null],
    ["Pressure Capacity", asset.pressure_capacity ? String(asset.pressure_capacity) : null],
    ["Temperature Range", asset.temperature_range],
    ["Maintenance Strategy", asset.maintenance_strategy],
    ["Notes", asset.notes],
  ];
  return (
    <div className="space-y-1">
      <dl className="divide-y divide-gray-100">
        {rows.map(([label, value]) =>
          value ? (
            <div key={label} className="grid grid-cols-5 py-2 gap-2">
              <dt className="col-span-2 text-xs font-medium text-gray-500">{label}</dt>
              <dd className="col-span-3 text-sm text-gray-900">{value}</dd>
            </div>
          ) : null
        )}
      </dl>
      <div className="flex justify-end pt-4">
        <Button variant="secondary" onClick={onClose}>Close</Button>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function UtilityAssetsPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  // Filters
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<UtilityType | "">("");
  const [filterCategoryId, setFilterCategoryId] = useState("");
  const [filterStatus, setFilterStatus] = useState<UtilityAssetStatus | "">("");
  const [filterLifecycle, setFilterLifecycle] = useState<LifecycleStatus | "">("");
  const [filterCriticality, setFilterCriticality] = useState<CriticalityLevel | "">("");
  const [filterDepartment, setFilterDepartment] = useState("");

  // Modals
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<UtilityAssetCreate>(EMPTY_CREATE);
  const [editTarget, setEditTarget] = useState<UtilityAsset | null>(null);
  const [editForm, setEditForm] = useState<UtilityAssetUpdate>({});
  const [deleteTarget, setDeleteTarget] = useState<UtilityAsset | null>(null);
  const [viewTarget, setViewTarget] = useState<UtilityAsset | null>(null);

  // Data
  const { data: categories = [] } = useQuery({
    queryKey: ["utility-management", "categories"],
    queryFn: () => utilityManagementApi.categories.list({ is_active: true, limit: 500 }),
  });

  const categoryOptions = [
    { value: "", label: "All categories" },
    ...categories.map((c: UtilityAssetCategory) => ({ value: c.id, label: `${c.code} — ${c.name}` })),
  ];

  const { data: assets = [], isLoading } = useQuery({
    queryKey: [
      "utility-management", "assets",
      filterType, filterCategoryId, filterStatus, filterLifecycle,
      filterCriticality, filterDepartment,
    ],
    queryFn: () =>
      utilityManagementApi.assets.list({
        utility_type: filterType || undefined,
        category_id: filterCategoryId || undefined,
        status: filterStatus || undefined,
        lifecycle_status: filterLifecycle || undefined,
        criticality_level: filterCriticality || undefined,
        department: filterDepartment || undefined,
        limit: 500,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data: UtilityAssetCreate) => utilityManagementApi.assets.create(data),
    onSuccess: (asset) => {
      qc.invalidateQueries({ queryKey: ["utility-management", "assets"] });
      setCreateOpen(false);
      setForm(EMPTY_CREATE);
      toast("success", "Asset created", `${asset.name} (${asset.asset_no}) added.`);
    },
    onError: (err) => toast("error", "Failed to create", extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UtilityAssetUpdate }) =>
      utilityManagementApi.assets.update(id, data),
    onSuccess: (asset) => {
      qc.invalidateQueries({ queryKey: ["utility-management", "assets"] });
      setEditTarget(null);
      toast("success", "Asset updated", `${asset.name} saved.`);
    },
    onError: (err) => toast("error", "Failed to update", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilityManagementApi.assets.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utility-management", "assets"] });
      setDeleteTarget(null);
      toast("success", "Asset deleted");
    },
    onError: (err) => toast("error", "Cannot delete", extractApiError(err)),
  });

  const openEdit = (asset: UtilityAsset) => {
    setEditTarget(asset);
    setEditForm({
      name: asset.name,
      description: asset.description ?? "",
      category_id: asset.category_id,
      utility_type: asset.utility_type,
      subsystem: asset.subsystem ?? "",
      location: asset.location ?? "",
      building_area: asset.building_area ?? "",
      department: asset.department ?? "",
      line_id: asset.line_id ?? "",
      machine_id: asset.machine_id ?? "",
      parent_asset_id: asset.parent_asset_id ?? null,
      manufacturer: asset.manufacturer ?? "",
      equipment_model: asset.equipment_model ?? "",
      serial_no: asset.serial_no ?? "",
      install_date: asset.install_date ?? null,
      warranty_expiry: asset.warranty_expiry ?? null,
      rated_capacity: asset.rated_capacity ?? null,
      capacity_unit: asset.capacity_unit ?? "",
      rated_power: asset.rated_power ?? null,
      rated_power_unit: asset.rated_power_unit ?? "",
      flow_capacity: asset.flow_capacity ?? null,
      pressure_capacity: asset.pressure_capacity ?? null,
      temperature_range: asset.temperature_range ?? "",
      status: asset.status,
      lifecycle_status: asset.lifecycle_status ?? null,
      criticality_level: asset.criticality_level ?? null,
      maintenance_strategy: asset.maintenance_strategy ?? "",
      is_active: asset.is_active,
      notes: asset.notes ?? "",
    });
  };

  const filteredAssets = assets.filter((a) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      a.asset_no.toLowerCase().includes(s) ||
      a.name.toLowerCase().includes(s) ||
      (a.department ?? "").toLowerCase().includes(s)
    );
  });

  const handleExport = async () => {
    try {
      await downloadAuthenticatedCsv(
        "/api/v1/utility-management/assets/export/csv",
        "utility_assets.csv",
      );
    } catch {
      toast("error", "Export failed");
    }
  };

  // Form helpers
  const setF = (k: keyof UtilityAssetCreate, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v }));
  const setE = (k: keyof UtilityAssetUpdate, v: unknown) =>
    setEditForm((f) => ({ ...f, [k]: v }));

  return (
    <RequirePermission permission="utility_management.view">
      <div>
        <ToastContainer toasts={toasts} onDismiss={dismiss} />

        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Utility Assets</h1>
            <p className="text-sm text-gray-500 mt-1">
              {assets.length} assets registered &nbsp;·&nbsp; Boilers, compressors, meters, solar, WWTP and more
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={handleExport}>Export CSV</Button>
            <ImportModal
              module="utility_assets"
              onSuccess={() => qc.invalidateQueries({ queryKey: ["utility-management", "assets"] })}
            />
            <Button onClick={() => setCreateOpen(true)}>+ Add Asset</Button>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Input
            placeholder="Search code, name, dept…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select
            label=""
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as UtilityType | "")}
            options={[{ value: "", label: "All types" }, ...UTILITY_TYPE_OPTIONS]}
          />
          <Select
            label=""
            value={filterCategoryId}
            onChange={(e) => setFilterCategoryId(e.target.value)}
            options={categoryOptions}
          />
          <Select
            label=""
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as UtilityAssetStatus | "")}
            options={[{ value: "", label: "All statuses" }, ...ASSET_STATUS_OPTIONS]}
          />
          <Select
            label=""
            value={filterLifecycle}
            onChange={(e) => setFilterLifecycle(e.target.value as LifecycleStatus | "")}
            options={[{ value: "", label: "All lifecycle" }, ...LIFECYCLE_STATUS_OPTIONS]}
          />
          <Select
            label=""
            value={filterCriticality}
            onChange={(e) => setFilterCriticality(e.target.value as CriticalityLevel | "")}
            options={[{ value: "", label: "All criticality" }, ...CRITICALITY_OPTIONS]}
          />
          <Input
            placeholder="Department…"
            value={filterDepartment}
            onChange={(e) => setFilterDepartment(e.target.value)}
            className="max-w-[140px]"
          />
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        ) : (
          <Table
            keyField="id"
            data={filteredAssets}
            emptyMessage={
              search ? "No assets match your search." : "No utility assets registered yet."
            }
            columns={[
              {
                header: "Asset Code",
                accessor: (r) => (
                  <span className="font-mono text-xs font-semibold">{r.asset_no}</span>
                ),
              },
              { header: "Name", accessor: "name" },
              {
                header: "Category",
                accessor: (r) =>
                  r.category_code ? (
                    <span className="text-xs text-gray-600">{r.category_code}</span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  ),
              },
              {
                header: "Utility Type",
                accessor: (r) => (
                  <Badge label={UTILITY_TYPE_LABELS[r.utility_type]} variant="blue" />
                ),
              },
              {
                header: "Status",
                accessor: (r) => (
                  <Badge label={ASSET_STATUS_LABELS[r.status]} variant={statusVariant(r.status)} />
                ),
              },
              {
                header: "Criticality",
                accessor: (r) =>
                  r.criticality_level ? (
                    <Badge
                      label={CRITICALITY_LABELS[r.criticality_level]}
                      variant={criticalityVariant(r.criticality_level)}
                    />
                  ) : (
                    <span className="text-gray-400">—</span>
                  ),
              },
              {
                header: "Dept / Area",
                accessor: (r) => (
                  <span className="text-xs text-gray-600">
                    {[r.department, r.building_area].filter(Boolean).join(" · ") || "—"}
                  </span>
                ),
              },
              {
                header: "",
                accessor: (r) => (
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setViewTarget(r)}
                      className="text-xs text-gray-500 hover:text-gray-800 hover:underline"
                    >
                      View
                    </button>
                    <button
                      onClick={() => openEdit(r)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => setDeleteTarget(r)}
                      className="text-xs text-red-500 hover:text-red-700 hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                ),
              },
            ]}
          />
        )}

        {/* Detail View Modal */}
        <Modal
          open={!!viewTarget}
          onClose={() => setViewTarget(null)}
          title={viewTarget ? `${viewTarget.asset_no} — ${viewTarget.name}` : ""}
        >
          {viewTarget && (
            <AssetDetailView asset={viewTarget} onClose={() => setViewTarget(null)} />
          )}
        </Modal>

        {/* Create Modal */}
        <Modal
          open={createOpen}
          onClose={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}
          title="Add Utility Asset"
        >
          <form
            onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Identity</SectionTitle>
              <Input
                label="Asset Code *"
                value={form.asset_no}
                onChange={(e) => setF("asset_no", e.target.value.toUpperCase())}
                placeholder="e.g. BLR-001"
                required
              />
              <Input
                label="Asset Name *"
                value={form.name}
                onChange={(e) => setF("name", e.target.value)}
                required
              />
              <Select
                label="Category *"
                value={form.category_id}
                onChange={(e) => setF("category_id", e.target.value)}
                options={[
                  { value: "", label: "— Select category —" },
                  ...categories.map((c: UtilityAssetCategory) => ({
                    value: c.id,
                    label: `${c.code} — ${c.name}`,
                  })),
                ]}
              />
              <Select
                label="Utility Type *"
                value={form.utility_type}
                onChange={(e) => setF("utility_type", e.target.value as UtilityType)}
                options={UTILITY_TYPE_OPTIONS}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Location</SectionTitle>
              <Input
                label="Location"
                value={form.location ?? ""}
                onChange={(e) => setF("location", e.target.value || null)}
                placeholder="e.g. Boiler House"
              />
              <Input
                label="Building / Area"
                value={form.building_area ?? ""}
                onChange={(e) => setF("building_area", e.target.value || null)}
              />
              <Input
                label="Department"
                value={form.department ?? ""}
                onChange={(e) => setF("department", e.target.value || null)}
              />
              <Input
                label="Subsystem"
                value={form.subsystem ?? ""}
                onChange={(e) => setF("subsystem", e.target.value || null)}
                placeholder="e.g. Cooling Loop"
              />
              <Input
                label="Line ID"
                value={form.line_id ?? ""}
                onChange={(e) => setF("line_id", e.target.value || null)}
                placeholder="Production line code"
              />
              <Input
                label="Machine ID"
                value={form.machine_id ?? ""}
                onChange={(e) => setF("machine_id", e.target.value || null)}
                placeholder="Machine/equipment code"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Equipment Details</SectionTitle>
              <Input
                label="Manufacturer"
                value={form.manufacturer ?? ""}
                onChange={(e) => setF("manufacturer", e.target.value || null)}
              />
              <Input
                label="Model"
                value={form.equipment_model ?? ""}
                onChange={(e) => setF("equipment_model", e.target.value || null)}
              />
              <Input
                label="Serial No."
                value={form.serial_no ?? ""}
                onChange={(e) => setF("serial_no", e.target.value || null)}
              />
              <Input
                label="Install / Commission Date"
                type="date"
                value={form.install_date ?? ""}
                onChange={(e) => setF("install_date", e.target.value || null)}
              />
              <Input
                label="Warranty Expiry"
                type="date"
                value={form.warranty_expiry ?? ""}
                onChange={(e) => setF("warranty_expiry", e.target.value || null)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Capacity & Rating</SectionTitle>
              <Input
                label="Rated Capacity"
                type="number"
                step="any"
                value={form.rated_capacity ?? ""}
                onChange={(e) => setF("rated_capacity", e.target.value || null)}
              />
              <Input
                label="Capacity Unit"
                value={form.capacity_unit ?? ""}
                onChange={(e) => setF("capacity_unit", e.target.value || null)}
                placeholder="e.g. kW, kg/h, m³/h"
              />
              <Input
                label="Rated Power"
                type="number"
                step="any"
                value={form.rated_power ?? ""}
                onChange={(e) => setF("rated_power", e.target.value || null)}
              />
              <Input
                label="Power Unit"
                value={form.rated_power_unit ?? ""}
                onChange={(e) => setF("rated_power_unit", e.target.value || null)}
                placeholder="e.g. kW, kVA"
              />
              <Input
                label="Flow Capacity"
                type="number"
                step="any"
                value={form.flow_capacity ?? ""}
                onChange={(e) => setF("flow_capacity", e.target.value || null)}
              />
              <Input
                label="Pressure Capacity"
                type="number"
                step="any"
                value={form.pressure_capacity ?? ""}
                onChange={(e) => setF("pressure_capacity", e.target.value || null)}
              />
              <Input
                label="Temperature Range"
                value={form.temperature_range ?? ""}
                onChange={(e) => setF("temperature_range", e.target.value || null)}
                placeholder="e.g. -10°C to 60°C"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Classification</SectionTitle>
              <Select
                label="Operating Status"
                value={form.status ?? "ACTIVE"}
                onChange={(e) => setF("status", e.target.value as UtilityAssetStatus)}
                options={ASSET_STATUS_OPTIONS}
              />
              <Select
                label="Lifecycle Status"
                value={form.lifecycle_status ?? ""}
                onChange={(e) => setF("lifecycle_status", e.target.value as LifecycleStatus || null)}
                options={[{ value: "", label: "— None —" }, ...LIFECYCLE_STATUS_OPTIONS]}
              />
              <Select
                label="Criticality Level"
                value={form.criticality_level ?? ""}
                onChange={(e) => setF("criticality_level", e.target.value as CriticalityLevel || null)}
                options={[{ value: "", label: "— None —" }, ...CRITICALITY_OPTIONS]}
              />
              <Input
                label="Maintenance Strategy"
                value={form.maintenance_strategy ?? ""}
                onChange={(e) => setF("maintenance_strategy", e.target.value || null)}
                placeholder="e.g. Predictive, Preventive"
              />
            </div>

            <Input
              label="Notes"
              value={form.notes ?? ""}
              onChange={(e) => setF("notes", e.target.value || null)}
              placeholder="Optional notes"
            />

            <div className="flex items-center gap-2">
              <input
                id="create-active"
                type="checkbox"
                checked={form.is_active ?? true}
                onChange={(e) => setF("is_active", e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600"
              />
              <label htmlFor="create-active" className="text-sm text-gray-700">Active</label>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}>
                Cancel
              </Button>
              <Button
                type="submit"
                loading={createMutation.isPending}
                disabled={!form.asset_no || !form.name || !form.category_id}
              >
                Create Asset
              </Button>
            </div>
          </form>
        </Modal>

        {/* Edit Modal */}
        <Modal
          open={!!editTarget}
          onClose={() => setEditTarget(null)}
          title={`Edit Asset — ${editTarget?.asset_no}`}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (editTarget) updateMutation.mutate({ id: editTarget.id, data: editForm });
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Identity</SectionTitle>
              <Input
                label="Asset Name *"
                value={editForm.name ?? ""}
                onChange={(e) => setE("name", e.target.value)}
                required
              />
              <Select
                label="Category *"
                value={editForm.category_id ?? ""}
                onChange={(e) => setE("category_id", e.target.value)}
                options={[
                  { value: "", label: "— Select category —" },
                  ...categories.map((c: UtilityAssetCategory) => ({
                    value: c.id,
                    label: `${c.code} — ${c.name}`,
                  })),
                ]}
              />
              <Select
                label="Utility Type"
                value={editForm.utility_type ?? "ELECTRICITY"}
                onChange={(e) => setE("utility_type", e.target.value as UtilityType)}
                options={UTILITY_TYPE_OPTIONS}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Location</SectionTitle>
              <Input label="Location" value={editForm.location ?? ""} onChange={(e) => setE("location", e.target.value || null)} />
              <Input label="Building / Area" value={editForm.building_area ?? ""} onChange={(e) => setE("building_area", e.target.value || null)} />
              <Input label="Department" value={editForm.department ?? ""} onChange={(e) => setE("department", e.target.value || null)} />
              <Input label="Subsystem" value={editForm.subsystem ?? ""} onChange={(e) => setE("subsystem", e.target.value || null)} />
              <Input label="Line ID" value={editForm.line_id ?? ""} onChange={(e) => setE("line_id", e.target.value || null)} />
              <Input label="Machine ID" value={editForm.machine_id ?? ""} onChange={(e) => setE("machine_id", e.target.value || null)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Equipment Details</SectionTitle>
              <Input label="Manufacturer" value={editForm.manufacturer ?? ""} onChange={(e) => setE("manufacturer", e.target.value || null)} />
              <Input label="Model" value={editForm.equipment_model ?? ""} onChange={(e) => setE("equipment_model", e.target.value || null)} />
              <Input label="Serial No." value={editForm.serial_no ?? ""} onChange={(e) => setE("serial_no", e.target.value || null)} />
              <Input label="Install / Commission Date" type="date" value={editForm.install_date ?? ""} onChange={(e) => setE("install_date", e.target.value || null)} />
              <Input label="Warranty Expiry" type="date" value={editForm.warranty_expiry ?? ""} onChange={(e) => setE("warranty_expiry", e.target.value || null)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Capacity & Rating</SectionTitle>
              <Input label="Rated Capacity" type="number" step="any" value={editForm.rated_capacity ?? ""} onChange={(e) => setE("rated_capacity", e.target.value || null)} />
              <Input label="Capacity Unit" value={editForm.capacity_unit ?? ""} onChange={(e) => setE("capacity_unit", e.target.value || null)} />
              <Input label="Rated Power" type="number" step="any" value={editForm.rated_power ?? ""} onChange={(e) => setE("rated_power", e.target.value || null)} />
              <Input label="Power Unit" value={editForm.rated_power_unit ?? ""} onChange={(e) => setE("rated_power_unit", e.target.value || null)} />
              <Input label="Flow Capacity" type="number" step="any" value={editForm.flow_capacity ?? ""} onChange={(e) => setE("flow_capacity", e.target.value || null)} />
              <Input label="Pressure Capacity" type="number" step="any" value={editForm.pressure_capacity ?? ""} onChange={(e) => setE("pressure_capacity", e.target.value || null)} />
              <Input label="Temperature Range" value={editForm.temperature_range ?? ""} onChange={(e) => setE("temperature_range", e.target.value || null)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>Classification</SectionTitle>
              <Select
                label="Operating Status"
                value={editForm.status ?? "ACTIVE"}
                onChange={(e) => setE("status", e.target.value as UtilityAssetStatus)}
                options={ASSET_STATUS_OPTIONS}
              />
              <Select
                label="Lifecycle Status"
                value={editForm.lifecycle_status ?? ""}
                onChange={(e) => setE("lifecycle_status", e.target.value as LifecycleStatus || null)}
                options={[{ value: "", label: "— None —" }, ...LIFECYCLE_STATUS_OPTIONS]}
              />
              <Select
                label="Criticality Level"
                value={editForm.criticality_level ?? ""}
                onChange={(e) => setE("criticality_level", e.target.value as CriticalityLevel || null)}
                options={[{ value: "", label: "— None —" }, ...CRITICALITY_OPTIONS]}
              />
              <Input
                label="Maintenance Strategy"
                value={editForm.maintenance_strategy ?? ""}
                onChange={(e) => setE("maintenance_strategy", e.target.value || null)}
              />
            </div>

            <Input
              label="Notes"
              value={editForm.notes ?? ""}
              onChange={(e) => setE("notes", e.target.value || null)}
            />

            <div className="flex items-center gap-2">
              <input
                id="edit-active"
                type="checkbox"
                checked={editForm.is_active ?? true}
                onChange={(e) => setE("is_active", e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600"
              />
              <label htmlFor="edit-active" className="text-sm text-gray-700">Active</label>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => setEditTarget(null)}>Cancel</Button>
              <Button type="submit" loading={updateMutation.isPending}>Save Changes</Button>
            </div>
          </form>
        </Modal>

        {/* Delete Confirm Modal */}
        <Modal
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          title="Delete Utility Asset"
        >
          <p className="text-sm text-gray-600 mb-4">
            Delete asset{" "}
            <span className="font-semibold">{deleteTarget?.name}</span>{" "}
            <span className="font-mono text-xs text-gray-500">({deleteTarget?.asset_no})</span>?
            This cannot be undone. Readings, transactions and other records referencing this asset will be unlinked.
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button
              variant="danger"
              loading={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              Delete
            </Button>
          </div>
        </Modal>
      </div>
    </RequirePermission>
  );
}
