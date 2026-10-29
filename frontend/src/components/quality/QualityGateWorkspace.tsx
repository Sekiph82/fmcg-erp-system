"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import {
  type GateAuditResult,
  type GateQCType,
  type GateTrigger,
  type QualityGateDefinitionCreate,
  type QualityGateSeverity,
  qualityGatesApi,
} from "@/lib/quality-gates";

const SCOPE_OPTIONS: Array<{
  key: string;
  label: string;
  targetModule: string;
  trigger: GateTrigger;
  qcType: GateQCType;
  gateType: string;
}> = [
  { key: "receiving", label: "Receiving", targetModule: "procurement", trigger: "ON_RECEIPT", qcType: "INCOMING", gateType: "INCOMING_QUALITY" },
  { key: "production-release", label: "Production release", targetModule: "production", trigger: "ON_PRODUCTION_RELEASE", qcType: "IN_PROCESS", gateType: "PRODUCTION_RELEASE_QUALITY" },
  { key: "in-process", label: "Production in-process", targetModule: "production", trigger: "ON_IN_PROCESS", qcType: "IN_PROCESS", gateType: "IN_PROCESS_QUALITY" },
  { key: "finished-goods", label: "Finished-goods release", targetModule: "inventory", trigger: "ON_FINISHED_GOODS_RELEASE", qcType: "FINISHED_GOODS", gateType: "FINISHED_GOODS_RELEASE_QUALITY" },
  { key: "dispatch", label: "Dispatch", targetModule: "sales", trigger: "ON_DISPATCH", qcType: "FINISHED_GOODS", gateType: "FINISHED_GOODS_DISPATCH_QUALITY" },
];

const AUDIT_RESULTS: Array<{ value: string; label: string }> = [
  { value: "", label: "All outcomes" },
  { value: "PASS", label: "Pass" },
  { value: "BLOCKED", label: "Blocked" },
  { value: "WAIVED", label: "Waived" },
  { value: "NO_GATE", label: "No gate" },
];

const severityVariant = (severity: QualityGateSeverity) =>
  severity === "CRITICAL" ? "red" : severity === "HIGH" ? "yellow" : severity === "MEDIUM" ? "blue" : "gray";

const resultVariant = (result: GateAuditResult) =>
  result === "PASS" ? "green" : result === "BLOCKED" ? "red" : result === "WAIVED" ? "yellow" : "gray";

