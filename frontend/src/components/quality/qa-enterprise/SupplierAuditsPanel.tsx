"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  type AuditItemResult, SUPPLIER_APPROVAL_NEXT, type SupplierApproval, type SupplierApprovalStatus, type SupplierAudit,
  supplierAuditApi,
} from "@/lib/qa-enterprise";
import { suppliersApi } from "@/lib/suppliers";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import {
  LoadError, type Notify, ReadOnlyNotice, Section, TextArea, addDaysIso, shortId, statusVariant, todayIso,
  useAction, useQualityPermissions,
} from "./shared";

const STANDARDS = ["BRC", "FSSC_22000", "ISO_22000", "HALAL", "KOSHER", "HACCP_CODEX", "SQF", "CUSTOM"];
const NEEDS_NOTES: SupplierApprovalStatus[] = ["CONDITIONAL", "SUSPENDED", "REJECTED"];

/** Supplier picker that falls back to a plain ID field when the user cannot list suppliers. */
function SupplierField({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) {
  const suppliers = useQuery({ queryKey: ["qa-supplier-options"], queryFn: () => suppliersApi.list(0, 200), retry: false });
  if (suppliers.data?.length) {
    return (
      <Select id={id} label="Supplier" value={value} onChange={(e) => onChange(e.target.value)}
        options={[{ value: "", label: "Select supplier" },
          ...suppliers.data.map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` }))]} />
    );
  }
  return <Input id={id} label="Supplier ID" required value={value} onChange={(e) => onChange(e.target.value)} />;
}

export function SupplierAuditsPanel({ notify }: { notify: Notify }) {
  const perms = useQualityPermissions();
  const approvals = useQuery({ queryKey: ["qa-supplier-approvals"], queryFn: supplierAuditApi.listApprovals, enabled: perms.canView });
  const audits = useQuery({ queryKey: ["qa-supplier-audits"], queryFn: supplierAuditApi.listAudits, enabled: perms.canView });

  const [request, setRequest] = useState({ supplier_id: "", approval_type: "HALAL", critical_findings: "0", notes: "" });
  const [plan, setPlan] = useState({ supplier_id: "", standard: "HALAL", audit_date: todayIso(), lead_auditor: "" });
  const [auditId, setAuditId] = useState("");
  const [scores, setScores] = useState<Record<number, { result: AuditItemResult; finding: string }>>({});
  const [nextAudit, setNextAudit] = useState(addDaysIso(365));
  const [decision, setDecision] = useState<{ id: string; status: SupplierApprovalStatus | ""; audit: string; expiry: string; notes: string }>(
    { id: "", status: "", audit: "", expiry: addDaysIso(365), notes: "" });

  const selectedAudit = useQuery({
    queryKey: ["qa-supplier-audit", auditId], queryFn: () => supplierAuditApi.getAudit(auditId), enabled: !!auditId,
  });

  const createApproval = useAction(supplierAuditApi.createApproval, notify,
    (a) => `Approval request for ${a.supplier_name} (${a.approval_type}) registered`, ["qa-supplier-approvals"]);
  const createAudit = useAction(supplierAuditApi.createAudit, notify, (a) => `Supplier audit ${a.audit_ref} scheduled`,
    ["qa-supplier-audits"]);
  const scoreAudit = useAction(
    (a: { id: string; results: Array<{ item_index: number; result: AuditItemResult; finding?: string }> }) =>
      supplierAuditApi.scoreAudit(a.id, a.results),
    notify, "Audit results saved", ["qa-supplier-audits", "qa-supplier-audit"]);
  const closeAudit = useAction((a: { id: string; next?: string }) => supplierAuditApi.closeAudit(a.id, a.next), notify,
    (r) => `Audit closed (${r.result})${r.suspended_approval_ids.length ? ` — ${r.suspended_approval_ids.length} approval(s) suspended` : ""}`,
    ["qa-supplier-audits", "qa-supplier-audit", "qa-supplier-approvals"]);
  const decide = useAction(
    (d: typeof decision) => supplierAuditApi.decide(d.id, {
      status: d.status as SupplierApprovalStatus, audit_checklist_id: d.audit || undefined,
      expiry_date: d.expiry || undefined, notes: d.notes || undefined,
    }),
    notify, (a) => `${a.supplier_name} ${a.approval_type} is now ${a.status}`, ["qa-supplier-approvals"]);

  const target = (approvals.data ?? []).find((a) => a.id === decision.id);
  // Only the supplier's most recently closed audit is accepted as evidence by the server.
  const closedAudits = useMemo(() => {
    const closed = (audits.data ?? []).filter((a) => a.closed_at && target && a.supplier_id === target.supplier_id);
    closed.sort((a, b) => (b.closed_at ?? "").localeCompare(a.closed_at ?? ""));
    return closed.slice(0, 1);
  }, [audits.data, target]);
  const needsAudit = !!target && (decision.status === "APPROVED" || (decision.status === "CONDITIONAL" && target.status === "PENDING"));

  if (!perms.canView) return <ReadOnlyNotice>Supplier audits require quality.view.</ReadOnlyNotice>;

  const items = selectedAudit.data?.items ?? [];
  const isOpen = !!selectedAudit.data && !selectedAudit.data.closed_at;
  const saveScores = () => scoreAudit.mutate({
    id: auditId,
    results: Object.entries(scores).map(([i, s]) => ({ item_index: Number(i), result: s.result, finding: s.finding || undefined })),
  }, { onSuccess: () => setScores({}) });

  return (
    <div className="space-y-4">
      <Section title="Supplier approvals" description="Requests start pending. Approval needs a closed, passing audit of the same supplier, decided by someone other than the audit closer, and cannot outlast the next audit. A failed supplier audit suspends the supplier's active approvals.">
        {approvals.error ? <LoadError error={approvals.error} /> : (
          <Table<SupplierApproval>
            keyField="id"
            data={approvals.data ?? []}
            emptyMessage="No supplier approvals."
            columns={[
              { header: "Supplier", accessor: "supplier_name" },
              { header: "Scheme", accessor: "approval_type" },
              { header: "Status", accessor: (a) => <Badge label={a.status} variant={statusVariant(a.status)} /> },
              { header: "Valid until", accessor: (a) => a.expiry_date ? `${a.expiry_date}${a.is_current ? "" : " (not current)"}` : "—" },
              { header: "Audit score", accessor: (a) => (a.audit_score ?? "—") },
              { header: "Decision", accessor: (a) => a.decision_notes ?? "—" },
              {
                header: "Actions",
                accessor: (a) => (perms.canEdit || perms.canApprove) && SUPPLIER_APPROVAL_NEXT[a.status].length ? (
                  <Button variant="secondary" aria-label={`Decide ${a.supplier_name} ${a.approval_type}`}
                    onClick={() => setDecision({ id: a.id, status: "", audit: "", expiry: addDaysIso(365), notes: "" })}>
                    Decide
                  </Button>
                ) : null,
              },
            ]}
          />
        )}

        {target && (
          <form aria-label="Approval decision" className="grid gap-3 rounded-lg border border-indigo-100 bg-indigo-50/40 p-3 md:grid-cols-4"
            onSubmit={(e) => { e.preventDefault(); decide.mutate(decision, { onSuccess: () => setDecision((d) => ({ ...d, id: "" })) }); }}>
            <p className="md:col-span-4 text-sm font-medium text-gray-800">
              {target.supplier_name} · {target.approval_type} · currently {target.status}
            </p>
            <Select id="decision-status" label="New status" value={decision.status}
              onChange={(e) => setDecision((d) => ({ ...d, status: e.target.value as SupplierApprovalStatus }))}
              options={[{ value: "", label: "Select" }, ...SUPPLIER_APPROVAL_NEXT[target.status]
                .filter((s) => (s === "PENDING" ? perms.canEdit || perms.canApprove : perms.canApprove))
                .map((s) => ({ value: s, label: s === "PENDING" ? "Re-audit (pending)" : s }))]} />
            {needsAudit && (
              <>
                <Select id="decision-audit" label="Evidence audit" value={decision.audit}
                  onChange={(e) => {
                    const a = closedAudits.find((x) => x.id === e.target.value);
                    setDecision((d) => ({ ...d, audit: e.target.value, expiry: a?.next_audit_date ?? d.expiry }));
                  }}
                  options={[{ value: "", label: closedAudits.length ? "Select closed audit" : "No closed audit for this supplier" },
                    ...closedAudits.map((a) => ({ value: a.id, label: `${a.audit_ref} — ${a.result} ${a.score_pct ?? ""}%` }))]} />
                <Input id="decision-expiry" label="Valid until" type="date" min={addDaysIso(1)} value={decision.expiry}
                  max={closedAudits.find((a) => a.id === decision.audit)?.next_audit_date ?? undefined}
                  onChange={(e) => setDecision((d) => ({ ...d, expiry: e.target.value }))} />
              </>
            )}
            <div className="md:col-span-4">
              <TextArea id="decision-notes" value={decision.notes} onChange={(v) => setDecision((d) => ({ ...d, notes: v }))}
                label={decision.status === "CONDITIONAL" ? "Conditions" : "Notes / reason"} />
            </div>
            <div className="md:col-span-4 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setDecision((d) => ({ ...d, id: "" }))}>Cancel</Button>
              <Button type="submit" loading={decide.isPending}
                disabled={!decision.status || (needsAudit && !decision.audit)
                  || (NEEDS_NOTES.includes(decision.status as SupplierApprovalStatus) && !decision.notes.trim())}>
                Record decision
              </Button>
            </div>
          </form>
        )}

        {perms.canCreate && (
          <form aria-label="New approval request" className="grid gap-3 md:grid-cols-4"
            onSubmit={(e) => { e.preventDefault(); createApproval.mutate({
              supplier_id: request.supplier_id.trim(), approval_type: request.approval_type.trim(),
              critical_findings: Number(request.critical_findings) || 0, notes: request.notes || undefined }); }}>
            <SupplierField id="approval-supplier" value={request.supplier_id} onChange={(v) => setRequest((r) => ({ ...r, supplier_id: v }))} />
            <Input id="approval-type" label="Scheme" required value={request.approval_type}
              onChange={(e) => setRequest((r) => ({ ...r, approval_type: e.target.value }))} />
            <Input id="approval-critical" label="Open critical findings" type="number" min={0} value={request.critical_findings}
              onChange={(e) => setRequest((r) => ({ ...r, critical_findings: e.target.value }))} />
            <div className="flex items-end">
              <Button type="submit" loading={createApproval.isPending} disabled={!request.supplier_id || !request.approval_type}>
                Request approval
              </Button>
            </div>
          </form>
        )}
      </Section>

      <Section title="Supplier audits" description="Schedule an audit against a standard, score every item (a failed item needs a finding), then close it. Closing raises a supplier CAPA for failed items.">
        {audits.error ? <LoadError error={audits.error} /> : (
          <Table<SupplierAudit>
            keyField="id"
            data={audits.data ?? []}
            emptyMessage="No supplier audits."
            columns={[
              { header: "Ref", accessor: "audit_ref" },
              { header: "Supplier", accessor: (a) => shortId(a.supplier_id) },
              { header: "Standard", accessor: "standard" },
              { header: "Date", accessor: "audit_date" },
              { header: "Result", accessor: (a) => <Badge label={a.closed_at ? a.result : `${a.result} (open)`} variant={statusVariant(a.result === "PASS" ? "APPROVED" : a.result === "FAIL" ? "FAILED" : a.result)} /> },
              { header: "Next audit", accessor: (a) => a.next_audit_date ?? "—" },
              {
                header: "",
                accessor: (a) => (
                  <Button variant="secondary" aria-label={`Open audit ${a.audit_ref}`} onClick={() => { setAuditId(a.id); setScores({}); }}>
                    {a.closed_at ? "View" : "Score"}
                  </Button>
                ),
              },
            ]}
          />
        )}

        {selectedAudit.data && (
          <div className="space-y-2 rounded-lg border border-gray-200 p-3" aria-label={`Audit ${selectedAudit.data.audit_ref} items`}>
            <p className="text-sm font-medium text-gray-800">
              {selectedAudit.data.audit_ref} · {selectedAudit.data.standard} · {selectedAudit.data.result}
              {selectedAudit.data.closed_at ? " · closed" : ""}
            </p>
            {items.map((item, index) => {
              const draft = scores[index];
              const result = draft?.result ?? item.result;
              return (
                <div key={index} className="grid items-end gap-2 md:grid-cols-[2fr_1fr_2fr]">
                  <p className="text-sm text-gray-700">[{item.section}] {item.item}</p>
                  <Select id={`audit-item-${index}`} label={`Result ${item.section}`} value={result} disabled={!isOpen || !perms.canEdit}
                    onChange={(e) => setScores((s) => ({ ...s, [index]: { result: e.target.value as AuditItemResult, finding: draft?.finding ?? item.finding ?? "" } }))}
                    options={[{ value: "pending", label: "Pending" }, { value: "pass", label: "Pass" }, { value: "fail", label: "Fail" }, { value: "na", label: "N/A" }]} />
                  <Input id={`audit-finding-${index}`} label={`Finding ${item.section}`} disabled={!isOpen || !perms.canEdit}
                    value={draft?.finding ?? item.finding ?? ""}
                    onChange={(e) => setScores((s) => ({ ...s, [index]: { result, finding: e.target.value } }))} />
                </div>
              );
            })}
            {isOpen && (
              <div className="flex flex-wrap items-end justify-end gap-2">
                {perms.canEdit && (
                  <Button variant="secondary" loading={scoreAudit.isPending} disabled={!Object.keys(scores).length} onClick={saveScores}>
                    Save results
                  </Button>
                )}
                {perms.canApprove && (
                  <>
                    <Input id="audit-next" label="Next audit" type="date" min={addDaysIso(1)} value={nextAudit}
                      onChange={(e) => setNextAudit(e.target.value)} />
                    <Button loading={closeAudit.isPending} disabled={!!Object.keys(scores).length}
                      onClick={() => closeAudit.mutate({ id: auditId, next: nextAudit || undefined })}>Close audit</Button>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {perms.canCreate && (
          <form aria-label="Schedule supplier audit" className="grid gap-3 md:grid-cols-5"
            onSubmit={(e) => { e.preventDefault(); createAudit.mutate({
              supplier_id: plan.supplier_id.trim(), standard: plan.standard, audit_type: "THIRD_PARTY",
              audit_date: plan.audit_date, lead_auditor: plan.lead_auditor || undefined }, { onSuccess: (a) => setAuditId(a.id) }); }}>
            <SupplierField id="audit-supplier" value={plan.supplier_id} onChange={(v) => setPlan((p) => ({ ...p, supplier_id: v }))} />
            <Select id="audit-standard" label="Standard" value={plan.standard} onChange={(e) => setPlan((p) => ({ ...p, standard: e.target.value }))}
              options={STANDARDS.map((s) => ({ value: s, label: s.replace("_", " ") }))} />
            <Input id="audit-date" label="Audit date" type="date" value={plan.audit_date}
              onChange={(e) => setPlan((p) => ({ ...p, audit_date: e.target.value }))} />
            <Input id="audit-lead" label="Lead auditor" value={plan.lead_auditor}
              onChange={(e) => setPlan((p) => ({ ...p, lead_auditor: e.target.value }))} />
            <div className="flex items-end">
              <Button type="submit" loading={createAudit.isPending} disabled={!plan.supplier_id}>Schedule audit</Button>
            </div>
          </form>
        )}
      </Section>
    </div>
  );
}
