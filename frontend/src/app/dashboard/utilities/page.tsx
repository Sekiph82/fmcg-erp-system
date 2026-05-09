"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  utilitiesApi,
  SystemConfig, SystemConfigCreate, SystemConfigUpdate, ConfigCategory,
  UomConversion, UomConversionCreate,
  NumberSeries, NumberSeriesCreate, NumberSeriesUpdate,
  Currency, CurrencyCreate, CurrencyUpdate,
} from "@/lib/utilities";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { RequirePermission, PermissionGuard } from "@/components/PermissionGuard";

// ── Tab definitions ────────────────────────────────────────────────────────────

type Tab = "configs" | "uom" | "series" | "currencies";

const TABS: { id: Tab; label: string }[] = [
  { id: "configs",    label: "System Configs" },
  { id: "uom",        label: "UOM Conversions" },
  { id: "series",     label: "Number Series" },
  { id: "currencies", label: "Currencies" },
];

const CONFIG_CATEGORIES: { value: string; label: string }[] = [
  { value: "COMPANY",       label: "Company" },
  { value: "SYSTEM",        label: "System" },
  { value: "FINANCE",       label: "Finance" },
  { value: "NOTIFICATIONS", label: "Notifications" },
  { value: "OPERATIONS",    label: "Operations" },
];

function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
    </div>
  );
}

// ── System Configs Tab ─────────────────────────────────────────────────────────

function ConfigsTab() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<SystemConfig | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<SystemConfig | null>(null);
  const [form, setForm] = useState<SystemConfigCreate>({ key: "", value: "", category: "SYSTEM", is_editable: true });
  const [editData, setEditData] = useState<SystemConfigUpdate>({});

  const { data: configs = [], isLoading } = useQuery({
    queryKey: ["utilities", "configs"],
    queryFn: () => utilitiesApi.configs.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: SystemConfigCreate) => utilitiesApi.configs.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "configs"] });
      setCreateOpen(false);
      setForm({ key: "", value: "", category: "SYSTEM", is_editable: true });
      toast("success", "Config created", "System configuration saved.");
    },
    onError: (err) => toast("error", "Failed to create config", extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: SystemConfigUpdate }) =>
      utilitiesApi.configs.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "configs"] });
      setEditTarget(null);
      toast("success", "Config updated", "Configuration saved.");
    },
    onError: (err) => toast("error", "Failed to update config", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilitiesApi.configs.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "configs"] });
      setDeleteTarget(null);
      toast("success", "Config deleted");
    },
    onError: (err) => toast("error", "Failed to delete config", extractApiError(err)),
  });

  const openEdit = (cfg: SystemConfig) => {
    setEditTarget(cfg);
    setEditData({ value: cfg.value ?? "", description: cfg.description ?? "", category: cfg.category, is_editable: cfg.is_editable });
  };

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-500">{configs.length} configuration entries</p>
        <PermissionGuard permission="utilities.manage">
          <Button onClick={() => setCreateOpen(true)}>+ Add Config</Button>
        </PermissionGuard>
      </div>

      {isLoading ? <Spinner /> : (
        <Table
          keyField="id"
          data={configs}
          emptyMessage="No system configurations found."
          columns={[
            { header: "Key",      accessor: (r) => <code className="text-xs bg-gray-100 px-1 rounded">{r.key}</code> },
            { header: "Value",    accessor: (r) => r.value ?? "—" },
            { header: "Category", accessor: (r) => <Badge label={r.category} variant={r.category === "FINANCE" ? "green" : r.category === "COMPANY" ? "blue" : r.category === "NOTIFICATIONS" ? "yellow" : "gray"} /> },
            { header: "Editable", accessor: (r) => <Badge label={r.is_editable ? "Yes" : "Read-only"} variant={r.is_editable ? "green" : "gray"} /> },
            {
              header: "Actions",
              accessor: (r) => (
                <div className="flex gap-2">
                  <PermissionGuard permission="utilities.edit">
                    <Button variant="secondary" onClick={() => openEdit(r)} disabled={!r.is_editable}>Edit</Button>
                  </PermissionGuard>
                  <PermissionGuard permission="utilities.manage">
                    <Button variant="danger" onClick={() => setDeleteTarget(r)} disabled={!r.is_editable}>Delete</Button>
                  </PermissionGuard>
                </div>
              ),
            },
          ]}
        />
      )}

      {/* Create Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add System Config">
        <div className="space-y-4">
          <Input label="Key" value={form.key} onChange={(e) => setForm((f) => ({ ...f, key: e.target.value }))} placeholder="e.g. company.name" />
          <Input label="Value" value={form.value ?? ""} onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))} />
          <Input label="Description" value={form.description ?? ""} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          <Select
            label="Category"
            value={form.category ?? "SYSTEM"}
            onChange={(e) => setForm((f) => ({ ...f, category: e.target.value as ConfigCategory }))}
            options={CONFIG_CATEGORIES}
          />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_editable ?? true} onChange={(e) => setForm((f) => ({ ...f, is_editable: e.target.checked }))} />
            Editable (users can change this value)
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={() => createMutation.mutate(form)} disabled={!form.key} loading={createMutation.isPending}>Save</Button>
          </div>
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title={`Edit: ${editTarget?.key}`}>
        <div className="space-y-4">
          <Input label="Value" value={editData.value ?? ""} onChange={(e) => setEditData((d) => ({ ...d, value: e.target.value }))} />
          <Input label="Description" value={editData.description ?? ""} onChange={(e) => setEditData((d) => ({ ...d, description: e.target.value }))} />
          <Select
            label="Category"
            value={editData.category ?? "SYSTEM"}
            onChange={(e) => setEditData((d) => ({ ...d, category: e.target.value as ConfigCategory }))}
            options={CONFIG_CATEGORIES}
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setEditTarget(null)}>Cancel</Button>
            <Button
              onClick={() => editTarget && updateMutation.mutate({ id: editTarget.id, data: editData })}
              loading={updateMutation.isPending}
            >Save</Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirm */}
      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Config">
        <p className="text-sm text-gray-700 mb-4">
          Delete config key <strong>{deleteTarget?.key}</strong>? This cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            variant="danger"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            loading={deleteMutation.isPending}
          >Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

