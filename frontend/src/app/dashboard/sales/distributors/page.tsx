"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { distributorsApi, DistributorCreate } from "@/lib/distribution";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

const empty: DistributorCreate = { code: "", name: "", currency: "KES", payment_terms_days: 30 };

const statusVariant: Record<string, "green" | "red" | "yellow"> = {
  ACTIVE: "green",
  INACTIVE: "red",
  SUSPENDED: "yellow",
};

export default function DistributorsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<DistributorCreate>(empty);

  const { data: distributors = [], isLoading } = useQuery({
    queryKey: ["distributors"],
    queryFn: () => distributorsApi.list(),
  });

  const create = useMutation({
    mutationFn: distributorsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["distributors"] }); setOpen(false); setForm(empty); },
  });

  const set = (k: keyof DistributorCreate, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Distributors</h1>
          <p className="text-sm text-gray-500 mt-1">{distributors.length} total</p>
        </div>
        <Button onClick={() => setOpen(true)}>+ Add Distributor</Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <Table
          keyField="id"
          data={distributors}
          columns={[
            { header: "Code", accessor: "code", className: "font-mono text-xs" },
            { header: "Name", accessor: "name" },
            { header: "Region", accessor: (r) => r.region ?? "—" },
            { header: "Contact", accessor: (r) => r.contact_person ?? "—" },
            { header: "Phone", accessor: (r) => r.phone ?? "—" },
            { header: "Terms", accessor: (r) => `${r.payment_terms_days} days` },
            { header: "Status", accessor: (r) => (
              <Badge label={r.status} variant={statusVariant[r.status] ?? "gray"} />
            )},
          ]}
        />
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Add Distributor">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Code *" value={form.code} onChange={(e) => set("code", e.target.value)} required />
            <Input label="Name *" value={form.name} onChange={(e) => set("name", e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Contact Person" onChange={(e) => set("contact_person", e.target.value)} />
            <Input label="Phone" onChange={(e) => set("phone", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Email" type="email" onChange={(e) => set("email", e.target.value)} />
            <Input label="Region" onChange={(e) => set("region", e.target.value)} placeholder="e.g. Nairobi" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Payment Terms (days)" type="number" value={form.payment_terms_days}
              onChange={(e) => set("payment_terms_days", parseInt(e.target.value))} />
            <Input label="Credit Limit (KES)" type="number" onChange={(e) => set("credit_limit", parseFloat(e.target.value))} />
          </div>
          <Input label="Territory (description)" onChange={(e) => set("territory", e.target.value)}
            placeholder="e.g. Nairobi CBD, Westlands, Parklands" />
          {create.error && <p className="text-sm text-red-600">Failed to create distributor.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
