"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  utilityDevicesApi,
  UtilityDevice,
  UtilityDeviceCreate,
  UtilityDeviceUpdate,
  DeviceType,
  ReadingType,
  ReadingSource,
  ReadingFrequency,
  DEVICE_TYPE_LABELS,
  DEVICE_TYPE_OPTIONS,
  READING_TYPE_LABELS,
  READING_TYPE_OPTIONS,
  READING_SOURCE_OPTIONS,
  READING_FREQUENCY_OPTIONS,
  downloadAuthenticatedCsvDevices,
} from "@/lib/utilityDevices";
import {
  UtilityType,
  UTILITY_TYPE_LABELS,
  UTILITY_TYPE_OPTIONS,
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

const EMPTY_CREATE: UtilityDeviceCreate = {
  device_code: "",
  name: "",
  device_type: "METER",
  utility_type: "ELECTRICITY",
  unit_of_measure: "",
  calibration_required: false,
  is_active: true,
};

function deviceTypeVariant(t: DeviceType): "blue" | "green" | "yellow" | "gray" | "red" {
  const map: Record<DeviceType, "blue" | "green" | "yellow" | "gray" | "red"> = {
    METER:      "blue",
    SENSOR:     "green",
    LOGGER:     "gray",
    CONTROLLER: "yellow",
    ANALYSER:   "red",
  };
  return map[t] ?? "gray";
}

function CalibrationWarning({ device }: { device: UtilityDevice }) {
  if (!device.calibration_required) return null;
  if (!device.next_calibration_date) return <span className="text-xs text-amber-500">Due date not set</span>;

  const today = new Date();
  const dueDate = new Date(device.next_calibration_date);
  const daysUntil = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  if (device.calibration_due) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-50 border border-red-200 px-2 py-0.5 text-xs font-medium text-red-700">
        Overdue
      </span>
    );
  }
  if (daysUntil <= 30) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-xs font-medium text-amber-700">
        Due in {daysUntil}d
      </span>
    );
  }
  return <span className="text-xs text-gray-400">{device.next_calibration_date}</span>;
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="col-span-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 border-b border-indigo-100 pb-1 mb-1 mt-3">
      {children}
    </p>
  );
}