// ── UOM Conversions Tab ────────────────────────────────────────────────────────

function UomTab() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<UomConversion | null>(null);
  const [form, setForm] = useState<UomConversionCreate>({ from_uom: "", to_uom: "", factor: "1", is_active: true });

  const { data: conversions = [], isLoading } = useQuery({
    queryKey: ["utilities", "uom"],
    queryFn: () => utilitiesApi.uomConversions.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: UomConversionCreate) => utilitiesApi.uomConversions.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "uom"] });
      setCreateOpen(false);
      setForm({ from_uom: "", to_uom: "", factor: "1", is_active: true });
      toast("success", "Conversion created");
    },
    onError: (err) => toast("error", "Failed to create conversion", extractApiError(err)),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      utilitiesApi.uomConversions.update(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["utilities", "uom"] }),
    onError: (err) => toast("error", "Update failed", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilitiesApi.uomConversions.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "uom"] });
      setDeleteTarget(null);
      toast("success", "Conversion deleted");
    },
    onError: (err) => toast("error", "Failed to delete", extractApiError(err)),
  });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-500">{conversions.length} conversion rules</p>
        <PermissionGuard permission="utilities.edit">
          <Button onClick={() => setCreateOpen(true)}>+ Add Conversion</Button>
        </PermissionGuard>
      </div>

      {isLoading ? <Spinner /> : (
        <Table
          keyField="id"
          data={conversions}
          emptyMessage="No UOM conversions defined."
          columns={[
            { header: "From",   accessor: (r) => <Badge label={r.from_uom} variant="blue" /> },
            { header: "To",     accessor: (r) => <Badge label={r.to_uom} variant="yellow" /> },
            { header: "Factor", accessor: (r) => <span className="font-mono text-sm">{r.factor}</span> },
            { header: "Status", accessor: (r) => <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "gray"} /> },
            {
              header: "Actions",
              accessor: (r) => (
                <div className="flex gap-2">
                  <PermissionGuard permission="utilities.edit">
                    <Button
                      variant="secondary"
                      onClick={() => toggleMutation.mutate({ id: r.id, is_active: !r.is_active })}
                    >
                      {r.is_active ? "Deactivate" : "Activate"}
                    </Button>
                  </PermissionGuard>
                  <PermissionGuard permission="utilities.manage">
                    <Button variant="danger" onClick={() => setDeleteTarget(r)}>Delete</Button>
                  </PermissionGuard>
                </div>
              ),
            },
          ]}
        />
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add UOM Conversion">
        <div className="space-y-4">
          <Input label="From UOM" value={form.from_uom} onChange={(e) => setForm((f) => ({ ...f, from_uom: e.target.value.toUpperCase() }))} placeholder="e.g. KG" />
          <Input label="To UOM" value={form.to_uom} onChange={(e) => setForm((f) => ({ ...f, to_uom: e.target.value.toUpperCase() }))} placeholder="e.g. G" />
          <Input label="Factor (from → to)" value={form.factor} onChange={(e) => setForm((f) => ({ ...f, factor: e.target.value }))} placeholder="e.g. 1000" type="number" step="any" />
          <p className="text-xs text-gray-500">1 {form.from_uom || "FROM"} = {form.factor || "?"} {form.to_uom || "TO"}</p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.from_uom || !form.to_uom || !form.factor}
              loading={createMutation.isPending}
            >Save</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Conversion">
        <p className="text-sm text-gray-700 mb-4">
          Delete conversion <strong>{deleteTarget?.from_uom} → {deleteTarget?.to_uom}</strong>?
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            variant="danger"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            loading={deleteMutation.isPending}
          >Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

