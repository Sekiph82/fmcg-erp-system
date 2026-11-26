"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  utilityDevicesApi,
  UtilityDevice,
  UtilityReading,
  UtilityReadingCreate,
  ValidatedStatus,
  SourceMethod,
  VALIDATED_STATUS_LABELS,
  SOURCE_METHOD_LABELS,
  DATA_QUALITY_LABELS,
  downloadAuthenticatedCsvDevices,
} from "@/lib/utilityDevices";
import { UtilityType, UTILITY_TYPE_LABELS } from "@/lib/utilityManagement";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { RequirePermission } from "@/components/PermissionGuard";
import { tx } from "@/lib/i18n/core";

const EMPTY_CREATE: UtilityReadingCreate = {
  device_id: "",
  reading_datetime: new Date().toISOString().slice(0, 16),
  raw_value: "",
  source_method: "MANUAL",
};

function validatedStatusVariant(s: ValidatedStatus): "green" | "blue" | "red" | "gray" | "yellow" {
  const map: Record<ValidatedStatus, "green" | "blue" | "red" | "gray" | "yellow"> = {
    AUTO_APPROVED: "green",
    VALIDATED:     "blue",
    REJECTED:      "red",
    PENDING:       "gray",
  };
  return map[s] ?? "gray";
}

function qualityVariant(q: string): "green" | "yellow" | "red" | "gray" {
  if (q === "GOOD") return "green";
  if (q === "ESTIMATED") return "yellow";
  if (q === "SUSPECT" || q === "MISSING") return "red";
  return "gray";
}