function DeviceForm({
  value,
  onChange,
  mode,
}: {
  value: UtilityDeviceCreate | UtilityDeviceUpdate;
  onChange: (update: Partial<UtilityDeviceCreate>) => void;
  mode: "create" | "edit";
}) {
  const v = value as UtilityDeviceCreate;
  return (
    <div className="space-y-0">
      <div className="grid grid-cols-2 gap-4">
        <SectionTitle>Identity</SectionTitle>
        {mode === "create" && (
          <Input
            label="Device Code *"
            value={v.device_code ?? ""}
            onChange={(e) => onChange({ device_code: e.target.value.toUpperCase() })}
            placeholder="e.g. MTR-ELEC-001"
            required
          />
        )}
        <Input
          label="Device Name *"
          value={v.name ?? ""}
          onChange={(e) => onChange({ name: e.target.value })}
          required
        />
        <Select
          label="Device Type *"
          value={v.device_type ?? "METER"}
          onChange={(e) => onChange({ device_type: e.target.value as DeviceType })}
          options={DEVICE_TYPE_OPTIONS}
        />
        <Select
          label="Utility Type *"
          value={v.utility_type ?? "ELECTRICITY"}
          onChange={(e) => onChange({ utility_type: e.target.value as UtilityType })}
          options={UTILITY_TYPE_OPTIONS}
        />
        <Input
          label="Unit of Measure *"
          value={v.unit_of_measure ?? ""}
          onChange={(e) => onChange({ unit_of_measure: e.target.value })}
          placeholder="e.g. kWh, m³, bar"
          required
        />

        <SectionTitle>Reading Classification</SectionTitle>
        <Select
          label="Reading Type"
          value={v.reading_type ?? ""}
          onChange={(e) => onChange({ reading_type: (e.target.value || null) as ReadingType | null })}
          options={[{ value: "", label: "— Select —" }, ...READING_TYPE_OPTIONS]}
        />
        <Select
          label="Reading Source"
          value={v.reading_source ?? ""}
          onChange={(e) => onChange({ reading_source: (e.target.value || null) as ReadingSource | null })}
          options={[{ value: "", label: "— Select —" }, ...READING_SOURCE_OPTIONS]}
        />
        <Select
          label="Reading Frequency"
          value={v.reading_frequency ?? ""}
          onChange={(e) => onChange({ reading_frequency: (e.target.value || null) as ReadingFrequency | null })}
          options={[{ value: "", label: "— Select —" }, ...READING_FREQUENCY_OPTIONS]}
        />

        <SectionTitle>Alarm Limits</SectionTitle>
        <Input
          label="Min Alarm Limit"
          type="number"
          value={v.min_alarm_limit ?? ""}
          onChange={(e) => onChange({ min_alarm_limit: e.target.value || null })}
          placeholder={`Min ${v.unit_of_measure || "value"}`}
        />
        <Input
          label="Max Alarm Limit"
          type="number"
          value={v.max_alarm_limit ?? ""}
          onChange={(e) => onChange({ max_alarm_limit: e.target.value || null })}
          placeholder={`Max ${v.unit_of_measure || "value"}`}
        />
        <Input
          label="Min Engineering Value"
          type="number"
          value={v.min_value ?? ""}
          onChange={(e) => onChange({ min_value: e.target.value || null })}
        />
        <Input
          label="Max Engineering Value"
          type="number"
          value={v.max_value ?? ""}
          onChange={(e) => onChange({ max_value: e.target.value || null })}
        />

        <SectionTitle>Calibration</SectionTitle>
        <div className="flex items-center gap-2 col-span-2">
          <input
            id="cal-required"
            type="checkbox"
            checked={v.calibration_required ?? false}
            onChange={(e) => onChange({ calibration_required: e.target.checked })}
            className="h-4 w-4 rounded border-gray-300 text-indigo-600"
          />
          <label htmlFor="cal-required" className="text-sm text-gray-700">Calibration Required</label>
        </div>
        <Input
          label="Calibration Frequency (days)"
          type="number"
          value={v.calibration_frequency_days ?? ""}
          onChange={(e) => onChange({ calibration_frequency_days: e.target.value ? Number(e.target.value) : null })}
          placeholder="e.g. 365"
        />
        <Input
          label="Last Calibration Date"
          type="date"
          value={v.last_calibration_date ?? ""}
          onChange={(e) => onChange({ last_calibration_date: e.target.value || null })}
        />
        <Input
          label="Next Calibration Date"
          type="date"
          value={v.next_calibration_date ?? ""}
          onChange={(e) => onChange({ next_calibration_date: e.target.value || null })}
        />

        <SectionTitle>Location</SectionTitle>
        <Input
          label="Location"
          value={v.location ?? ""}
          onChange={(e) => onChange({ location: e.target.value || null })}
          placeholder="Physical location description"
        />
        <Input
          label="Building / Area"
          value={v.building_area ?? ""}
          onChange={(e) => onChange({ building_area: e.target.value || null })}
          placeholder="e.g. Main Substation"
        />
        <Input
          label="Department"
          value={v.department ?? ""}
          onChange={(e) => onChange({ department: e.target.value || null })}
          placeholder="e.g. Utilities"
        />
        <Input
          label="Related Line ID"
          value={v.related_line_id ?? ""}
          onChange={(e) => onChange({ related_line_id: e.target.value || null })}
          placeholder="Production line code"
        />
        <Input
          label="Related Machine ID"
          value={v.related_machine_id ?? ""}
          onChange={(e) => onChange({ related_machine_id: e.target.value || null })}
          placeholder="Machine / equipment code"
        />

        <SectionTitle>Equipment</SectionTitle>
        <Input
          label="Manufacturer"
          value={v.manufacturer ?? ""}
          onChange={(e) => onChange({ manufacturer: e.target.value || null })}
        />
        <Input
          label="Model"
          value={v.equipment_model ?? ""}
          onChange={(e) => onChange({ equipment_model: e.target.value || null })}
        />
        <Input
          label="Serial Number"
          value={v.serial_no ?? ""}
          onChange={(e) => onChange({ serial_no: e.target.value || null })}
        />
        <Input
          label="Install Date"
          type="date"
          value={v.install_date ?? ""}
          onChange={(e) => onChange({ install_date: e.target.value || null })}
        />

        <SectionTitle>Notes</SectionTitle>
        <Input
          label="Notes"
          value={v.notes ?? ""}
          onChange={(e) => onChange({ notes: e.target.value || null })}
          placeholder="Optional notes"
        />
        <div className="flex items-center gap-2">
          <input
            id="dev-is-active"
            type="checkbox"
            checked={v.is_active ?? true}
            onChange={(e) => onChange({ is_active: e.target.checked })}
            className="h-4 w-4 rounded border-gray-300 text-indigo-600"
          />
          <label htmlFor="dev-is-active" className="text-sm text-gray-700">Active</label>
        </div>
      </div>
    </div>
  );
}