// ── Number Series Tab ──────────────────────────────────────────────────────────

function previewNumber(prefix: string, padding: number, currentNumber: number, suffix?: string | null) {
  const next = (currentNumber ?? 0) + 1;
  const padded = String(next).padStart(padding ?? 4, "0");
  return `${prefix}${padded}${suffix ?? ""}`;
}

function NumberSeriesTab() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<NumberSeries | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<NumberSeries | null>(null);
  const [form, setForm] = useState<NumberSeriesCreate>({ module: "", label: "", prefix: "", suffix: null, current_number: 0, padding: 4, is_active: true });
  const [editData, setEditData] = useState<NumberSeriesUpdate>({});

  const { data: series = [], isLoading } = useQuery({
    queryKey: ["utilities", "series"],
    queryFn: () => utilitiesApi.numberSeries.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: NumberSeriesCreate) => utilitiesApi.numberSeries.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "series"] });
      setCreateOpen(false);
      setForm({ module: "", label: "", prefix: "", suffix: null, current_number: 0, padding: 4, is_active: true });
      toast("success", "Number series created");
    },
    onError: (err) => toast("error", "Failed to create series", extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: NumberSeriesUpdate }) =>
      utilitiesApi.numberSeries.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "series"] });
      setEditTarget(null);
      toast("success", "Number series updated");
    },
    onError: (err) => toast("error", "Update failed", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilitiesApi.numberSeries.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "series"] });
      setDeleteTarget(null);
      toast("success", "Number series deleted");
    },
    onError: (err) => toast("error", "Failed to delete", extractApiError(err)),
  });

  const openEdit = (s: NumberSeries) => {
    setEditTarget(s);
    setEditData({ label: s.label, prefix: s.prefix, suffix: s.suffix, current_number: s.current_number, padding: s.padding, is_active: s.is_active });
  };

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-500">{series.length} number series</p>
        <PermissionGuard permission="utilities.manage">
          <Button onClick={() => setCreateOpen(true)}>+ Add Series</Button>
        </PermissionGuard>
      </div>

      {isLoading ? <Spinner /> : (
        <Table
          keyField="id"
          data={series}
          emptyMessage="No number series configured."
          columns={[
            { header: "Module",      accessor: (r) => <code className="text-xs bg-gray-100 px-1 rounded">{r.module}</code> },
            { header: "Label",       accessor: (r) => r.label },
            { header: "Prefix",      accessor: (r) => <Badge label={r.prefix} variant="blue" /> },
            { header: "Current #",   accessor: (r) => String(r.current_number) },
            { header: "Next Number", accessor: (r) => <span className="font-mono text-sm text-green-700">{previewNumber(r.prefix, r.padding, r.current_number, r.suffix)}</span> },
            { header: "Status",      accessor: (r) => <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "gray"} /> },
            {
              header: "Actions",
              accessor: (r) => (
                <div className="flex gap-2">
                  <PermissionGuard permission="utilities.manage">
                    <Button variant="secondary" onClick={() => openEdit(r)}>Edit</Button>
                    <Button variant="danger" onClick={() => setDeleteTarget(r)}>Delete</Button>
                  </PermissionGuard>
                </div>
              ),
            },
          ]}
        />
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add Number Series">
        <div className="space-y-4">
          <Input label="Module key" value={form.module} onChange={(e) => setForm((f) => ({ ...f, module: e.target.value }))} placeholder="e.g. purchase_order" />
          <Input label="Label" value={form.label} onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))} placeholder="e.g. Purchase Order" />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Prefix" value={form.prefix} onChange={(e) => setForm((f) => ({ ...f, prefix: e.target.value }))} placeholder="e.g. PO-" />
            <Input label="Suffix (optional)" value={form.suffix ?? ""} onChange={(e) => setForm((f) => ({ ...f, suffix: e.target.value || null }))} placeholder="e.g. -KE" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Start at" type="number" value={String(form.current_number ?? 0)} onChange={(e) => setForm((f) => ({ ...f, current_number: parseInt(e.target.value) || 0 }))} />
            <Input label="Padding digits" type="number" value={String(form.padding ?? 4)} onChange={(e) => setForm((f) => ({ ...f, padding: parseInt(e.target.value) || 4 }))} />
          </div>
          {form.prefix && (
            <p className="text-xs text-gray-500">Preview: <span className="font-mono text-green-700">{previewNumber(form.prefix, form.padding ?? 4, form.current_number ?? 0, form.suffix)}</span></p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.module || !form.label || !form.prefix}
              loading={createMutation.isPending}
            >Save</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title={`Edit: ${editTarget?.label}`}>
        <div className="space-y-4">
          <Input label="Label" value={editData.label ?? ""} onChange={(e) => setEditData((d) => ({ ...d, label: e.target.value }))} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Prefix" value={editData.prefix ?? ""} onChange={(e) => setEditData((d) => ({ ...d, prefix: e.target.value }))} />
            <Input label="Suffix" value={editData.suffix ?? ""} onChange={(e) => setEditData((d) => ({ ...d, suffix: e.target.value || null }))} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Reset current #" type="number" value={String(editData.current_number ?? 0)} onChange={(e) => setEditData((d) => ({ ...d, current_number: parseInt(e.target.value) || 0 }))} />
            <Input label="Padding digits" type="number" value={String(editData.padding ?? 4)} onChange={(e) => setEditData((d) => ({ ...d, padding: parseInt(e.target.value) || 4 }))} />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={editData.is_active ?? true} onChange={(e) => setEditData((d) => ({ ...d, is_active: e.target.checked }))} />
            Active
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setEditTarget(null)}>Cancel</Button>
            <Button
              onClick={() => editTarget && updateMutation.mutate({ id: editTarget.id, data: editData })}
              loading={updateMutation.isPending}
            >Save</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Number Series">
        <p className="text-sm text-gray-700 mb-4">
          Delete series <strong>{deleteTarget?.label}</strong>? Document numbers already issued are not affected.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            variant="danger"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            loading={deleteMutation.isPending}
          >Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