function todayLocal(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function addIsoDay(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  const next = new Date(year, month - 1, day + 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}`;
}

function versionState(definitions: Array<{ code: string; version: number; effective_from: string; effective_to?: string | null }>, code: string) {
  const matching = definitions
    .filter((item) => item.code.trim().toUpperCase() === code.trim().toUpperCase())
    .sort((a, b) => b.version - a.version);
  const latest = matching[0];
  const openVersions = matching.filter((item) => !item.effective_to);
  const closeThrough = latest ? (latest.effective_from > todayLocal() ? latest.effective_from : todayLocal()) : todayLocal();
  const earliestStart = latest?.effective_to
    ? (addIsoDay(latest.effective_to) > todayLocal() ? addIsoDay(latest.effective_to) : todayLocal())
    : latest
      ? addIsoDay(closeThrough)
      : todayLocal();
  return { nextVersion: (latest?.version ?? 0) + 1, latest, openVersions, closeThrough, earliestStart };
}

function errorMessage(error: unknown): string {
  const candidate = error as { response?: { data?: { detail?: unknown } }; message?: string };
  const detail = candidate.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "detail" in detail && typeof detail.detail === "string") return detail.detail;
  return candidate.message || "The request could not be completed.";
}

export function QualityGateWorkspace() {
  const queryClient = useQueryClient();
  const { hasAnyPermission, hasPermission } = useAuth();
  const { toasts, toast, dismiss } = useToast();
  const canViewDefinitions = hasAnyPermission(["quality.view_all", "quality.gate_configure"]);
  const canViewAudit = hasAnyPermission(["quality.view", "quality.view_all", "quality.gate_configure"]);
  const canConfigure = hasPermission("quality.gate_configure");
  const [createOpen, setCreateOpen] = useState(false);
  const [auditResult, setAuditResult] = useState("");
  const [scopeKey, setScopeKey] = useState(SCOPE_OPTIONS[0].key);
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>([]);
  const [createError, setCreateError] = useState("");
  const [form, setForm] = useState({
    code: "",
    name: "",
    description: "",
    effectiveFrom: todayLocal(),
    severity: "MEDIUM" as QualityGateSeverity,
    mandatory: true,
    waiverAllowed: false,
  });

  const definitionsQuery = useQuery({
    queryKey: ["quality-gate-definitions"],
    queryFn: qualityGatesApi.listDefinitions,
    enabled: canViewDefinitions,
  });
  const auditQuery = useQuery({
    queryKey: ["quality-gate-audit", auditResult],
    queryFn: () => qualityGatesApi.listAuditHistory(auditResult ? auditResult as GateAuditResult : undefined),
    enabled: canViewAudit,
  });
  const scope = SCOPE_OPTIONS.find((item) => item.key === scopeKey) ?? SCOPE_OPTIONS[0];
  const templatesQuery = useQuery({
    queryKey: ["quality-gate-templates", scope.qcType],
    queryFn: () => qualityGatesApi.listTemplates(scope.qcType),
    enabled: createOpen && canConfigure,
  });
  const templates = useMemo(
    () => (templatesQuery.data ?? []).filter((template) =>
      template.is_active
      && template.is_mandatory
      && template.blocks_progression
      && template.release_required
      && template.parameters.length > 0
      && template.parameters.every((parameter) => {
        const target = (parameter.target_value ?? "").trim();
        if (parameter.parameter_type === "NUMERIC") {
          return target !== "" || parameter.min_value != null || parameter.max_value != null;
        }
        if (parameter.parameter_type === "TEXT") return target !== "";
        if (parameter.parameter_type === "BOOLEAN") return ["true", "false"].includes(target.toLowerCase());
        return parameter.parameter_type === "PASS_FAIL" && target !== "";
      }),
    ),
    [templatesQuery.data],
  );

  const createDefinition = useMutation({
    mutationFn: (data: QualityGateDefinitionCreate) => qualityGatesApi.createDefinition(data),
    onSuccess: async (definition) => {
      await queryClient.invalidateQueries({ queryKey: ["quality-gate-definitions"] });
      setCreateOpen(false);
      setSelectedTemplateIds([]);
      setForm({ code: "", name: "", description: "", effectiveFrom: todayLocal(), severity: "MEDIUM", mandatory: true, waiverAllowed: false });
      toast("success", "Gate definition created", `${definition.code} v${definition.version} is saved.`);
    },
    onError: (error) => setCreateError(errorMessage(error)),
  });
  const closeDefinition = useMutation({
    mutationFn: (definition: { id: string; effective_from: string }) => qualityGatesApi.updateDefinition(
      definition.id,
      { effective_to: definition.effective_from > todayLocal() ? definition.effective_from : todayLocal() },
    ),
    onSuccess: async (_updated, definition) => {
      await queryClient.invalidateQueries({ queryKey: ["quality-gate-definitions"] });
      const closedThrough = definition.effective_from > todayLocal() ? definition.effective_from : todayLocal();
      setForm((current) => ({ ...current, effectiveFrom: addIsoDay(closedThrough) }));
      toast("success", "Gate version closed", "The next version must start after the closed effective period.");
    },
    onError: (error) => toast("error", "Could not close gate version", errorMessage(error)),
  });

  const definitions = definitionsQuery.data ?? [];
  const auditEvents = auditQuery.data ?? [];
  const currentVersionState = versionState(definitions, form.code);
  const canSubmit = Boolean(
    form.code.trim()
    && form.name.trim()
    && form.effectiveFrom
    && selectedTemplateIds.length > 0
    && currentVersionState.openVersions.length === 0
    && form.effectiveFrom >= currentVersionState.earliestStart
    && !(form.severity === "CRITICAL" && (!form.mandatory || form.waiverAllowed))
  );

  const submitDefinition = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateError("");
    createDefinition.mutate({
      code: form.code,
      name: form.name,
      description: form.description,
      gate_type: scope.gateType,
      target_module: scope.targetModule,
      trigger_event: scope.trigger,
      is_active: true,
      version: currentVersionState.nextVersion,
      effective_from: form.effectiveFrom,
      severity: form.severity,
      is_mandatory: form.mandatory,
      waiver_allowed: form.waiverAllowed,
      waiver_reason_required: true,
      waiver_approval_required: true,
      required_template_ids: selectedTemplateIds,
    });
  };

  if (!canViewAudit) {
    return (
      <div className="m-6 rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900" role="alert">
        Gate evaluation history requires a quality view permission.
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6" data-testid="quality-gate-workspace">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Quality gate definitions</h2>
          <p className="mt-1 max-w-3xl text-sm text-gray-600">
            Review versioned controls for receiving, production, finished-goods release, and dispatch. Each active mandatory gate links specification-backed QC templates.
          </p>
        </div>
        {canConfigure && <Button onClick={() => { setCreateError(""); setCreateOpen(true); }}>Create gate definition</Button>}
      </div>

      {canViewDefinitions ? (
        <>
          {definitionsQuery.isLoading ? <p role="status" className="py-8 text-center text-sm text-gray-500">Loading gate definitions…</p> : null}
          {definitionsQuery.isError ? <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">Could not load gate definitions: {errorMessage(definitionsQuery.error)}</p> : null}
          {!definitionsQuery.isLoading && !definitionsQuery.isError && definitions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-600">
              No gate definitions are configured yet.{canConfigure ? " Create the first version to apply mandatory QC controls." : ""}
            </div>
          ) : null}
          {definitions.length > 0 && (
            <Table
              keyField="id"
              data={definitions}
              emptyMessage="No gate definitions are available."
              columns={[
                { header: "Gate", accessor: (item) => <span><strong>{item.name}</strong><span className="ml-2 font-mono text-xs text-gray-500">{item.code} v{item.version}</span></span> },
                { header: "Scope", accessor: (item) => <span>{item.target_module} · {item.trigger_event}</span> },
                { header: "Required QC", accessor: (item) => item.required_templates.map((template) => template.name).join(", ") || "No templates" },
                { header: "Policy", accessor: (item) => <span className="flex flex-wrap gap-1"><Badge label={item.severity} variant={severityVariant(item.severity)} /><Badge label={item.is_mandatory ? "Mandatory" : "Optional"} variant={item.is_mandatory ? "blue" : "gray"} /><Badge label={item.is_active ? "Active" : "Inactive"} variant={item.is_active ? "green" : "gray"} /></span> },
                { header: "Effective", accessor: (item) => <span className="flex flex-wrap items-center gap-2">{`${item.effective_from}${item.effective_to ? ` – ${item.effective_to}` : " – open"}`}{canConfigure && !item.effective_to && <Button type="button" variant="secondary" className="!px-2 !py-1 text-xs" loading={closeDefinition.isPending} onClick={() => closeDefinition.mutate(item)}>Close version</Button>}</span> },
              ]}
            />
          )}
        </>
      ) : (
        <p className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">
          Gate definition details require quality.view_all or quality.gate_configure. You can still review evaluation history below.
        </p>
      )}

      <section className="space-y-3" aria-labelledby="gate-audit-heading">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 id="gate-audit-heading" className="text-lg font-semibold text-gray-900">Recent gate evaluations</h3>
            <p className="text-sm text-gray-600">Append-only history of pass, blocked, waived, and no-gate decisions.</p>
          </div>
          <Select
            label="Outcome"
            aria-label="Filter audit outcome"
            className="min-w-40"
            options={AUDIT_RESULTS}
            value={auditResult}
            onChange={(event) => setAuditResult(event.target.value)}
          />
        </div>
        {auditQuery.isLoading ? <p role="status" className="py-6 text-center text-sm text-gray-500">Loading gate evaluations…</p> : null}
        {auditQuery.isError ? <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">Could not load gate evaluations: {errorMessage(auditQuery.error)}</p> : null}
        {!auditQuery.isLoading && !auditQuery.isError && auditEvents.length === 0 ? (
          <p className="rounded-lg border border-gray-200 bg-white p-5 text-center text-sm text-gray-500">No evaluations match this outcome.</p>
        ) : null}
        {auditEvents.length > 0 && (
          <Table
            keyField="id"
            data={auditEvents}
            columns={[
              { header: "Evaluated", accessor: (item) => new Date(item.evaluated_at).toLocaleString() },
              { header: "Gate", accessor: (item) => `${item.gate_code} v${item.gate_version}` },
              { header: "Decision", accessor: (item) => <Badge label={item.result} variant={resultVariant(item.result)} /> },
              { header: "Actor ID", accessor: (item) => item.evaluated_by_id || "System" },
              { header: "Scope", accessor: (item) => `${item.scope_type} · ${item.business_type}` },
              { header: "Reason", accessor: (item) => item.reason || "—" },
            ]}
          />
        )}
      </section>

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Create first gate version">
        <form className="max-h-[calc(100vh-10rem)] space-y-4 overflow-y-auto pr-2" onSubmit={submitDefinition} data-testid="quality-gate-create-form">
          <p className="text-sm text-gray-600">Gate rules are immutable once effective. Close the current version before saving the next sequential version.</p>
          <Input id="quality-gate-code" label="Gate code" value={form.code} onChange={(event) => {
            const code = event.target.value;
            const version = versionState(definitions, code);
            setForm((current) => ({ ...current, code, effectiveFrom: version.earliestStart }));
          }} required maxLength={50} placeholder="e.g. RECEIVING_QC" />
          <p className="text-xs text-gray-500">Version {currentVersionState.nextVersion}; earliest start date {currentVersionState.earliestStart}.</p>
          {currentVersionState.openVersions.length > 0 && (
            <p role="alert" className="rounded bg-amber-50 p-3 text-sm text-amber-900">
              Close the current {form.code.toUpperCase()} version before creating its next version.
            </p>
          )}
          <Input id="quality-gate-name" label="Name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required maxLength={120} />
          <Input id="quality-gate-description" label="Description" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
          <Select
            label="Applies to"
            options={SCOPE_OPTIONS.map((item) => ({ value: item.key, label: item.label }))}
            value={scopeKey}
            onChange={(event) => { setScopeKey(event.target.value); setSelectedTemplateIds([]); }}
          />
          <p className="text-xs text-gray-500">{scope.targetModule} · {scope.trigger} · {scope.qcType} QC</p>
          <Input id="quality-gate-effective-from" label="Effective from" type="date" min={currentVersionState.earliestStart} value={form.effectiveFrom} onChange={(event) => setForm((current) => ({ ...current, effectiveFrom: event.target.value }))} required />
          <Select
            label="Severity"
            options={["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => ({ value, label: value }))}
            value={form.severity}
            onChange={(event) => setForm((current) => ({ ...current, severity: event.target.value as QualityGateSeverity }))}
          />
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.mandatory} onChange={(event) => setForm((current) => ({ ...current, mandatory: event.target.checked }))} /> Mandatory gate</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.waiverAllowed} onChange={(event) => setForm((current) => ({ ...current, waiverAllowed: event.target.checked }))} /> Allow a reasoned, independently approved waiver</label>
          {form.waiverAllowed && <p className="text-xs text-amber-800">Every waiver requires a reason and quality approval. Critical gates cannot be waived.</p>}

          <fieldset className="space-y-2 rounded-lg border border-gray-200 p-3">
            <legend className="px-1 text-sm font-medium">Required specification-backed QC templates</legend>
            {templatesQuery.isLoading ? <p role="status" className="text-sm text-gray-500">Loading {scope.qcType} templates…</p> : null}
            {templatesQuery.isError ? <p role="alert" className="text-sm text-red-700">Could not load QC templates: {errorMessage(templatesQuery.error)}</p> : null}
            {!templatesQuery.isLoading && templates.length === 0 ? <p className="text-sm text-gray-600">No active mandatory blocking templates with specification parameters match this gate scope.</p> : null}
            {templates.map((template) => (
              <label key={template.id} className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  aria-label={`Required template: ${template.name}`}
                  checked={selectedTemplateIds.includes(template.id)}
                  onChange={(event) => setSelectedTemplateIds((current) => event.target.checked ? [...current, template.id] : current.filter((id) => id !== template.id))}
                />
                <span>{template.name}<span className="ml-2 text-xs text-gray-500">{template.parameters.length} specified checks</span></span>
              </label>
            ))}
          </fieldset>
          {createError && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{createError}</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createDefinition.isPending} disabled={!canSubmit || templatesQuery.isLoading || templatesQuery.isError || selectedTemplateIds.length === 0}>Save gate definition</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