function formatDateTime(dt: string): string {
  try {
    return new Date(dt).toLocaleString(undefined, {
      year: "numeric", month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return dt;
  }
}

export default function UtilityReadingsPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [filterDeviceId, setFilterDeviceId] = useState("");
  const [filterSource, setFilterSource] = useState<SourceMethod | "">("");
  const [filterValidated, setFilterValidated] = useState<ValidatedStatus | "">("");
  const [filterAnomaly, setFilterAnomaly] = useState<"" | "true" | "false">("");
  const [filterBatchId, setFilterBatchId] = useState("");
  const [filterFromDt, setFilterFromDt] = useState("");
  const [filterToDt, setFilterToDt] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<UtilityReadingCreate>(EMPTY_CREATE);

  const [viewTarget, setViewTarget] = useState<UtilityReading | null>(null);
  const [validateTarget, setValidateTarget] = useState<UtilityReading | null>(null);
  const [validateStatus, setValidateStatus] = useState<ValidatedStatus>("VALIDATED");
  const [validateNotes, setValidateNotes] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<UtilityReading | null>(null);

  // Fetch device list for the selector
  const { data: devices = [] } = useQuery({
    queryKey: ["utility-management", "devices", "all"],
    queryFn: () => utilityDevicesApi.devices.list({ is_active: true, limit: 500 }),
  });

  const deviceMap = Object.fromEntries(devices.map((d) => [d.id, d]));

  const { data: readings = [], isLoading } = useQuery({
    queryKey: [
      "utility-management", "readings",
      filterDeviceId, filterSource, filterValidated, filterAnomaly,
      filterBatchId, filterFromDt, filterToDt,
    ],
    queryFn: () =>
      utilityDevicesApi.readings.list({
        device_id:        filterDeviceId || undefined,
        source_method:    (filterSource || undefined) as SourceMethod | undefined,
        validated_status: (filterValidated || undefined) as ValidatedStatus | undefined,
        is_anomaly:       filterAnomaly === "" ? undefined : filterAnomaly === "true",
        batch_id:         filterBatchId || undefined,
        from_dt:          filterFromDt || undefined,
        to_dt:            filterToDt || undefined,
        limit:            500,
      }),
  });

  const selectedDevice = form.device_id ? deviceMap[form.device_id] : null;

  const createMutation = useMutation({
    mutationFn: (data: UtilityReadingCreate) => utilityDevicesApi.readings.create(data),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["utility-management", "readings"] });
      setCreateOpen(false);
      setForm(EMPTY_CREATE);
      const anomalyNote = r.is_anomaly ? ` ⚠ Anomaly flagged: ${r.anomaly_note}` : "";
      toast(
        r.is_anomaly ? "error" : "success",
        tx("Reading recorded"),
        tx("{reading_no} — quality: {quality}{anomalyNote}", { reading_no: r.reading_no, quality: r.quality, anomalyNote }),
      );
    },
    onError: (err) => toast("error", tx("Failed to record reading"), extractApiError(err)),
  });

  const validateMutation = useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: ValidatedStatus; notes: string }) =>
      utilityDevicesApi.readings.validate(id, status, notes || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utility-management", "readings"] });
      setValidateTarget(null);
      toast("success", tx("Reading validated"));
    },
    onError: (err) => toast("error", tx("Failed to validate"), extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilityDevicesApi.readings.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utility-management", "readings"] });
      setDeleteTarget(null);
      toast("success", tx("Reading deleted"));
    },
    onError: (err) => toast("error", tx("Cannot delete"), extractApiError(err)),
  });

  const openValidate = (r: UtilityReading) => {
    setValidateTarget(r);
    setValidateStatus("VALIDATED");
    setValidateNotes(r.validation_notes ?? "");
  };

  const handleExport = async () => {
    const params = new URLSearchParams();
    if (filterDeviceId) params.set("device_id", filterDeviceId);
    if (filterFromDt)  params.set("from_dt", filterFromDt);
    if (filterToDt)    params.set("to_dt", filterToDt);
    const qs = params.toString();
    try {
      await downloadAuthenticatedCsvDevices(
        `/api/v1/utility-management/readings/export/csv${qs ? `?${qs}` : ""}`,
        "utility_readings.csv",
      );
    } catch {
      toast("error", tx("Export failed"));
    }
  };

  const anomalyCount = readings.filter((r) => r.is_anomaly).length;
  const pendingCount = readings.filter((r) => r.validated_status === "PENDING").length;

  return (
    <RequirePermission permission="utility_management.view">
      <div>
        <ToastContainer toasts={toasts} onDismiss={dismiss} />

        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{tx("Utility Readings")}</h1>
            <p className="text-sm text-gray-500 mt-1 flex items-center gap-3">
              <span>{readings.length} {tx("readings")}</span>
              {anomalyCount > 0 && (
                <span className="text-red-600 font-medium">{anomalyCount} {tx("anomaly(ies)")}</span>
              )}
              {pendingCount > 0 && (
                <span className="text-amber-600 font-medium">{pendingCount} {tx("pending validation")}</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={handleExport}>{tx("Export CSV")}</Button>
            <Button onClick={() => setCreateOpen(true)}>{tx("+ Record Reading")}</Button>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Select
            label=""
            value={filterDeviceId}
            onChange={(e) => setFilterDeviceId(e.target.value)}
            options={[
              { value: "", label: tx("All devices") },
              ...devices.map((d) => ({ value: d.id, label: `${d.device_code} — ${d.name}` })),
            ]}
          />
          <Select
            label=""
            value={filterValidated}
            onChange={(e) => setFilterValidated(e.target.value as ValidatedStatus | "")}
            options={[
              { value: "", label: tx("All statuses") },
              ...Object.entries(VALIDATED_STATUS_LABELS).map(([v, l]) => ({ value: v, label: l })),
            ]}
          />
          <Select
            label=""
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value as SourceMethod | "")}
            options={[
              { value: "", label: tx("All sources") },
              ...Object.entries(SOURCE_METHOD_LABELS).map(([v, l]) => ({ value: v, label: l })),
            ]}
          />
          <Select
            label=""
            value={filterAnomaly}
            onChange={(e) => setFilterAnomaly(e.target.value as "" | "true" | "false")}
            options={[
              { value: "", label: tx("Anomaly: all") },
              { value: "true", label: tx("Anomalies only") },
              { value: "false", label: tx("Normal only") },
            ]}
          />
          <Input
            placeholder={tx("Batch ID")}
            value={filterBatchId}
            onChange={(e) => setFilterBatchId(e.target.value)}
            className="max-w-xs"
          />
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">{tx("From:")}</span>
            <input
              type="datetime-local"
              value={filterFromDt}
              onChange={(e) => setFilterFromDt(e.target.value)}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">{tx("To:")}</span>
            <input
              type="datetime-local"
              value={filterToDt}
              onChange={(e) => setFilterToDt(e.target.value)}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
          </div>
        ) : (
          <Table
            keyField="id"
            data={readings}
            emptyMessage="No readings found. Apply different filters or record a new reading."
            columns={[
              {
                header: tx("Reading No."),
                accessor: (r) => (
                  <span className="font-mono text-xs font-semibold text-gray-800">{r.reading_no}</span>
                ),
              },
              {
                header: tx("Device"),
                accessor: (r) => (
                  <div>
                    <span className="font-mono text-xs text-gray-800">{r.device_code}</span>
                    {r.device_name && (
                      <p className="text-xs text-gray-500 truncate max-w-[160px]">{r.device_name}</p>
                    )}
                  </div>
                ),
              },
              {
                header: tx("Date / Time"),
                accessor: (r) => (
                  <span className="text-xs text-gray-700">{formatDateTime(r.reading_datetime)}</span>
                ),
              },
              {
                header: tx("Value"),
                accessor: (r) => (
                  <span className="font-mono font-semibold text-sm">
                    {r.raw_value} <span className="text-xs font-normal text-gray-500">{r.unit_of_measure}</span>
                  </span>
                ),
              },
              {
                header: tx("Interval"),
                accessor: (r) =>
                  r.interval_consumption ? (
                    <span className="font-mono text-xs text-emerald-700">{tx("Δ")} {r.interval_consumption}</span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  ),
              },
              {
                header: tx("Quality"),
                accessor: (r) => (
                  <Badge label={DATA_QUALITY_LABELS[r.quality as keyof typeof DATA_QUALITY_LABELS] ?? r.quality} variant={qualityVariant(r.quality)} />
                ),
              },
              {
                header: tx("Anomaly"),
                accessor: (r) =>
                  r.is_anomaly ? (
                    <span
                      className="inline-flex items-center rounded-full bg-red-50 border border-red-200 px-2 py-0.5 text-xs font-medium text-red-700 cursor-help"
                      title={r.anomaly_note ?? ""}
                    >
                      {tx("Yes")}
                    </span>
                  ) : (
                    <span className="text-gray-400 text-xs">—</span>
                  ),
              },
              {
                header: tx("Validation"),
                accessor: (r) => (
                  <Badge
                    label={VALIDATED_STATUS_LABELS[r.validated_status]}
                    variant={validatedStatusVariant(r.validated_status)}
                  />
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
                      {tx("View")}
                    </button>
                    {(r.validated_status === "PENDING" || r.is_anomaly) && (
                      <button
                        onClick={() => openValidate(r)}
                        className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
                      >
                        {tx("Validate")}
                      </button>
                    )}
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

        {/* Record Reading Modal */}
        <Modal
          open={createOpen}
          onClose={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}
          title={tx("Record Reading")}
        >
          <form
            onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }}
            className="space-y-4"
          >
            <Select
              label={tx("Device *")}
              value={form.device_id}
              onChange={(e) => setForm((f) => ({ ...f, device_id: e.target.value }))}
              options={[
                { value: "", label: tx("— Select device —") },
                ...devices.map((d) => ({
                  value: d.id,
                  label: `${d.device_code} — ${d.name} (${d.unit_of_measure})`,
                })),
              ]}
            />

            {selectedDevice && (
              <div className="rounded-lg bg-indigo-50 border border-indigo-100 px-3 py-2 text-xs text-indigo-700 space-y-1">
                <p><span className="font-semibold">{tx("Utility:")}</span> {UTILITY_TYPE_LABELS[selectedDevice.utility_type]}</p>
                <p><span className="font-semibold">{tx("Unit:")}</span> {selectedDevice.unit_of_measure}</p>
                {selectedDevice.min_alarm_limit && <p><span className="font-semibold">{tx("Min alarm:")}</span> {selectedDevice.min_alarm_limit}</p>}
                {selectedDevice.max_alarm_limit && <p><span className="font-semibold">{tx("Max alarm:")}</span> {selectedDevice.max_alarm_limit}</p>}
                {selectedDevice.calibration_due && (
                  <p className="text-red-600 font-semibold">{tx("Calibration overdue — readings may be unreliable")}</p>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">{tx("Reading Date / Time *")}</label>
                <input
                  type="datetime-local"
                  value={form.reading_datetime}
                  onChange={(e) => setForm((f) => ({ ...f, reading_datetime: e.target.value }))}
                  required
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <Input
                label={tx("Raw Value *")}
                type="number"
                step="any"
                value={String(form.raw_value)}
                onChange={(e) => setForm((f) => ({ ...f, raw_value: e.target.value }))}
                placeholder={selectedDevice ? tx("Value in {unit_of_measure}", { unit_of_measure: selectedDevice.unit_of_measure }) : tx("Reading value")}
                required
              />
              <Input
                label={tx("Cumulative Value {reading_type}", { reading_type: selectedDevice?.reading_type === "CUMULATIVE" ? "*" : "(opt.)" })}
                type="number"
                step="any"
                value={String(form.cumulative_value ?? "")}
                onChange={(e) => setForm((f) => ({ ...f, cumulative_value: e.target.value || null }))}
                placeholder={tx("Totalizer / index value")}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Select
                label={tx("Source Method")}
                value={form.source_method ?? "MANUAL"}
                onChange={(e) => setForm((f) => ({ ...f, source_method: e.target.value as SourceMethod }))}
                options={Object.entries(SOURCE_METHOD_LABELS).map(([v, l]) => ({ value: v, label: l }))}
              />
              <Input
                label={tx("Source Reference")}
                value={form.source_reference ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, source_reference: e.target.value || null }))}
                placeholder={tx("IoT message ID / batch ref")}
              />
              <Input
                label={tx("Shift Reference")}
                value={form.shift_ref ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, shift_ref: e.target.value || null }))}
                placeholder={tx("e.g. SHIFT-A")}
              />
              <Input
                label={tx("Batch ID")}
                value={form.batch_id ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, batch_id: e.target.value || null }))}
                placeholder={tx("e.g. BATCH-2026-001")}
              />
              <Input
                label={tx("Department")}
                value={form.department ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, department: e.target.value || null }))}
              />
              <Input
                label={tx("Notes")}
                value={form.notes ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value || null }))}
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => { setCreateOpen(false); setForm(EMPTY_CREATE); }}>
                {tx("Cancel")}
              </Button>
              <Button type="submit" loading={createMutation.isPending}>{tx("Record")}</Button>
            </div>
          </form>
        </Modal>

        {/* View Modal */}
        <Modal
          open={!!viewTarget}
          onClose={() => setViewTarget(null)}
          title={tx("Reading — {reading_no}", { reading_no: viewTarget?.reading_no })}
        >
          {viewTarget && (
            <div className="space-y-4">
              {viewTarget.is_anomaly && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
                  <p className="text-sm font-semibold text-red-800">{tx("Anomaly Detected")}</p>
                  <p className="text-xs text-red-600 mt-1">{viewTarget.anomaly_note}</p>
                </div>
              )}
              <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                <div><dt className="text-xs text-gray-500">{tx("Device")}</dt><dd className="font-mono text-xs">{viewTarget.device_code}</dd></div>
                <div><dt className="text-xs text-gray-500">{tx("Date / Time")}</dt><dd>{formatDateTime(viewTarget.reading_datetime)}</dd></div>
                <div><dt className="text-xs text-gray-500">{tx("Raw Value")}</dt><dd className="font-mono font-bold">{viewTarget.raw_value} {viewTarget.unit_of_measure}</dd></div>
                {viewTarget.adjusted_value && (
                  <div><dt className="text-xs text-gray-500">{tx("Adjusted Value")}</dt><dd className="font-mono">{viewTarget.adjusted_value} {viewTarget.unit_of_measure}</dd></div>
                )}
                {viewTarget.cumulative_value && (
                  <div><dt className="text-xs text-gray-500">{tx("Cumulative")}</dt><dd className="font-mono">{viewTarget.cumulative_value}</dd></div>
                )}
                {viewTarget.interval_consumption && (
                  <div><dt className="text-xs text-gray-500">{tx("Interval Consumption")}</dt><dd className="font-mono text-emerald-700">{tx("Δ")} {viewTarget.interval_consumption}</dd></div>
                )}
                <div><dt className="text-xs text-gray-500">{tx("Quality")}</dt>
                  <dd><Badge label={DATA_QUALITY_LABELS[viewTarget.quality as keyof typeof DATA_QUALITY_LABELS] ?? viewTarget.quality} variant={qualityVariant(viewTarget.quality)} /></dd>
                </div>
                <div><dt className="text-xs text-gray-500">{tx("Validation")}</dt>
                  <dd><Badge label={VALIDATED_STATUS_LABELS[viewTarget.validated_status]} variant={validatedStatusVariant(viewTarget.validated_status)} /></dd>
                </div>
                <div><dt className="text-xs text-gray-500">{tx("Source")}</dt><dd>{SOURCE_METHOD_LABELS[viewTarget.source_method]}</dd></div>
                {viewTarget.source_reference && (
                  <div><dt className="text-xs text-gray-500">{tx("Source Reference")}</dt><dd className="font-mono text-xs">{viewTarget.source_reference}</dd></div>
                )}
                {viewTarget.shift_ref && (
                  <div><dt className="text-xs text-gray-500">{tx("Shift")}</dt><dd>{viewTarget.shift_ref}</dd></div>
                )}
                {viewTarget.batch_id && (
                  <div><dt className="text-xs text-gray-500">{tx("Batch ID")}</dt><dd className="font-mono text-xs">{viewTarget.batch_id}</dd></div>
                )}
                {viewTarget.department && (
                  <div><dt className="text-xs text-gray-500">{tx("Department")}</dt><dd>{viewTarget.department}</dd></div>
                )}
                {viewTarget.validation_notes && (
                  <div className="col-span-2"><dt className="text-xs text-gray-500">{tx("Validation Notes")}</dt><dd className="text-xs">{viewTarget.validation_notes}</dd></div>
                )}
                {viewTarget.notes && (
                  <div className="col-span-2"><dt className="text-xs text-gray-500">{tx("Notes")}</dt><dd className="text-xs">{viewTarget.notes}</dd></div>
                )}
                {viewTarget.created_at && (
                  <div className="col-span-2"><dt className="text-xs text-gray-500">{tx("Recorded At")}</dt><dd className="text-xs text-gray-500">{formatDateTime(viewTarget.created_at)}</dd></div>
                )}
              </dl>
              <div className="flex justify-end gap-3">
                {(viewTarget.validated_status === "PENDING" || viewTarget.is_anomaly) && (
                  <Button onClick={() => { setViewTarget(null); openValidate(viewTarget); }}>{tx("Validate")}</Button>
                )}
                <Button variant="secondary" onClick={() => setViewTarget(null)}>{tx("Close")}</Button>
              </div>
            </div>
          )}
        </Modal>

        {/* Validate Modal */}
        <Modal
          open={!!validateTarget}
          onClose={() => setValidateTarget(null)}
          title={tx("Validate Reading — {reading_no}", { reading_no: validateTarget?.reading_no })}
        >
          {validateTarget && (
            <div className="space-y-4">
              {validateTarget.is_anomaly && (
                <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700">
                  <span className="font-semibold">{tx("Anomaly flagged:")}</span> {validateTarget.anomaly_note}
                </div>
              )}
              <div className="text-sm text-gray-700">
                <span className="font-mono font-bold">{validateTarget.raw_value} {validateTarget.unit_of_measure}</span>
                {" "} {tx("at")} {formatDateTime(validateTarget.reading_datetime)}
              </div>
              <Select
                label={tx("Validation Decision *")}
                value={validateStatus}
                onChange={(e) => setValidateStatus(e.target.value as ValidatedStatus)}
                options={[
                  { value: "VALIDATED", label: tx("Validated — accept reading") },
                  { value: "REJECTED", label: tx("Rejected — mark invalid") },
                ]}
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{tx("Notes")}</label>
                <textarea
                  rows={3}
                  value={validateNotes}
                  onChange={(e) => setValidateNotes(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder={tx("Reason for decision (optional)")}
                />
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="secondary" onClick={() => setValidateTarget(null)}>{tx("Cancel")}</Button>
                <Button
                  variant={validateStatus === "REJECTED" ? "danger" : "primary"}
                  loading={validateMutation.isPending}
                  onClick={() =>
                    validateMutation.mutate({
                      id: validateTarget.id,
                      status: validateStatus,
                      notes: validateNotes,
                    })
                  }
                >
                  {validateStatus === "REJECTED" ? tx("Reject") : tx("Validate")}
                </Button>
              </div>
            </div>
          )}
        </Modal>

        {/* Delete Confirm */}
        <Modal
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          title={tx("Delete Reading")}
        >
          {deleteTarget && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                {tx("Delete reading")} <span className="font-mono font-semibold">{deleteTarget.reading_no}</span>{tx("? This action cannot be undone.")}
              </p>
              <div className="flex justify-end gap-3">
                <Button variant="secondary" onClick={() => setDeleteTarget(null)}>{tx("Cancel")}</Button>
                <Button
                  variant="danger"
                  loading={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(deleteTarget.id)}
                >
                  {tx("Delete")}
                </Button>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </RequirePermission>
  );
}