// ── Currencies Tab ─────────────────────────────────────────────────────────────

function CurrenciesTab() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Currency | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Currency | null>(null);
  const [form, setForm] = useState<CurrencyCreate>({ code: "", name: "", symbol: "", exchange_rate: "1", is_base: false, is_active: true });
  const [editData, setEditData] = useState<CurrencyUpdate>({});

  const { data: currencies = [], isLoading } = useQuery({
    queryKey: ["utilities", "currencies"],
    queryFn: () => utilitiesApi.currencies.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: CurrencyCreate) => utilitiesApi.currencies.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "currencies"] });
      setCreateOpen(false);
      setForm({ code: "", name: "", symbol: "", exchange_rate: "1", is_base: false, is_active: true });
      toast("success", "Currency created");
    },
    onError: (err) => toast("error", "Failed to create currency", extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CurrencyUpdate }) =>
      utilitiesApi.currencies.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "currencies"] });
      setEditTarget(null);
      toast("success", "Currency updated");
    },
    onError: (err) => toast("error", "Update failed", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => utilitiesApi.currencies.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["utilities", "currencies"] });
      setDeleteTarget(null);
      toast("success", "Currency deleted");
    },
    onError: (err) => toast("error", "Failed to delete", extractApiError(err)),
  });

  const openEdit = (c: Currency) => {
    setEditTarget(c);
    setEditData({ name: c.name, symbol: c.symbol, exchange_rate: c.exchange_rate, is_base: c.is_base, is_active: c.is_active });
  };

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-gray-500">{currencies.length} currencies</p>
        <PermissionGuard permission="utilities.manage">
          <Button onClick={() => setCreateOpen(true)}>+ Add Currency</Button>
        </PermissionGuard>
      </div>

      {isLoading ? <Spinner /> : (
        <Table
          keyField="id"
          data={currencies}
          emptyMessage="No currencies configured."
          columns={[
            { header: "Code",   accessor: (r) => <Badge label={r.code} variant="blue" /> },
            { header: "Name",   accessor: (r) => r.name },
            { header: "Symbol", accessor: (r) => <span className="font-mono">{r.symbol}</span> },
            { header: "Rate",   accessor: (r) => <span className="font-mono text-sm">{r.exchange_rate}</span> },
            { header: "Base",   accessor: (r) => r.is_base ? <Badge label="Base" variant="green" /> : <span className="text-gray-400">—</span> },
            { header: "Status", accessor: (r) => <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "gray"} /> },
            {
              header: "Actions",
              accessor: (r) => (
                <div className="flex gap-2">
                  <PermissionGuard permission="utilities.edit">
                    <Button variant="secondary" onClick={() => openEdit(r)}>Edit</Button>
                  </PermissionGuard>
                  <PermissionGuard permission="utilities.manage">
                    <Button variant="danger" onClick={() => setDeleteTarget(r)} disabled={r.is_base}>
                      {r.is_base ? "Base" : "Delete"}
                    </Button>
                  </PermissionGuard>
                </div>
              ),
            },
          ]}
        />
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Add Currency">
        <div className="space-y-4">
          <Input label="Code (ISO 4217)" value={form.code} onChange={(e) => setForm((f) => ({ ...f, code: e.target.value.toUpperCase() }))} placeholder="e.g. KES" maxLength={10} />
          <Input label="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="e.g. Kenyan Shilling" />
          <Input label="Symbol" value={form.symbol} onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value }))} placeholder="e.g. KSh" />
          <Input label="Exchange Rate (vs base)" type="number" step="any" value={form.exchange_rate} onChange={(e) => setForm((f) => ({ ...f, exchange_rate: e.target.value }))} />
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_base ?? false} onChange={(e) => setForm((f) => ({ ...f, is_base: e.target.checked }))} />
              Set as base currency
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_active ?? true} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
              Active
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.code || !form.name || !form.symbol}
              loading={createMutation.isPending}
            >Save</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title={`Edit: ${editTarget?.code}`}>
        <div className="space-y-4">
          <Input label="Name" value={editData.name ?? ""} onChange={(e) => setEditData((d) => ({ ...d, name: e.target.value }))} />
          <Input label="Symbol" value={editData.symbol ?? ""} onChange={(e) => setEditData((d) => ({ ...d, symbol: e.target.value }))} />
          <Input label="Exchange Rate" type="number" step="any" value={editData.exchange_rate ?? "1"} onChange={(e) => setEditData((d) => ({ ...d, exchange_rate: e.target.value }))} />
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={editData.is_base ?? false} onChange={(e) => setEditData((d) => ({ ...d, is_base: e.target.checked }))} />
              Set as base currency
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={editData.is_active ?? true} onChange={(e) => setEditData((d) => ({ ...d, is_active: e.target.checked }))} />
              Active
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setEditTarget(null)}>Cancel</Button>
            <Button
              onClick={() => editTarget && updateMutation.mutate({ id: editTarget.id, data: editData })}
              loading={updateMutation.isPending}
            >Save</Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Currency">
        <p className="text-sm text-gray-700 mb-4">
          Delete currency <strong>{deleteTarget?.code} – {deleteTarget?.name}</strong>?
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            variant="danger"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            loading={deleteMutation.isPending}
          >Delete</Button>
        </div>
      </Modal>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function UtilitiesPage({ defaultTab }: { defaultTab?: Tab } = {}) {
  const [activeTab, setActiveTab] = useState<Tab>(defaultTab ?? "configs");

  return (
    <RequirePermission permission="utilities.view">
      <div>
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Utilities</h1>
          <p className="text-sm text-gray-500 mt-1">
            System configuration, unit-of-measure conversions, document numbering and currency management.
          </p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex gap-6">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {activeTab === "configs"    && <ConfigsTab />}
        {activeTab === "uom"        && <UomTab />}
        {activeTab === "series"     && <NumberSeriesTab />}
        {activeTab === "currencies" && <CurrenciesTab />}
      </div>
    </RequirePermission>
  );
}