export default function UtilityDevicesPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<UtilityType | "">("");
  const [filterDeviceType, setFilterDeviceType] = useState<DeviceType | "">("");
  const [filterActive, setFilterActive] = useState<"" | "true" | "false">("");

  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<UtilityDeviceCreate>(EMPTY_CREATE);

  const [editTarget, setEditTarget] = useState<UtilityDevice | null>(null);
  const [editForm, setEditForm] = useState<UtilityDeviceUpdate>({});

  const [viewTarget, setViewTarget] = useState<UtilityDevice | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<UtilityDevice | null>(null);

  const { data: devices = [], isLoading } = useQuery({
    queryKey: ["utility-management", "devices", filterType, filterDeviceType, filterActive],
    queryFn: () =>
      utilityDevicesApi.devices.list({
        utility_type: filterType || undefined,
        device_type: filterDeviceType || undefined,
        is_active: filterActive === "" ? undefined : filterActive === "true",
        limit: 500,
      }),
  });

  const createMutation = useMutation({
    mutationFn: (data: UtilityDeviceCreate) => utilityDevicesApi.devices.create(data),
    onSuccess: (dev) => {
      qc.invalidateQueries({ queryKey: ["utility-management", "devices"] });
      setCreateOpen(false);
      setForm(EMPTY_CREATE);
      toast("success", "Device created", `${dev.name} (${dev.device_code}) added.`);
    },
    onError: (err) => toast("error", "Failed to create", extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UtilityDeviceUpdate }) =>
      utilityDevicesApi.devices.update(id, data),
    onSuccess: (dev) => {
      qc.invalidateQueries({ queryKey: ["utility-management", "devices"] });
      setEditTarget(null);
      toast("success", "Device updated", `${dev.name} saved.`);
    },
    onError: (err) => toast("error", "Failed to update", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilityDevicesApi.devices.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utility-management", "devices"] });
      setDeleteTarget(null);
      toast("success", "Device deleted");
    },
    onError: (err) => toast("error", "Cannot delete", extractApiError(err)),
  });

  const openEdit = (dev: UtilityDevice) => {
    setEditTarget(dev);
    setEditForm({
      name: dev.name,
      description: dev.description ?? "",
      device_type: dev.device_type,
      utility_type: dev.utility_type,
      reading_type: dev.reading_type,
      reading_source: dev.reading_source,
      reading_frequency: dev.reading_frequency,
      location: dev.location ?? "",
      building_area: dev.building_area ?? "",
      department: dev.department ?? "",
      related_line_id: dev.related_line_id ?? "",
      related_machine_id: dev.related_machine_id ?? "",
      unit_of_measure: dev.unit_of_measure,
      min_value: dev.min_value ?? "",
      max_value: dev.max_value ?? "",
      min_alarm_limit: dev.min_alarm_limit ?? "",
      max_alarm_limit: dev.max_alarm_limit ?? "",
      calibration_required: dev.calibration_required,
      calibration_frequency_days: dev.calibration_frequency_days,
      last_calibration_date: dev.last_calibration_date ?? "",
      next_calibration_date: dev.next_calibration_date ?? "",
      manufacturer: dev.manufacturer ?? "",
      equipment_model: dev.equipment_model ?? "",
      serial_no: dev.serial_no ?? "",
      notes: dev.notes ?? "",
      is_active: dev.is_active,
    });
  };

  const filtered = devices.filter((d) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return d.device_code.toLowerCase().includes(s) || d.name.toLowerCase().includes(s);
  });

  const handleExport = async () => {
    try {
      await downloadAuthenticatedCsvDevices(
        "/api/v1/utility-management/devices/export/csv",
        "utility_devices.csv",
      );
    } catch {
      toast("error", "Export failed");
    }
  };

  return (
    <RequirePermission permission="utility_management.view">
      <div>
        <ToastContainer toasts={toasts} onDismiss={dismiss} />

        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Meters &amp; Sensors</h1>
            <p className="text-sm text-gray-500 mt-1">
              {devices.length} devices &nbsp;·&nbsp;
              {devices.filter((d) => d.calibration_due).length > 0 && (
                <span className="text-red-600 font-medium">
                  {devices.filter((d) => d.calibration_due).length} calibration(s) overdue
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={handleExport}>Export CSV</Button>
            <ImportModal
              module="utility_devices"
              onSuccess={() => qc.invalidateQueries({ queryKey: ["utility-management", "devices"] })}
            />
            <Button onClick={() => setCreateOpen(true)}>+ Add Device</Button>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Input
            placeholder="Search code or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
          <Select
            label=""
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as UtilityType | "")}
            options={[{ value: "", label: "All utility types" }, ...UTILITY_TYPE_OPTIONS]}
          />
          <Select
            label=""
            value={filterDeviceType}
            onChange={(e) => setFilterDeviceType(e.target.value as DeviceType | "")}
            options={[{ value: "", label: "All device types" }, ...DEVICE_TYPE_OPTIONS]}
          />
          <Select
            label=""
            value={filterActive}
            onChange={(e) => setFilterActive(e.target.value as "" | "true" | "false")}
            options={[
              { value: "", label: "All statuses" },
              { value: "true", label: "Active only" },
              { value: "false", label: "Inactive only" },
            ]}
          />
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        ) : (
          <Table
            keyField="id"
            data={filtered}
            emptyMessage={search ? "No devices match your search." : "No devices yet."}
            columns={[
              {
                header: "Code",
                accessor: (r) => (
                  <span className="font-mono text-xs font-semibold text-gray-800">{r.device_code}</span>
                ),
              },
              { header: "Name", accessor: "name" },
              {
                header: "Type",
                accessor: (r) => (
                  <Badge label={DEVICE_TYPE_LABELS[r.device_type]} variant={deviceTypeVariant(r.device_type)} />
                ),
              },
              {
                header: "Utility",
                accessor: (r) => (
                  <span className="text-xs text-gray-600">{UTILITY_TYPE_LABELS[r.utility_type]}</span>
                ),
              },
              {
                header: "Unit",
                accessor: (r) => (
                  <span className="font-mono text-xs text-gray-600">{r.unit_of_measure}</span>
                ),
              },
              {
                header: "Readings",
                accessor: (r) => (
                  <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                    {r.reading_count}
                  </span>
                ),
              },
              {
                header: "Calibration",
                accessor: (r) => <CalibrationWarning device={r} />,
              },
              {
                header: "Status",
                accessor: (r) => (
                  <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "gray"} />
                ),
              },
              {
                header: "",
                accessor: (r) => (
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setViewTarget(r)}
                      className="text-xs text-gray-500 hover:text-gray-700 hover:underline"
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
                      disabled={r.reading_count > 0}
                      title={r.reading_count > 0 ? "Has readings — delete readings first" : "Delete"}
                    >
                      Delete
                    </button>
                  </div>
                ),
              },
            ]}
          />
        )}

        {/* View Modal */}
        <Modal
          open={!!viewTarget}
          onClose={() => setViewTarget(null)}
          title={`Device — ${viewTarget?.device_code}`}
        >
          {viewTarget && (
            <div className="space-y-4">
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                <div><dt className="text-xs text-gray-500">Name</dt><dd className="font-medium">{viewTarget.name}</dd></div>
                <div><dt className="text-xs text-gray-500">Device Type</dt><dd>{DEVICE_TYPE_LABELS[viewTarget.device_type]}</dd></div>
                <div><dt className="text-xs text-gray-500">Utility Type</dt><dd>{UTILITY_TYPE_LABELS[viewTarget.utility_type]}</dd></div>
                <div><dt className="text-xs text-gray-500">Unit</dt><dd className="font-mono">{viewTarget.unit_of_measure}</dd></div>
                {viewTarget.reading_type && (
                  <div><dt className="text-xs text-gray-500">Reading Type</dt><dd>{viewTarget.reading_type}</dd></div>
                )}
                {viewTarget.reading_frequency && (
                  <div><dt className="text-xs text-gray-500">Frequency</dt><dd>{viewTarget.reading_frequency}</dd></div>
                )}
                {viewTarget.min_alarm_limit && (
                  <div><dt className="text-xs text-gray-500">Min Alarm</dt><dd>{viewTarget.min_alarm_limit} {viewTarget.unit_of_measure}</dd></div>
                )}
                {viewTarget.max_alarm_limit && (
                  <div><dt className="text-xs text-gray-500">Max Alarm</dt><dd>{viewTarget.max_alarm_limit} {viewTarget.unit_of_measure}</dd></div>
                )}
                {viewTarget.department && (
                  <div><dt className="text-xs text-gray-500">Department</dt><dd>{viewTarget.department}</dd></div>
                )}
                {viewTarget.building_area && (
                  <div><dt className="text-xs text-gray-500">Building / Area</dt><dd>{viewTarget.building_area}</dd></div>
                )}
                {viewTarget.location && (
                  <div className="col-span-2"><dt className="text-xs text-gray-500">Location</dt><dd>{viewTarget.location}</dd></div>
                )}
                <div><dt className="text-xs text-gray-500">Calibration Required</dt><dd>{viewTarget.calibration_required ? "Yes" : "No"}</dd></div>
                {viewTarget.next_calibration_date && (
                  <div><dt className="text-xs text-gray-500">Next Calibration</dt><dd><CalibrationWarning device={viewTarget} /></dd></div>
                )}
                {viewTarget.manufacturer && (
                  <div><dt className="text-xs text-gray-500">Manufacturer</dt><dd>{viewTarget.manufacturer}</dd></div>
                )}
                {viewTarget.serial_no && (
                  <div><dt className="text-xs text-gray-500">Serial No.</dt><dd className="font-mono text-xs">{viewTarget.serial_no}</dd></div>
                )}
                <div><dt className="text-xs text-gray-500">Readings</dt><dd>{viewTarget.reading_count}</dd></div>
              </dl>
              <div className="flex justify-end">
                <Button variant="secondary" onClick={() => setViewTarget(null)}>Close</Button>
              </div>
            </div>
          )}
        </Modal>

        {/* Create Modal */}
        <Modal
          open={createOpen}
          onClose={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}
          title="Add Device"
        >
          <form
            onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }}
            className="space-y-4 max-h-[70vh] overflow-y-auto pr-1"
          >
            <DeviceForm value={form} onChange={(u) => setForm((f) => ({ ...f, ...u }))} mode="create" />
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}>
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending}>Create</Button>
            </div>
          </form>
        </Modal>

        {/* Edit Modal */}
        <Modal
          open={!!editTarget}
          onClose={() => setEditTarget(null)}
          title={`Edit Device — ${editTarget?.device_code}`}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (editTarget) updateMutation.mutate({ id: editTarget.id, data: editForm });
            }}
            className="space-y-4 max-h-[70vh] overflow-y-auto pr-1"
          >
            <DeviceForm value={editForm} onChange={(u) => setEditForm((f) => ({ ...f, ...u }))} mode="edit" />
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => setEditTarget(null)}>Cancel</Button>
              <Button type="submit" loading={updateMutation.isPending}>Save Changes</Button>
            </div>
          </form>
        </Modal>

        {/* Delete Confirm */}
        <Modal
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          title="Delete Device"
        >
          {deleteTarget && (
            deleteTarget.reading_count > 0 ? (
              <div className="space-y-4">
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
                  <p className="text-sm font-semibold text-red-800">Cannot delete &quot;{deleteTarget.name}&quot;</p>
                  <p className="text-xs text-red-600 mt-1">
                    {deleteTarget.reading_count} reading(s) reference this device. Delete readings first.
                  </p>
                </div>
                <div className="flex justify-end">
                  <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Close</Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Delete device{" "}
                  <span className="font-semibold">{deleteTarget.name}</span>{" "}
                  <span className="font-mono text-xs text-gray-500">({deleteTarget.device_code})</span>?
                  This cannot be undone.
                </p>
                <div className="flex justify-end gap-3">
                  <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
                  <Button
                    variant="danger"
                    loading={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(deleteTarget.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            )
          )}
        </Modal>
      </div>
    </RequirePermission>
  );
}
