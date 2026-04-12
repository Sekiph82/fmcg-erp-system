"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { qualityApi, ParameterType } from "@/lib/quality";
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

const PARAM_TYPE_OPTS = [
  { value: "NUMERIC", label: "Numeric" },
  { value: "TEXT", label: "Text" },
  { value: "BOOLEAN", label: "Yes / No" },
  { value: "PASS_FAIL", label: "Pass / Fail" },
];

const APPLICABLE_OPTS = [
  { value: "ALL", label: "All QC Types" },
  { value: "INCOMING", label: "Incoming QC only" },
  { value: "IN_PROCESS", label: "In-Process QC only" },
  { value: "FINISHED_GOODS", label: "Finished Goods only" },
  { value: "INCOMING,IN_PROCESS", label: "Incoming + In-Process" },
  { value: "IN_PROCESS,FINISHED_GOODS", label: "In-Process + Finished Goods" },
];

// Pre-built chemical factory parameter templates
const TEMPLATES = [
  { name: "pH", parameter_type: "NUMERIC" as ParameterType, unit: "pH", min_value: "6.5", max_value: "7.5", is_critical: true, applicable_types: "ALL" },
  { name: "Viscosity", parameter_type: "NUMERIC" as ParameterType, unit: "cP", min_value: "", max_value: "", is_critical: true, applicable_types: "IN_PROCESS,FINISHED_GOODS" },
  { name: "Temperature", parameter_type: "NUMERIC" as ParameterType, unit: "°C", min_value: "", max_value: "", is_critical: false, applicable_types: "IN_PROCESS" },
  { name: "Appearance", parameter_type: "TEXT" as ParameterType, unit: "", min_value: "", max_value: "", is_critical: false, applicable_types: "ALL" },
  { name: "Moisture Content", parameter_type: "NUMERIC" as ParameterType, unit: "%", min_value: "", max_value: "5.0", is_critical: true, applicable_types: "INCOMING,FINISHED_GOODS" },
  { name: "Specific Gravity", parameter_type: "NUMERIC" as ParameterType, unit: "g/mL", min_value: "", max_value: "", is_critical: false, applicable_types: "ALL" },
  { name: "Color Conformance", parameter_type: "PASS_FAIL" as ParameterType, unit: "", min_value: "", max_value: "", is_critical: false, applicable_types: "FINISHED_GOODS" },
  { name: "Label Check", parameter_type: "PASS_FAIL" as ParameterType, unit: "", min_value: "", max_value: "", is_critical: true, applicable_types: "FINISHED_GOODS" },
  { name: "Net Weight", parameter_type: "NUMERIC" as ParameterType, unit: "g", min_value: "", max_value: "", is_critical: true, applicable_types: "FINISHED_GOODS" },
  { name: "Purity", parameter_type: "NUMERIC" as ParameterType, unit: "%", min_value: "98.0", max_value: "100.0", is_critical: true, applicable_types: "INCOMING,FINISHED_GOODS" },
];

