"use client";

import { useState } from "react";
import { type CapaLink, qaEnterpriseApi } from "@/lib/qa-enterprise";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import { type Notify, ReadOnlyNotice, Section, statusVariant, useAction, useQualityPermissions } from "./shared";
import { tx } from "@/lib/i18n/core";

type Trigger = "COMPLAINT" | "RECALL" | "AUDIT" | "DEVIATION";

export function CapaLinksPanel({ notify }: { notify: Notify }) {
  const perms = useQualityPermissions();
  const [trigger, setTrigger] = useState<Trigger>("COMPLAINT");
  const [triggerId, setTriggerId] = useState("");
  const [links, setLinks] = useState<CapaLink[] | null>(null);

  const lookup = useAction(() => qaEnterpriseApi.capaLinks(trigger, triggerId.trim()), notify,
    (rows) => tx("{length} linked CAPA(s)", { length: rows.length }), []);
  const raise = useAction(
    () => (trigger === "COMPLAINT" ? qaEnterpriseApi.capaFromComplaint(triggerId.trim()) : qaEnterpriseApi.capaFromRecall(triggerId.trim())),
    notify, (r) => (r.created ? tx("CAPA {ca_no} opened", { ca_no: r.ca_no }) : tx("Open CAPA {ca_no} already exists", { ca_no: r.ca_no })), [],
  );

  if (!perms.canView) return <ReadOnlyNotice>{tx("CAPA links require quality.view.")}</ReadOnlyNotice>;

  const refresh = () => lookup.mutate(undefined, { onSuccess: setLinks });

  return (
    <Section title={tx("Complaint, recall and audit CAPAs")} description={tx("Open one CAPA per complaint or recall (repeat requests return the open one). A live recall cannot close until its CAPAs are verified.")}>
      <form className="grid gap-3 md:grid-cols-4" onSubmit={(e) => { e.preventDefault(); refresh(); }}>
        <Select id="link-trigger" label={tx("Source")} value={trigger} onChange={(e) => { setTrigger(e.target.value as Trigger); setLinks(null); }}
          options={["COMPLAINT", "RECALL", "AUDIT", "DEVIATION"].map((v) => ({ value: v, label: v[0] + v.slice(1).toLowerCase() }))} />
        <Input id="link-trigger-id" label={tx("Source record ID")} required value={triggerId} onChange={(e) => setTriggerId(e.target.value)} />
        <div className="flex items-end gap-2 md:col-span-2">
          <Button type="submit" variant="secondary" loading={lookup.isPending} disabled={!triggerId}>{tx("Show linked CAPAs")}</Button>
          {perms.canCreate && (trigger === "COMPLAINT" || trigger === "RECALL") && (
            <Button type="button" loading={raise.isPending} disabled={!triggerId}
              onClick={() => raise.mutate(undefined, { onSuccess: refresh })}>{tx("Open CAPA")}</Button>
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
            { header: tx("Title"), accessor: "title" },
            { header: tx("Severity"), accessor: "severity" },
            { header: tx("Status"), accessor: (c) => <Badge label={c.status} variant={statusVariant(c.status)} /> },
            { header: tx("Due"), accessor: (c) => c.due_date ?? "—" },
          ]}
        />
      )}
    </Section>
  );
}
