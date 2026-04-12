"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, SupplierCreate } from "@/lib/suppliers";
import { ImportModal } from "@/components/import/ImportModal";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

const empty: SupplierCreate = { code: "", name: "", payment_terms_days: 30, is_active: true };

export default function SuppliersPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<SupplierCreate>(empty);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: suppliers = [], isLoading } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => suppliersApi.list(),
  });

  const create = useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); setOpen(false); setForm(empty); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => suppliersApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); setDeletingId(null); },
  });

  const set = (key: keyof SupplierCreate, value: unknown) => setForm((f) => ({ ...f, [key]: value }));

  const deletingSupplier = suppliers.find((s) => s.id === deletingId);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Suppliers</h1>
          <p className="text-sm text-gray-500 mt-1">{suppliers.length} total</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal module="suppliers" onSuccess={() => qc.invalidateQueries({ queryKey: ["suppliers"] })} />
          <Button onClick={() => setOpen(true)}>+ Add Supplier</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <Table
          keyField="id"
          data={suppliers}
          columns={[
            { header: "Code", accessor: "code", className: "font-mono text-xs" },
            { header: "Name", accessor: "name" },
            { header: "Contact", accessor: (r) => r.contact_person ?? "—" },
            { header: "Email", accessor: (r) => r.email ?? "—" },
            { header: "Country", accessor: (r) => r.country ?? "—" },
            { header: "Payment Terms", accessor: (r) => `${r.payment_terms_days} days` },
            { header: "Status", accessor: (r) => <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "red"} /> },
            {
              header: "",
              accessor: (r) => (
                <button
                  onClick={() => setDeletingId(r.id)}
                  className="text-xs text-red-500 hover:text-red-700 hover:underline"
                >
                  Delete
                </button>
              ),
            },
          ]}
        />
      )}

      {/* Add Supplier Modal */}
      <Modal open={open} onClose={() => setOpen(false)} title="Add Supplier">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Code *" value={form.code} onChange={(e) => set("code", e.target.value)} required />
            <Input label="Name *" value={form.name} onChange={(e) => set("name", e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Contact Person" onChange={(e) => set("contact_person", e.target.value)} />
            <Input label="Email" type="email" onChange={(e) => set("email", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Phone" onChange={(e) => set("phone", e.target.value)} />
            <Input label="Country" onChange={(e) => set("country", e.target.value)} />
          </div>
          <Input label="Payment Terms (days)" type="number" value={form.payment_terms_days}
            onChange={(e) => set("payment_terms_days", parseInt(e.target.value))} />
          {create.error && <p className="text-sm text-red-600">Failed to create supplier.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create</Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title="Delete Supplier">
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete{" "}
          <span className="font-semibold text-gray-900">{deletingSupplier?.name}</span>?
          This action cannot be undone.
        </p>
        {deleteMutation.error && <p className="text-sm text-red-600 mb-3">Failed to delete supplier.</p>}
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
    </div>
  );
}
