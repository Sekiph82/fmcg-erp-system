"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type Concession, type CostCategory, type QualityCostSummary, qaEnterpriseApi } from "@/lib/qa-enterprise";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import {
  LoadError, type Notify, ReadOnlyNotice, Section, TextArea, addDaysIso, shortId, statusVariant, todayIso,
  useAction, useQualityPermissions,
} from "./shared";

const CATEGORIES: CostCategory[] = ["PREVENTION", "APPRAISAL", "INTERNAL_FAILURE", "EXTERNAL_FAILURE"];

function DecideRow({ concession, notify }: { concession: Concession; notify: Notify }) {
  const [conditions, setConditions] = useState("");
  const [until, setUntil] = useState(addDaysIso(7));
  const decide = useAction(
    (approve: boolean) => qaEnterpriseApi.decideConcession(concession.id, approve
      ? { approve, conditions, valid_until: new Date(`${until}T23:59:59`).toISOString() }
      : { approve }),
    notify, (c) => `Concession ${c.concession_no} ${c.status.toLowerCase()}`, ["qa-concessions"]);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <input aria-label={`Conditions for ${concession.concession_no}`} placeholder="Conditions" value={conditions}
        onChange={(e) => setConditions(e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-xs" />
      <input aria-label={`Valid until for ${concession.concession_no}`} type="date" min={todayIso()} value={until}
        onChange={(e) => setUntil(e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-xs" />
      <Button variant="secondary" loading={decide.isPending} aria-label={`Approve ${concession.concession_no}`}
        disabled={!conditions.trim()} onClick={() => decide.mutate(true)}>Approve</Button>
      <Button variant="danger" loading={decide.isPending} aria-label={`Reject ${concession.concession_no}`}
        onClick={() => decide.mutate(false)}>Reject</Button>
    </div>
  );
}

export function ConcessionsCostsPanel({ notify }: { notify: Notify }) {
  const perms = useQualityPermissions();
  const [lotFilter, setLotFilter] = useState("");
  const concessions = useQuery({
    queryKey: ["qa-concessions", lotFilter], queryFn: () => qaEnterpriseApi.listConcessions(lotFilter.trim() || undefined),
    enabled: perms.canView,
  });
  const [req, setReq] = useState({ deviation_id: "", lot_id: "", justification: "", quantity_limit: "", uom: "" });
  const request = useAction(qaEnterpriseApi.requestConcession, notify, (c) => `Concession ${c.concession_no} requested`, ["qa-concessions"]);
  const revoke = useAction((c: Concession) => qaEnterpriseApi.revokeConcession(c.id, "Revoked from QA workspace"), notify,
    (c) => `Concession ${c.concession_no} revoked`, ["qa-concessions"]);

  const [range, setRange] = useState({ date_from: "", date_to: "" });
  const summary = useQuery<QualityCostSummary>({
    queryKey: ["qa-cost-summary", range],
    queryFn: () => qaEnterpriseApi.qualityCostSummary({ date_from: range.date_from || undefined, date_to: range.date_to || undefined }),
    enabled: perms.canView,
  });
  const [cost, setCost] = useState({ category: "INTERNAL_FAILURE" as CostCategory, amount: "", currency: "KES",
    cost_date: todayIso(), description: "", deviation_id: "", lot_id: "" });
  const recordCost = useAction(qaEnterpriseApi.recordQualityCost, notify, "Quality cost recorded", ["qa-cost-summary"]);

  if (!perms.canView) return <ReadOnlyNotice>Concessions and quality cost require quality.view.</ReadOnlyNotice>;

  return (
    <div className="space-y-4">
      <Section title="Concessions" description="Time-limited, conditioned acceptance of a nonconforming lot. Conditional release needs an approved concession on that inspection's deviation."
        actions={<Input aria-label="Filter concessions by lot ID" placeholder="Filter by lot ID" value={lotFilter} onChange={(e) => setLotFilter(e.target.value)} />}>
        {concessions.error ? <LoadError error={concessions.error} /> : (
          <Table<Concession>
            keyField="id"
            data={concessions.data ?? []}
            emptyMessage="No concessions."
            columns={[
              { header: "Ref", accessor: "concession_no" },
              { header: "Lot", accessor: (c) => shortId(c.lot_id) },
              { header: "Deviation", accessor: (c) => shortId(c.deviation_id) },
              { header: "Conditions", accessor: (c) => c.conditions ?? "—" },
              { header: "Valid until", accessor: (c) => (c.valid_until ? new Date(c.valid_until).toLocaleString() : "—") },
              { header: "Status", accessor: (c) => <Badge label={c.status} variant={statusVariant(c.status)} /> },
              {
                header: "Decision",
                accessor: (c) => !perms.canApprove ? null
                  : c.status === "PENDING" ? <DecideRow concession={c} notify={notify} />
                  : c.status === "APPROVED" ? (
                    <Button variant="danger" aria-label={`Revoke ${c.concession_no}`} loading={revoke.isPending}
                      onClick={() => revoke.mutate(c)}>Revoke</Button>
                  ) : null,
              },
            ]}
          />
        )}
        {perms.canCreate && (
          <form className="grid gap-3 md:grid-cols-3" onSubmit={(e) => {
            e.preventDefault();
            request.mutate({ deviation_id: req.deviation_id.trim(), lot_id: req.lot_id.trim(), justification: req.justification,
              quantity_limit: req.quantity_limit || undefined, uom: req.uom || undefined });
          }}>
            <Input id="con-deviation" label="Deviation ID" required value={req.deviation_id} onChange={(e) => setReq((r) => ({ ...r, deviation_id: e.target.value }))} />
            <Input id="con-lot" label="Lot ID" required value={req.lot_id} onChange={(e) => setReq((r) => ({ ...r, lot_id: e.target.value }))} />
            <div className="grid grid-cols-2 gap-2">
              <Input id="con-qty" label="Quantity limit" type="number" min={0} step="0.001" value={req.quantity_limit}
                onChange={(e) => setReq((r) => ({ ...r, quantity_limit: e.target.value }))} />
              <Input id="con-uom" label="UoM" value={req.uom} onChange={(e) => setReq((r) => ({ ...r, uom: e.target.value }))} />
            </div>
            <div className="md:col-span-3">
              <TextArea id="con-justification" label="Justification" value={req.justification} onChange={(v) => setReq((r) => ({ ...r, justification: v }))} />
            </div>
            <div className="md:col-span-3 flex justify-end">
              <Button type="submit" loading={request.isPending} disabled={!req.deviation_id || !req.lot_id || !req.justification.trim()}>Request concession</Button>
            </div>
          </form>
        )}
      </Section>

      <Section title="Cost of quality" description="Prevention and appraisal (cost of good quality) versus internal and external failure (cost of poor quality).">
        <div className="grid gap-3 md:grid-cols-4">
          <Input id="cost-from" label="From" type="date" value={range.date_from} onChange={(e) => setRange((r) => ({ ...r, date_from: e.target.value }))} />
          <Input id="cost-to" label="To" type="date" value={range.date_to} onChange={(e) => setRange((r) => ({ ...r, date_to: e.target.value }))} />
        </div>
        {summary.error ? <LoadError error={summary.error} /> : summary.data && (
          <div data-testid="cost-summary" className="space-y-2">
            <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
              {CATEGORIES.map((c) => (
                <div key={c} className="rounded-lg bg-gray-50 p-3">
                  <dt className="text-gray-500">{c.replace("_", " ")}</dt>
                  <dd className="text-lg font-semibold">{summary.data.by_category[c]}</dd>
                </div>
              ))}
            </dl>
            <p className="text-sm text-gray-700">
              Cost of poor quality <strong>{summary.data.cost_of_poor_quality}</strong> of <strong>{summary.data.total}</strong>
              {summary.data.copq_share_pct ? ` (${summary.data.copq_share_pct}%)` : ""}{summary.data.currencies.length ? ` ${summary.data.currencies.join("/")}` : ""}
            </p>
            {summary.data.mixed_currency && (
              <p role="alert" className="text-sm text-amber-700">Entries use more than one currency; totals are not converted.</p>
            )}
          </div>
        )}
        {perms.canCreate && (
          <form className="grid gap-3 md:grid-cols-4" onSubmit={(e) => {
            e.preventDefault();
            recordCost.mutate({ category: cost.category, amount: cost.amount, currency: cost.currency.toUpperCase(), cost_date: cost.cost_date,
              description: cost.description, deviation_id: cost.deviation_id.trim() || undefined, lot_id: cost.lot_id.trim() || undefined });
          }}>
            <Select id="cost-category" label="Category" value={cost.category}
              onChange={(e) => setCost((c) => ({ ...c, category: e.target.value as CostCategory }))}
              options={CATEGORIES.map((c) => ({ value: c, label: c.replace("_", " ") }))} />
            <Input id="cost-amount" label="Amount" type="number" min={0.01} step="0.01" required value={cost.amount}
              onChange={(e) => setCost((c) => ({ ...c, amount: e.target.value }))} />
            <Input id="cost-currency" label="Currency" maxLength={3} value={cost.currency}
              onChange={(e) => setCost((c) => ({ ...c, currency: e.target.value }))} />
            <Input id="cost-date" label="Cost date" type="date" value={cost.cost_date}
              onChange={(e) => setCost((c) => ({ ...c, cost_date: e.target.value }))} />
            <Input id="cost-deviation" label="Deviation ID (optional)" value={cost.deviation_id}
              onChange={(e) => setCost((c) => ({ ...c, deviation_id: e.target.value }))} />
            <Input id="cost-lot" label="Lot ID (optional)" value={cost.lot_id}
              onChange={(e) => setCost((c) => ({ ...c, lot_id: e.target.value }))} />
            <div className="md:col-span-2">
              <Input id="cost-description" label="Cost description" required value={cost.description}
                onChange={(e) => setCost((c) => ({ ...c, description: e.target.value }))} />
            </div>
            <div className="md:col-span-4 flex justify-end">
              <Button type="submit" loading={recordCost.isPending} disabled={!cost.amount || !cost.description}>Record cost</Button>
            </div>
          </form>
        )}
      </Section>
    </div>
  );
}
