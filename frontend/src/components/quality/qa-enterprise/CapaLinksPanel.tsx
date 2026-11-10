"use client";

import { useState } from "react";
import { type CapaLink, qaEnterpriseApi } from "@/lib/qa-enterprise";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import { type Notify, ReadOnlyNotice, Section, statusVariant, useAction, useQualityPermissions } from "./shared";

type Trigger = "COMPLAINT" | "RECALL" | "AUDIT" | "DEVIATION";

export function CapaLinksPanel({ notify }: { notify: Notify }) {
  const perms = useQualityPermissions();
  const [trigger, setTrigger] = useState<Trigger>("COMPLAINT");
  const [triggerId, setTriggerId] = useState("");
  const [links, setLinks] = useState<CapaLink[] | null>(null);

  const lookup = useAction(() => qaEnterpriseApi.capaLinks(trigger, triggerId.trim()), notify,
    (rows) => `${rows.length} linked CAPA(s)`, []);
  const raise = useAction(
    () => (trigger === "COMPLAINT" ? qaEnterpriseApi.capaFromComplaint(triggerId.trim()) : qaEnterpriseApi.capaFromRecall(triggerId.trim())),
    notify, (r) => (r.created ? `CAPA ${r.ca_no} opened` : `Open CAPA ${r.ca_no} already exists`), [],
  );

  if (!perms.canView) return <ReadOnlyNotice>CAPA links require quality.view.</ReadOnlyNotice>;

  const refresh = () => lookup.mutate(undefined, { onSuccess: setLinks });

  return (
    <Section title="Complaint, recall and audit CAPAs" description="Open one CAPA per complaint or recall (repeat requests return the open one). A live recall cannot close until its CAPAs are verified.">
      <form className="grid gap-3 md:grid-cols-4" onSubmit={(e) => { e.preventDefault(); refresh(); }}>
        <Select id="link-trigger" label="Source" value={trigger} onChange={(e) => { setTrigger(e.target.value as Trigger); setLinks(null); }}
          options={["COMPLAINT", "RECALL", "AUDIT", "DEVIATION"].map((v) => ({ value: v, label: v[0] + v.slice(1).toLowerCase() }))} />
        <Input id="link-trigger-id" label="Source record ID" required value={triggerId} onChange={(e) => setTriggerId(e.target.value)} />
        <div className="flex items-end gap-2 md:col-span-2">
          <Button type="submit" variant="secondary" loading={lookup.isPending} disabled={!triggerId}>Show linked CAPAs</Button>
          {perms.canCreate && (trigger === "COMPLAINT" || trigger === "RECALL") && (
            <Button type="button" loading={raise.isPending} disabled={!triggerId}
              onClick={() => raise.mutate(undefined, { onSuccess: refresh })}>Open CAPA</Button>
          )}
        </div>
      </form>
      {links && (
        <Table<CapaLink>
          keyField="id"
          data={links}
          emptyMessage="No CAPA is linked to this record."
          columns={[
            { header: "CAPA", accessor: "ca_no" },
            { header: "Title", accessor: "title" },
            { header: "Severity", accessor: "severity" },
            { header: "Status", accessor: (c) => <Badge label={c.status} variant={statusVariant(c.status)} /> },
            { header: "Due", accessor: (c) => c.due_date ?? "—" },
          ]}
        />
      )}
    </Section>
  );
}
