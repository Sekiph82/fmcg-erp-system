"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type RetainSample, type TestMethod, qaEnterpriseApi } from "@/lib/qa-enterprise";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Table } from "@/components/ui/Table";
import {
  LoadError, type Notify, ReadOnlyNotice, Section, addDaysIso, shortId, statusVariant, todayIso,
  useAction, useQualityPermissions,
} from "./shared";

function SampleActions({ sample, notify, canApprove }: { sample: RetainSample; notify: Notify; canApprove: boolean }) {
  const [qty, setQty] = useState("");
  const [reason, setReason] = useState("");
  const withdraw = useAction(() => qaEnterpriseApi.withdrawRetainSample(sample.id, qty, reason), notify,
    (s) => `${s.sample_no}: ${s.quantity_remaining} ${s.uom} remaining`, ["qa-retain"]);
  const dispose = useAction(() => qaEnterpriseApi.disposeRetainSample(sample.id, reason), notify,
    (s) => `${s.sample_no} disposed`, ["qa-retain"]);
  if (sample.status === "DISPOSED") return null;
  const early = sample.retain_until >= todayIso();
  return (
    <div className="flex flex-wrap items-center gap-2">
      <input aria-label={`Reason for ${sample.sample_no}`} placeholder="Reason" value={reason}
        onChange={(e) => setReason(e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-xs" />
      {sample.status === "STORED" && (
        <>
          <input aria-label={`Withdraw quantity for ${sample.sample_no}`} type="number" min={0} step="0.001" placeholder="Qty"
            value={qty} onChange={(e) => setQty(e.target.value)} className="w-20 rounded border border-gray-300 px-2 py-1 text-xs" />
          <Button variant="secondary" aria-label={`Withdraw from ${sample.sample_no}`} loading={withdraw.isPending}
            disabled={!qty || !reason.trim()} onClick={() => withdraw.mutate(undefined)}>Withdraw</Button>
        </>
      )}
      <Button variant="danger" aria-label={`Dispose ${sample.sample_no}`} loading={dispose.isPending}
        disabled={!reason.trim() || (early && !canApprove)}
        title={early && !canApprove ? "Disposal before the retention date needs quality approval" : undefined}
        onClick={() => dispose.mutate(undefined)}>Dispose</Button>
    </div>
  );
}

export function LabPanel({ notify }: { notify: Notify }) {
  const perms = useQualityPermissions();
  const [dueOnly, setDueOnly] = useState(false);
  const samples = useQuery({ queryKey: ["qa-retain", dueOnly], queryFn: () => qaEnterpriseApi.listRetainSamples(dueOnly), enabled: perms.canView });
  const methods = useQuery({ queryKey: ["qa-methods"], queryFn: qaEnterpriseApi.listTestMethods, enabled: perms.canView });
  const [sample, setSample] = useState({ lot_id: "", quantity: "", uom: "unit", storage_location: "", storage_condition: "",
    collected_on: todayIso(), retain_until: addDaysIso(365) });
  const [method, setMethod] = useState({ method_code: "", name: "", standard_reference: "", instrument_type: "",
    requires_instrument: false, required_skill_id: "" });
  const [link, setLink] = useState({ parameter_id: "", test_method_id: "" });

  const register = useAction(qaEnterpriseApi.registerRetainSample, notify, (s) => `Retain sample ${s.sample_no} registered`, ["qa-retain"]);
  const createMethod = useAction(qaEnterpriseApi.createTestMethod, notify, (m) => `Test method ${m.method_code} v${m.version} created`, ["qa-methods"]);
  const linkMethod = useAction(() => qaEnterpriseApi.linkParameterMethod(link.parameter_id.trim(), link.test_method_id || null),
    notify, "Template parameter linked to test method", []);

  if (!perms.canView) return <ReadOnlyNotice>Laboratory records require quality.view.</ReadOnlyNotice>;

  return (
    <div className="space-y-4">
      <Section title="Retain samples" description="Reference samples kept until their retention date. Early disposal needs quality approval and a reason."
        actions={(
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={dueOnly} onChange={(e) => setDueOnly(e.target.checked)} /> Past retention only
          </label>
        )}>
        {samples.error ? <LoadError error={samples.error} /> : (
          <Table<RetainSample>
            keyField="id"
            data={samples.data ?? []}
            emptyMessage={dueOnly ? "No samples are past their retention date." : "No retain samples."}
            columns={[
              { header: "Sample", accessor: "sample_no" },
              { header: "Lot", accessor: (s) => shortId(s.lot_id) },
              { header: "Remaining", accessor: (s) => `${s.quantity_remaining} / ${s.quantity} ${s.uom}` },
              { header: "Location", accessor: "storage_location" },
              { header: "Retain until", accessor: "retain_until" },
              { header: "Status", accessor: (s) => <Badge label={s.status} variant={statusVariant(s.status)} /> },
              { header: "Actions", accessor: (s) => perms.canEdit ? <SampleActions sample={s} notify={notify} canApprove={perms.canApprove} /> : null },
            ]}
          />
        )}
        {perms.canCreate && (
          <form className="grid gap-3 md:grid-cols-4" onSubmit={(e) => { e.preventDefault(); register.mutate({ ...sample, lot_id: sample.lot_id.trim(),
            storage_condition: sample.storage_condition || undefined }); }}>
            <Input id="rs-lot" label="Lot ID" required value={sample.lot_id} onChange={(e) => setSample((s) => ({ ...s, lot_id: e.target.value }))} />
            <Input id="rs-qty" label="Quantity" type="number" min={0.001} step="0.001" required value={sample.quantity}
              onChange={(e) => setSample((s) => ({ ...s, quantity: e.target.value }))} />
            <Input id="rs-uom" label="Unit" required value={sample.uom} onChange={(e) => setSample((s) => ({ ...s, uom: e.target.value }))} />
            <Input id="rs-location" label="Storage location" required value={sample.storage_location}
              onChange={(e) => setSample((s) => ({ ...s, storage_location: e.target.value }))} />
            <Input id="rs-condition" label="Storage condition" value={sample.storage_condition}
              onChange={(e) => setSample((s) => ({ ...s, storage_condition: e.target.value }))} />
            <Input id="rs-collected" label="Collected on" type="date" value={sample.collected_on}
              onChange={(e) => setSample((s) => ({ ...s, collected_on: e.target.value }))} />
            <Input id="rs-until" label="Retain until" type="date" min={sample.collected_on} value={sample.retain_until}
              onChange={(e) => setSample((s) => ({ ...s, retain_until: e.target.value }))} />
            <div className="flex items-end justify-end">
              <Button type="submit" loading={register.isPending} disabled={!sample.lot_id || !sample.quantity || !sample.storage_location}>Register sample</Button>
            </div>
          </form>
        )}
      </Section>

      <Section title="Test methods" description="Versioned methods. A required instrument blocks results from uncalibrated equipment; a required skill blocks unqualified testers.">
        {methods.error ? <LoadError error={methods.error} /> : (
          <Table<TestMethod>
            keyField="id"
            data={methods.data ?? []}
            emptyMessage="No test methods."
            columns={[
              { header: "Method", accessor: (m) => `${m.method_code} v${m.version}` },
              { header: "Name", accessor: "name" },
              { header: "Standard", accessor: (m) => m.standard_reference ?? "—" },
              { header: "Instrument", accessor: (m) => (m.requires_instrument ? `Required: ${m.instrument_type}` : m.instrument_type ?? "—") },
              { header: "Skill", accessor: (m) => shortId(m.required_skill_id) },
            ]}
          />
        )}
        {perms.canCreate && (
          <form className="grid gap-3 md:grid-cols-3" onSubmit={(e) => { e.preventDefault(); createMethod.mutate({
            method_code: method.method_code.trim(), name: method.name.trim(), standard_reference: method.standard_reference || null,
            instrument_type: method.instrument_type || null, requires_instrument: method.requires_instrument,
            required_skill_id: method.required_skill_id.trim() || null }); }}>
            <Input id="tm-code" label="Method code" required value={method.method_code} onChange={(e) => setMethod((m) => ({ ...m, method_code: e.target.value }))} />
            <Input id="tm-name" label="Method name" required value={method.name} onChange={(e) => setMethod((m) => ({ ...m, name: e.target.value }))} />
            <Input id="tm-standard" label="Standard reference" value={method.standard_reference}
              onChange={(e) => setMethod((m) => ({ ...m, standard_reference: e.target.value }))} />
            <Input id="tm-instrument" label="Instrument type" value={method.instrument_type}
              onChange={(e) => setMethod((m) => ({ ...m, instrument_type: e.target.value }))} />
            <Input id="tm-skill" label="Required skill ID (optional)" value={method.required_skill_id}
              onChange={(e) => setMethod((m) => ({ ...m, required_skill_id: e.target.value }))} />
            <label className="flex items-end gap-2 pb-2 text-sm text-gray-700">
              <input type="checkbox" checked={method.requires_instrument}
                onChange={(e) => setMethod((m) => ({ ...m, requires_instrument: e.target.checked }))} /> Instrument required
            </label>
            <div className="md:col-span-3 flex justify-end">
              <Button type="submit" loading={createMethod.isPending}
                disabled={!method.method_code || !method.name || (method.requires_instrument && !method.instrument_type)}>Create test method</Button>
            </div>
          </form>
        )}
        {perms.canEdit && (
          <form className="grid gap-3 border-t border-gray-100 pt-3 md:grid-cols-3" onSubmit={(e) => { e.preventDefault(); linkMethod.mutate(undefined); }}>
            <Input id="link-parameter" label="Template parameter ID" required value={link.parameter_id}
              onChange={(e) => setLink((l) => ({ ...l, parameter_id: e.target.value }))} />
            <div className="flex flex-col gap-1">
              <label htmlFor="link-method" className="text-sm font-medium text-gray-700">Test method</label>
              <select id="link-method" value={link.test_method_id} onChange={(e) => setLink((l) => ({ ...l, test_method_id: e.target.value }))}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm">
                <option value="">None (unlink)</option>
                {(methods.data ?? []).filter((m) => m.is_active).map((m) => <option key={m.id} value={m.id}>{m.method_code} v{m.version}</option>)}
              </select>
            </div>
            <div className="flex items-end">
              <Button type="submit" variant="secondary" loading={linkMethod.isPending} disabled={!link.parameter_id}>Link parameter</Button>
            </div>
          </form>
        )}
      </Section>
    </div>
  );
}