export default function QCParametersPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "", parameter_type: "NUMERIC" as ParameterType, unit: "",
    min_value: "", max_value: "", expected_value: "",
    is_critical: false, applicable_types: "ALL", description: "",
  });

  const { data: parameters = [], isLoading } = useQuery({
    queryKey: ["qc-parameters"],
    queryFn: () => qualityApi.listParameters({ active_only: false }),
  });

  const create = useMutation({
    mutationFn: () => qualityApi.createParameter({
      ...form,
      min_value: form.min_value ? parseFloat(form.min_value) : undefined,
      max_value: form.max_value ? parseFloat(form.max_value) : undefined,
      expected_value: form.expected_value || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["qc-parameters"] });
      setOpen(false);
      toast("success", "Parameter created", "");
    },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const toggleActive = useMutation({
    mutationFn: (p: { id: string; is_active: boolean }) => qualityApi.updateParameter(p.id, { is_active: !p.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["qc-parameters"] }),
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => qualityApi.deleteParameter(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["qc-parameters"] });
      toast("success", "Parameter deleted", "");
      setDeletingId(null);
    },
    onError: (e) => toast("error", "Failed to delete", extractApiError(e)),
  });

  const deletingParam = parameters.find((p) => p.id === deletingId);

  const fillTemplate = (t: typeof TEMPLATES[0]) => {
    setForm((f) => ({
      ...f,
      name: t.name,
      parameter_type: t.parameter_type,
      unit: t.unit,
      min_value: t.min_value,
      max_value: t.max_value,
      is_critical: t.is_critical,
      applicable_types: t.applicable_types,
    }));
  };

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">QC Parameters</h1>
          <p className="text-sm text-gray-500 mt-1">Reusable test parameter templates for QC inspections</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal
            module="qc_parameters"
            onSuccess={() => qc.invalidateQueries({ queryKey: ["qc-parameters"] })}
          />
          <Button onClick={() => setOpen(true)}>+ New Parameter</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <Table
          keyField="id"
          data={parameters}
          emptyMessage="No parameters. Add templates to speed up QC data entry."
          columns={[
            { header: "Name", accessor: "name", className: "font-medium" },
            { header: "Type", accessor: (p) => <span className="text-xs text-gray-500">{p.parameter_type}</span> },
            { header: "Unit", accessor: (p) => p.unit || "—" },
            {
              header: "Spec Range",
              accessor: (p) => {
                if (p.parameter_type === "NUMERIC") {
                  if (p.min_value != null && p.max_value != null) return `${p.min_value} – ${p.max_value}`;
                  if (p.min_value != null) return `≥ ${p.min_value}`;
                  if (p.max_value != null) return `≤ ${p.max_value}`;
                }
                return p.expected_value || "—";
              },
            },
            { header: "Critical", accessor: (p) => p.is_critical ? <Badge label="Critical" variant="red" /> : <span className="text-gray-300 text-xs">—</span> },
            { header: "Applicable To", accessor: (p) => <span className="text-xs text-gray-500">{p.applicable_types === "ALL" ? "All QC Types" : p.applicable_types.replace(/,/g, " + ").replace(/_/g, " ")}</span> },
            {
              header: "Status",
              accessor: (p) => <Badge label={p.is_active ? "Active" : "Inactive"} variant={p.is_active ? "green" : "red"} />,
            },
            {
              header: "",
              accessor: (p) => (
                <div className="flex items-center justify-end gap-3">
                  <button className="text-xs text-gray-400 hover:text-gray-600" onClick={() => toggleActive.mutate({ id: p.id, is_active: p.is_active })}>
                    {p.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button className="text-xs text-red-500 hover:text-red-700 hover:underline" onClick={() => setDeletingId(p.id)}>
                    Delete
                  </button>
                </div>
              ),
            },
          ]}
        />
      )}

      {/* Delete Confirm Modal */}
      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title="Delete QC Parameter">
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete the parameter{" "}
          <span className="font-semibold text-gray-900">{deletingParam?.name}</span>?
          This action cannot be undone.
        </p>
        {deleteMutation.error && <p className="text-sm text-red-600 mb-3">Failed to delete parameter.</p>}
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeletingId(null)}>Cancel</Button>
          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={() => deletingId && deleteMutation.mutate(deletingId)}
          >
            Delete
          </Button>
        </div>
      </Modal>

      <Modal open={open} onClose={() => setOpen(false)} title="New QC Parameter">
        <div className="space-y-4">
          <div>
            <p className="text-xs text-gray-500 mb-2">Quick templates (chemical factory):</p>
            <div className="flex flex-wrap gap-1.5">
              {TEMPLATES.map((t) => (
                <button key={t.name} className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 rounded px-2 py-1 border border-blue-200" onClick={() => fillTemplate(t)}>
                  {t.name}
                </button>
              ))}
            </div>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Input label="Name *" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
              <Select label="Type *" options={PARAM_TYPE_OPTS} value={form.parameter_type} onChange={(e) => setForm((f) => ({ ...f, parameter_type: e.target.value as ParameterType }))} />
            </div>
            <Input label="Unit" value={form.unit} onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))} placeholder="e.g. cP, °C, pH, %" />
            {form.parameter_type === "NUMERIC" && (
              <div className="grid grid-cols-2 gap-4">
                <Input label="Min Spec" type="number" step="any" value={form.min_value} onChange={(e) => setForm((f) => ({ ...f, min_value: e.target.value }))} />
                <Input label="Max Spec" type="number" step="any" value={form.max_value} onChange={(e) => setForm((f) => ({ ...f, max_value: e.target.value }))} />
              </div>
            )}
            {(form.parameter_type === "TEXT" || form.parameter_type === "BOOLEAN") && (
              <Input label="Expected Value" value={form.expected_value} onChange={(e) => setForm((f) => ({ ...f, expected_value: e.target.value }))} placeholder="e.g. Clear liquid, true" />
            )}
            <Select label="Applicable QC Types" options={APPLICABLE_OPTS} value={form.applicable_types} onChange={(e) => setForm((f) => ({ ...f, applicable_types: e.target.value }))} />
            <Input label="Description" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
            <div className="flex items-center gap-2">
              <input type="checkbox" id="is_crit" checked={form.is_critical} onChange={(e) => setForm((f) => ({ ...f, is_critical: e.target.checked }))} />
              <label htmlFor="is_crit" className="text-sm text-gray-700">Mark as critical parameter</label>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" loading={create.isPending} disabled={!form.name}>Create Parameter</Button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
}
