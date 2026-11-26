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
import { tx } from "@/lib/i18n/core";

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
    [tx("Asset Code"), asset.asset_no],
    [tx("Name"), asset.name],
    [tx("Category"), asset.category_name ? `${asset.category_name} (${asset.category_code})` : asset.category_code],
    [tx("Utility Type"), UTILITY_TYPE_LABELS[asset.utility_type]],
    [tx("Operating Status"), ASSET_STATUS_LABELS[asset.status]],
    [tx("Lifecycle Status"), asset.lifecycle_status ? LIFECYCLE_STATUS_LABELS[asset.lifecycle_status] : null],
    [tx("Criticality"), asset.criticality_level ? CRITICALITY_LABELS[asset.criticality_level] : null],
    [tx("Subsystem"), asset.subsystem],
    [tx("Location"), asset.location],
    [tx("Department"), asset.department],
    [tx("Building/Area"), asset.building_area],
    [tx("Line ID"), asset.line_id],
    [tx("Machine ID"), asset.machine_id],
    [tx("Parent Asset"), asset.parent_asset_no],
    [tx("Manufacturer"), asset.manufacturer],
    [tx("Model"), asset.equipment_model],
    [tx("Serial No."), asset.serial_no],
    [tx("Install/Commission Date"), asset.install_date],
    [tx("Warranty Expiry"), asset.warranty_expiry],
    [tx("Rated Capacity"), asset.rated_capacity ? `${asset.rated_capacity} ${asset.capacity_unit ?? ""}`.trim() : null],
    [tx("Rated Power"), asset.rated_power ? `${asset.rated_power} ${asset.rated_power_unit ?? ""}`.trim() : null],
    [tx("Flow Capacity"), asset.flow_capacity ? String(asset.flow_capacity) : null],
    [tx("Pressure Capacity"), asset.pressure_capacity ? String(asset.pressure_capacity) : null],
    [tx("Temperature Range"), asset.temperature_range],
    [tx("Maintenance Strategy"), asset.maintenance_strategy],
    [tx("Notes"), asset.notes],
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
        <Button variant="secondary" onClick={onClose}>{tx("Close")}</Button>
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
    { value: "", label: tx("All categories") },
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
      toast("success", tx("Asset created"), tx("{name} ({asset_no}) added.", { name: asset.name, asset_no: asset.asset_no }));
    },
    onError: (err) => toast("error", tx("Failed to create"), extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UtilityAssetUpdate }) =>
      utilityManagementApi.assets.update(id, data),
    onSuccess: (asset) => {
      qc.invalidateQueries({ queryKey: ["utility-management", "assets"] });
      setEditTarget(null);
      toast("success", tx("Asset updated"), tx("{name} saved.", { name: asset.name }));
    },
    onError: (err) => toast("error", tx("Failed to update"), extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilityManagementApi.assets.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utility-management", "assets"] });
      setDeleteTarget(null);
      toast("success", tx("Asset deleted"));
    },
    onError: (err) => toast("error", tx("Cannot delete"), extractApiError(err)),
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
      toast("error", tx("Export failed"));
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
            <h1 className="text-2xl font-bold text-gray-900">{tx("Utility Assets")}</h1>
            <p className="text-sm text-gray-500 mt-1">
              {assets.length} assets registered &nbsp;·&nbsp; Boilers, compressors, meters, solar, WWTP and more
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={handleExport}>{tx("Export CSV")}</Button>
            <ImportModal
              module="utility_assets"
              onSuccess={() => qc.invalidateQueries({ queryKey: ["utility-management", "assets"] })}
            />
            <Button onClick={() => setCreateOpen(true)}>{tx("+ Add Asset")}</Button>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Input
            placeholder={tx("Search code, name, dept…")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select
            label=""
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as UtilityType | "")}
            options={[{ value: "", label: tx("All types") }, ...UTILITY_TYPE_OPTIONS]}
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
            options={[{ value: "", label: tx("All statuses") }, ...ASSET_STATUS_OPTIONS]}
          />
          <Select
            label=""
            value={filterLifecycle}
            onChange={(e) => setFilterLifecycle(e.target.value as LifecycleStatus | "")}
            options={[{ value: "", label: tx("All lifecycle") }, ...LIFECYCLE_STATUS_OPTIONS]}
          />
          <Select
            label=""
            value={filterCriticality}
            onChange={(e) => setFilterCriticality(e.target.value as CriticalityLevel | "")}
            options={[{ value: "", label: tx("All criticality") }, ...CRITICALITY_OPTIONS]}
          />
          <Input
            placeholder={tx("Department…")}
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
              search ? tx("No assets match your search.") : tx("No utility assets registered yet.")
            }
            columns={[
              {
                header: tx("Asset Code"),
                accessor: (r) => (
                  <span className="font-mono text-xs font-semibold">{r.asset_no}</span>
                ),
              },
              { header: tx("Name"), accessor: "name" },
              {
                header: tx("Category"),
                accessor: (r) =>
                  r.category_code ? (
                    <span className="text-xs text-gray-600">{r.category_code}</span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  ),
              },
              {
                header: tx("Utility Type"),
                accessor: (r) => (
                  <Badge label={UTILITY_TYPE_LABELS[r.utility_type]} variant="blue" />
                ),
              },
              {
                header: tx("Status"),
                accessor: (r) => (
                  <Badge label={ASSET_STATUS_LABELS[r.status]} variant={statusVariant(r.status)} />
                ),
              },
              {
                header: tx("Criticality"),
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
                header: tx("Dept / Area"),
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
                      {tx("View")}
                    </button>
                    <button
                      onClick={() => openEdit(r)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
                    >
                      {tx("Edit")}
                    </button>
                    <button
                      onClick={() => setDeleteTarget(r)}
                      className="text-xs text-red-500 hover:text-red-700 hover:underline"
                    >
                      {tx("Delete")}
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
          title={tx("Add Utility Asset")}
        >
          <form
            onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Identity")}</SectionTitle>
              <Input
                label={tx("Asset Code *")}
                value={form.asset_no}
                onChange={(e) => setF("asset_no", e.target.value.toUpperCase())}
                placeholder={tx("e.g. BLR-001")}
                required
              />
              <Input
                label={tx("Asset Name *")}
                value={form.name}
                onChange={(e) => setF("name", e.target.value)}
                required
              />
              <Select
                label={tx("Category *")}
                value={form.category_id}
                onChange={(e) => setF("category_id", e.target.value)}
                options={[
                  { value: "", label: tx("— Select category —") },
                  ...categories.map((c: UtilityAssetCategory) => ({
                    value: c.id,
                    label: `${c.code} — ${c.name}`,
                  })),
                ]}
              />
              <Select
                label={tx("Utility Type *")}
                value={form.utility_type}
                onChange={(e) => setF("utility_type", e.target.value as UtilityType)}
                options={UTILITY_TYPE_OPTIONS}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Location")}</SectionTitle>
              <Input
                label={tx("Location")}
                value={form.location ?? ""}
                onChange={(e) => setF("location", e.target.value || null)}
                placeholder={tx("e.g. Boiler House")}
              />
              <Input
                label={tx("Building / Area")}
                value={form.building_area ?? ""}
                onChange={(e) => setF("building_area", e.target.value || null)}
              />
              <Input
                label={tx("Department")}
                value={form.department ?? ""}
                onChange={(e) => setF("department", e.target.value || null)}
              />
              <Input
                label={tx("Subsystem")}
                value={form.subsystem ?? ""}
                onChange={(e) => setF("subsystem", e.target.value || null)}
                placeholder={tx("e.g. Cooling Loop")}
              />
              <Input
                label={tx("Line ID")}
                value={form.line_id ?? ""}
                onChange={(e) => setF("line_id", e.target.value || null)}
                placeholder={tx("Production line code")}
              />
              <Input
                label={tx("Machine ID")}
                value={form.machine_id ?? ""}
                onChange={(e) => setF("machine_id", e.target.value || null)}
                placeholder={tx("Machine/equipment code")}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Equipment Details")}</SectionTitle>
              <Input
                label={tx("Manufacturer")}
                value={form.manufacturer ?? ""}
                onChange={(e) => setF("manufacturer", e.target.value || null)}
              />
              <Input
                label={tx("Model")}
                value={form.equipment_model ?? ""}
                onChange={(e) => setF("equipment_model", e.target.value || null)}
              />
              <Input
                label={tx("Serial No.")}
                value={form.serial_no ?? ""}
                onChange={(e) => setF("serial_no", e.target.value || null)}
              />
              <Input
                label={tx("Install / Commission Date")}
                type="date"
                value={form.install_date ?? ""}
                onChange={(e) => setF("install_date", e.target.value || null)}
              />
              <Input
                label={tx("Warranty Expiry")}
                type="date"
                value={form.warranty_expiry ?? ""}
                onChange={(e) => setF("warranty_expiry", e.target.value || null)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Capacity & Rating")}</SectionTitle>
              <Input
                label={tx("Rated Capacity")}
                type="number"
                step="any"
                value={form.rated_capacity ?? ""}
                onChange={(e) => setF("rated_capacity", e.target.value || null)}
              />
              <Input
                label={tx("Capacity Unit")}
                value={form.capacity_unit ?? ""}
                onChange={(e) => setF("capacity_unit", e.target.value || null)}
                placeholder={tx("e.g. kW, kg/h, m³/h")}
              />
              <Input
                label={tx("Rated Power")}
                type="number"
                step="any"
                value={form.rated_power ?? ""}
                onChange={(e) => setF("rated_power", e.target.value || null)}
              />
              <Input
                label={tx("Power Unit")}
                value={form.rated_power_unit ?? ""}
                onChange={(e) => setF("rated_power_unit", e.target.value || null)}
                placeholder={tx("e.g. kW, kVA")}
              />
              <Input
                label={tx("Flow Capacity")}
                type="number"
                step="any"
                value={form.flow_capacity ?? ""}
                onChange={(e) => setF("flow_capacity", e.target.value || null)}
              />
              <Input
                label={tx("Pressure Capacity")}
                type="number"
                step="any"
                value={form.pressure_capacity ?? ""}
                onChange={(e) => setF("pressure_capacity", e.target.value || null)}
              />
              <Input
                label={tx("Temperature Range")}
                value={form.temperature_range ?? ""}
                onChange={(e) => setF("temperature_range", e.target.value || null)}
                placeholder={tx("e.g. -10°C to 60°C")}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Classification")}</SectionTitle>
              <Select
                label={tx("Operating Status")}
                value={form.status ?? "ACTIVE"}
                onChange={(e) => setF("status", e.target.value as UtilityAssetStatus)}
                options={ASSET_STATUS_OPTIONS}
              />
              <Select
                label={tx("Lifecycle Status")}
                value={form.lifecycle_status ?? ""}
                onChange={(e) => setF("lifecycle_status", e.target.value as LifecycleStatus || null)}
                options={[{ value: "", label: tx("— None —") }, ...LIFECYCLE_STATUS_OPTIONS]}
              />
              <Select
                label={tx("Criticality Level")}
                value={form.criticality_level ?? ""}
                onChange={(e) => setF("criticality_level", e.target.value as CriticalityLevel || null)}
                options={[{ value: "", label: tx("— None —") }, ...CRITICALITY_OPTIONS]}
              />
              <Input
                label={tx("Maintenance Strategy")}
                value={form.maintenance_strategy ?? ""}
                onChange={(e) => setF("maintenance_strategy", e.target.value || null)}
                placeholder={tx("e.g. Predictive, Preventive")}
              />
            </div>

            <Input
              label={tx("Notes")}
              value={form.notes ?? ""}
              onChange={(e) => setF("notes", e.target.value || null)}
              placeholder={tx("Optional notes")}
            />

            <div className="flex items-center gap-2">
              <input
                id="create-active"
                type="checkbox"
                checked={form.is_active ?? true}
                onChange={(e) => setF("is_active", e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600"
              />
              <label htmlFor="create-active" className="text-sm text-gray-700">{tx("Active")}</label>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}>
                {tx("Cancel")}
              </Button>
              <Button
                type="submit"
                loading={createMutation.isPending}
                disabled={!form.asset_no || !form.name || !form.category_id}
              >
                {tx("Create Asset")}
              </Button>
            </div>
          </form>
        </Modal>

        {/* Edit Modal */}
        <Modal
          open={!!editTarget}
          onClose={() => setEditTarget(null)}
          title={tx("Edit Asset — {asset_no}", { asset_no: editTarget?.asset_no })}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (editTarget) updateMutation.mutate({ id: editTarget.id, data: editForm });
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Identity")}</SectionTitle>
              <Input
                label={tx("Asset Name *")}
                value={editForm.name ?? ""}
                onChange={(e) => setE("name", e.target.value)}
                required
              />
              <Select
                label={tx("Category *")}
                value={editForm.category_id ?? ""}
                onChange={(e) => setE("category_id", e.target.value)}
                options={[
                  { value: "", label: tx("— Select category —") },
                  ...categories.map((c: UtilityAssetCategory) => ({
                    value: c.id,
                    label: `${c.code} — ${c.name}`,
                  })),
                ]}
              />
              <Select
                label={tx("Utility Type")}
                value={editForm.utility_type ?? "ELECTRICITY"}
                onChange={(e) => setE("utility_type", e.target.value as UtilityType)}
                options={UTILITY_TYPE_OPTIONS}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Location")}</SectionTitle>
              <Input label={tx("Location")} value={editForm.location ?? ""} onChange={(e) => setE("location", e.target.value || null)} />
              <Input label={tx("Building / Area")} value={editForm.building_area ?? ""} onChange={(e) => setE("building_area", e.target.value || null)} />
              <Input label={tx("Department")} value={editForm.department ?? ""} onChange={(e) => setE("department", e.target.value || null)} />
              <Input label={tx("Subsystem")} value={editForm.subsystem ?? ""} onChange={(e) => setE("subsystem", e.target.value || null)} />
              <Input label={tx("Line ID")} value={editForm.line_id ?? ""} onChange={(e) => setE("line_id", e.target.value || null)} />
              <Input label={tx("Machine ID")} value={editForm.machine_id ?? ""} onChange={(e) => setE("machine_id", e.target.value || null)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Equipment Details")}</SectionTitle>
              <Input label={tx("Manufacturer")} value={editForm.manufacturer ?? ""} onChange={(e) => setE("manufacturer", e.target.value || null)} />
              <Input label={tx("Model")} value={editForm.equipment_model ?? ""} onChange={(e) => setE("equipment_model", e.target.value || null)} />
              <Input label={tx("Serial No.")} value={editForm.serial_no ?? ""} onChange={(e) => setE("serial_no", e.target.value || null)} />
              <Input label={tx("Install / Commission Date")} type="date" value={editForm.install_date ?? ""} onChange={(e) => setE("install_date", e.target.value || null)} />
              <Input label={tx("Warranty Expiry")} type="date" value={editForm.warranty_expiry ?? ""} onChange={(e) => setE("warranty_expiry", e.target.value || null)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Capacity & Rating")}</SectionTitle>
              <Input label={tx("Rated Capacity")} type="number" step="any" value={editForm.rated_capacity ?? ""} onChange={(e) => setE("rated_capacity", e.target.value || null)} />
              <Input label={tx("Capacity Unit")} value={editForm.capacity_unit ?? ""} onChange={(e) => setE("capacity_unit", e.target.value || null)} />
              <Input label={tx("Rated Power")} type="number" step="any" value={editForm.rated_power ?? ""} onChange={(e) => setE("rated_power", e.target.value || null)} />
              <Input label={tx("Power Unit")} value={editForm.rated_power_unit ?? ""} onChange={(e) => setE("rated_power_unit", e.target.value || null)} />
              <Input label={tx("Flow Capacity")} type="number" step="any" value={editForm.flow_capacity ?? ""} onChange={(e) => setE("flow_capacity", e.target.value || null)} />
              <Input label={tx("Pressure Capacity")} type="number" step="any" value={editForm.pressure_capacity ?? ""} onChange={(e) => setE("pressure_capacity", e.target.value || null)} />
              <Input label={tx("Temperature Range")} value={editForm.temperature_range ?? ""} onChange={(e) => setE("temperature_range", e.target.value || null)} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SectionTitle>{tx("Classification")}</SectionTitle>
              <Select
                label={tx("Operating Status")}
                value={editForm.status ?? "ACTIVE"}
                onChange={(e) => setE("status", e.target.value as UtilityAssetStatus)}
                options={ASSET_STATUS_OPTIONS}
              />
              <Select
                label={tx("Lifecycle Status")}
                value={editForm.lifecycle_status ?? ""}
                onChange={(e) => setE("lifecycle_status", e.target.value as LifecycleStatus || null)}
                options={[{ value: "", label: tx("— None —") }, ...LIFECYCLE_STATUS_OPTIONS]}
              />
              <Select
                label={tx("Criticality Level")}
                value={editForm.criticality_level ?? ""}
                onChange={(e) => setE("criticality_level", e.target.value as CriticalityLevel || null)}
                options={[{ value: "", label: tx("— None —") }, ...CRITICALITY_OPTIONS]}
              />
              <Input
                label={tx("Maintenance Strategy")}
                value={editForm.maintenance_strategy ?? ""}
                onChange={(e) => setE("maintenance_strategy", e.target.value || null)}
              />
            </div>

            <Input
              label={tx("Notes")}
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
              <label htmlFor="edit-active" className="text-sm text-gray-700">{tx("Active")}</label>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => setEditTarget(null)}>{tx("Cancel")}</Button>
              <Button type="submit" loading={updateMutation.isPending}>{tx("Save Changes")}</Button>
            </div>
          </form>
        </Modal>

        {/* Delete Confirm Modal */}
        <Modal
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          title={tx("Delete Utility Asset")}
        >
          <p className="text-sm text-gray-600 mb-4">
            {tx("Delete asset")}{" "}
            <span className="font-semibold">{deleteTarget?.name}</span>{" "}
            <span className="font-mono text-xs text-gray-500">({deleteTarget?.asset_no})</span>{tx("? This cannot be undone. Readings, transactions and other records referencing this asset will be unlinked.")}
          </p>
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>{tx("Cancel")}</Button>
            <Button
              variant="danger"
              loading={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              {tx("Delete")}
            </Button>
          </div>
        </Modal>
      </div>
    </RequirePermission>
  );
}
