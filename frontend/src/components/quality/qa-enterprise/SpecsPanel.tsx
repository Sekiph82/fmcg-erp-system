"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { type ChangeRequest, type ChangeStatus, type ChangeType, qaEnterpriseApi } from "@/lib/qa-enterprise";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import {
  LoadError, type Notify, ReadOnlyNotice, Section, TextArea, shortId, statusVariant, todayIso,
  useAction, useQualityPermissions,
} from "./shared";

const NEXT_STEPS: Record<ChangeStatus, Array<{ status: ChangeStatus; label: string; approve?: boolean }>> = {
  DRAFT: [{ status: "SUBMITTED", label: "Submit" }, { status: "CANCELLED", label: "Cancel" }],
  SUBMITTED: [{ status: "APPROVED", label: "Approve", approve: true }, { status: "REJECTED", label: "Reject", approve: true },
    { status: "CANCELLED", label: "Cancel" }],
  APPROVED: [{ status: "IMPLEMENTED", label: "Mark implemented" }],
  IMPLEMENTED: [{ status: "CLOSED", label: "Close", approve: true }],
  REJECTED: [], CANCELLED: [], CLOSED: [],
};

export function SpecsPanel({ notify }: { notify: Notify }) {
  const perms = useQualityPermissions();
  const specs = useQuery({ queryKey: ["qa-specs"], queryFn: qaEnterpriseApi.listSpecifications, enabled: perms.canView });
  const crs = useQuery({ queryKey: ["qa-change-requests"], queryFn: qaEnterpriseApi.listChangeRequests, enabled: perms.canView });
  const templates = useQuery({
    queryKey: ["qa-templates"],
    queryFn: async () => (await apiClient.get<Array<{ id: string; name: string; is_active: boolean }>>("/api/v1/qms/templates")).data,
    enabled: perms.canCreate,
  });

  const [spec, setSpec] = useState({
    spec_code: "", name: "", scope_type: "PRODUCT", scope_ref: "", template_id: "",
    effective_from: todayIso(), change_request_id: "", change_reason: "",
  });
  const [cr, setCr] = useState({ title: "", change_type: "SPECIFICATION" as ChangeType, target_reference: "",
    description: "", risk_assessment: "" });
  const [crNotes, setCrNotes] = useState<Record<string, string>>({});

  const createSpec = useAction(qaEnterpriseApi.createSpecification, notify,
    (s) => `Specification ${s.spec_code} v${s.version} saved as draft`, ["qa-specs"]);
  const approveSpec = useAction(qaEnterpriseApi.approveSpecification, notify,
    (s) => `Specification ${s.spec_code} v${s.version} approved`, ["qa-specs"]);
  const createCr = useAction(qaEnterpriseApi.createChangeRequest, notify, (c) => `Change request ${c.cr_no} created`,
    ["qa-change-requests"]);
  const transitionCr = useAction(
    (a: { id: string; status: ChangeStatus; notes?: string }) => qaEnterpriseApi.transitionChangeRequest(a.id, a.status, a.notes),
    notify, (c) => `${c.cr_no} is now ${c.status}`, ["qa-change-requests"]);

  const submitSpec = () => {
    const scopeKey = spec.scope_type === "PRODUCT" ? "product_id" : spec.scope_type === "MATERIAL" ? "material_id" : "process_stage";
    createSpec.mutate({
      spec_code: spec.spec_code.trim(), name: spec.name.trim(), scope_type: spec.scope_type,
      [scopeKey]: spec.scope_ref.trim(), template_id: spec.template_id, effective_from: spec.effective_from,
      change_request_id: spec.change_request_id || undefined, change_reason: spec.change_reason || undefined,
    });
  };

  if (!perms.canView) return <ReadOnlyNotice>Specifications require quality.view.</ReadOnlyNotice>;
  const approvedCrs = (crs.data ?? []).filter((c) => c.status === "APPROVED" || c.status === "IMPLEMENTED");

  return (
    <div className="space-y-4">
      <Section title="Specifications" description="Versioned, effective-dated specifications. The author cannot approve; version 2+ needs an approved change request.">
        {specs.error ? <LoadError error={specs.error} /> : (
          <Table
            keyField="id"
            data={specs.data ?? []}
            emptyMessage="No specifications yet."
            columns={[
              { header: "Code", accessor: (s) => `${s.spec_code} v${s.version}` },
              { header: "Name", accessor: "name" },
              { header: "Scope", accessor: (s) => `${s.scope_type} ${s.process_stage ?? shortId(s.product_id ?? s.material_id)}` },
              { header: "Effective", accessor: (s) => `${s.effective_from} → ${s.effective_to ?? "open"}` },
              { header: "Status", accessor: (s) => <Badge label={s.status} variant={statusVariant(s.status)} /> },
              {
                header: "Actions",
                accessor: (s) => s.status === "DRAFT" && perms.canApprove ? (
                  <Button variant="secondary" onClick={() => approveSpec.mutate(s.id)} loading={approveSpec.isPending}
                    aria-label={`Approve ${s.spec_code} v${s.version}`}>Approve</Button>
                ) : null,
              },
            ]}
          />
        )}
        {perms.canCreate && (
          <form className="grid gap-3 md:grid-cols-3" onSubmit={(e) => { e.preventDefault(); submitSpec(); }}>
            <Input id="spec-code" label="Spec code" value={spec.spec_code} required
              onChange={(e) => setSpec((s) => ({ ...s, spec_code: e.target.value }))} />
            <Input id="spec-name" label="Spec name" value={spec.name} required
              onChange={(e) => setSpec((s) => ({ ...s, name: e.target.value }))} />
            <Select id="spec-scope" label="Scope" value={spec.scope_type}
              onChange={(e) => setSpec((s) => ({ ...s, scope_type: e.target.value }))}
              options={[{ value: "PRODUCT", label: "Product" }, { value: "MATERIAL", label: "Material" },
                { value: "PROCESS", label: "Process stage" }]} />
            <Input id="spec-scope-ref" required value={spec.scope_ref}
              label={spec.scope_type === "PROCESS" ? "Process stage" : `${spec.scope_type === "PRODUCT" ? "Product" : "Material"} ID`}
              onChange={(e) => setSpec((s) => ({ ...s, scope_ref: e.target.value }))} />
            <Select id="spec-template" label="Parameter template" value={spec.template_id} required
              onChange={(e) => setSpec((s) => ({ ...s, template_id: e.target.value }))}
              options={[{ value: "", label: "Select template" },
                ...(templates.data ?? []).filter((t) => t.is_active).map((t) => ({ value: t.id, label: t.name }))]} />
            <Input id="spec-effective" label="Effective from" type="date" min={todayIso()} value={spec.effective_from}
              onChange={(e) => setSpec((s) => ({ ...s, effective_from: e.target.value }))} />
            <Select id="spec-cr" label="Change request" value={spec.change_request_id}
              onChange={(e) => setSpec((s) => ({ ...s, change_request_id: e.target.value }))}
              options={[{ value: "", label: "None (first version)" },
                ...approvedCrs.map((c) => ({ value: c.id, label: `${c.cr_no} — ${c.target_reference ?? c.title}` }))]} />
            <div className="md:col-span-2">
              <Input id="spec-reason" label="Change reason" value={spec.change_reason}
                onChange={(e) => setSpec((s) => ({ ...s, change_reason: e.target.value }))} />
            </div>
            <div className="md:col-span-3 flex justify-end">
              <Button type="submit" loading={createSpec.isPending}
                disabled={!spec.spec_code || !spec.name || !spec.scope_ref || !spec.template_id}>Save draft specification</Button>
            </div>
          </form>
        )}
      </Section>

      <Section title="Change control" description="Draft → submitted → approved → implemented → closed. The requester cannot approve their own change.">
        {crs.error ? <LoadError error={crs.error} /> : (
          <Table<ChangeRequest>
            keyField="id"
            data={crs.data ?? []}
            emptyMessage="No change requests."
            columns={[
              { header: "Ref", accessor: "cr_no" },
              { header: "Title", accessor: "title" },
              { header: "Type", accessor: "change_type" },
              { header: "Target", accessor: (c) => c.target_reference ?? "—" },
              { header: "Status", accessor: (c) => <Badge label={c.status} variant={statusVariant(c.status)} /> },
              {
                header: "Next step",
                accessor: (c) => {
                  const steps = NEXT_STEPS[c.status].filter((s) => (s.approve ? perms.canApprove : perms.canEdit || perms.canApprove));
                  if (!steps.length) return null;
                  return (
                    <div className="flex flex-wrap items-center gap-2">
                      {c.status === "IMPLEMENTED" && (
                        <input aria-label={`Verification notes for ${c.cr_no}`} placeholder="Verification notes"
                          className="rounded border border-gray-300 px-2 py-1 text-xs"
                          value={crNotes[c.id] ?? ""} onChange={(e) => setCrNotes((n) => ({ ...n, [c.id]: e.target.value }))} />
                      )}
                      {steps.map((s) => (
                        <Button key={s.status} variant={s.status === "REJECTED" || s.status === "CANCELLED" ? "danger" : "secondary"}
                          aria-label={`${s.label} ${c.cr_no}`} loading={transitionCr.isPending}
                          onClick={() => transitionCr.mutate({ id: c.id, status: s.status, notes: crNotes[c.id] })}>
                          {s.label}
                        </Button>
                      ))}
                    </div>
                  );
                },
              },
            ]}
          />
        )}
        {perms.canCreate && (
          <form className="grid gap-3 md:grid-cols-2" onSubmit={(e) => { e.preventDefault(); createCr.mutate({
            ...cr, target_reference: cr.target_reference || undefined, risk_assessment: cr.risk_assessment || undefined }); }}>
            <Input id="cr-title" label="Change title" required value={cr.title} onChange={(e) => setCr((c) => ({ ...c, title: e.target.value }))} />
            <Select id="cr-type" label="Change type" value={cr.change_type}
              onChange={(e) => setCr((c) => ({ ...c, change_type: e.target.value as ChangeType }))}
              options={["SPECIFICATION", "QC_PLAN", "TEST_METHOD", "PROCESS", "OTHER"].map((v) => ({ value: v, label: v.replace("_", " ") }))} />
            <Input id="cr-target" label="Target reference" placeholder="e.g. SPEC-PH" value={cr.target_reference}
              onChange={(e) => setCr((c) => ({ ...c, target_reference: e.target.value }))} />
            <div />
            <TextArea id="cr-description" label="Description" value={cr.description} onChange={(v) => setCr((c) => ({ ...c, description: v }))} />
            <TextArea id="cr-risk" label="Risk assessment" value={cr.risk_assessment} onChange={(v) => setCr((c) => ({ ...c, risk_assessment: v }))} />
            <div className="md:col-span-2 flex justify-end">
              <Button type="submit" loading={createCr.isPending} disabled={!cr.title || !cr.description}>Create change request</Button>
            </div>
          </form>
        )}
      </Section>
    </div>
  );
}
