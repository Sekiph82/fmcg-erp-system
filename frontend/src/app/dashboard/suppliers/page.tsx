"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { PermissionGuard } from "@/components/PermissionGuard";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { suppliersApi, SupplierCreate, SupplierQualificationStatus } from "@/lib/suppliers";
import { ImportModal } from "@/components/import/ImportModal";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { tx } from "@/lib/i18n/core";

const empty: SupplierCreate = { code: "", name: "", payment_terms_days: 30, is_active: true };

function SuppliersListTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<SupplierCreate>(empty);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [governanceId, setGovernanceId] = useState<string | null>(null);
  const [qualificationStatus, setQualificationStatus] = useState<SupplierQualificationStatus>("PENDING");
  const [approvedFrom, setApprovedFrom] = useState("");
  const [approvedUntil, setApprovedUntil] = useState("");
  const [qualificationReason, setQualificationReason] = useState("");
  const [preferredValue, setPreferredValue] = useState(false);
  const [preferenceReason, setPreferenceReason] = useState("");

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

  const qualification = useMutation({
    mutationFn: () => suppliersApi.decideQualification(governanceId!, {
      qualification_status: qualificationStatus,
      approved_from: qualificationStatus === "APPROVED" ? approvedFrom || null : null,
      approved_until: qualificationStatus === "APPROVED" ? approvedUntil || null : null,
      reason: qualificationReason,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      qc.invalidateQueries({ queryKey: ["supplier-dashboard"] });
      setQualificationReason("");
    },
  });

  const preference = useMutation({
    mutationFn: () => suppliersApi.decidePreference(governanceId!, { is_preferred: preferredValue, reason: preferenceReason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      qc.invalidateQueries({ queryKey: ["supplier-dashboard"] });
      setPreferenceReason("");
    },
  });

  const set = (key: keyof SupplierCreate, value: unknown) => setForm((f) => ({ ...f, [key]: value }));

  const deletingSupplier = suppliers.find((s) => s.id === deletingId);
  const governanceSupplier = suppliers.find((s) => s.id === governanceId);

  const openGovernance = (supplierId: string) => {
    const supplier = suppliers.find((row) => row.id === supplierId);
    if (!supplier) return;
    setGovernanceId(supplierId);
    setQualificationStatus(supplier.qualification_status ?? "PENDING");
    setApprovedFrom(supplier.approved_from ?? "");
    setApprovedUntil(supplier.approved_until ?? "");
    setPreferredValue(supplier.is_preferred);
    setQualificationReason("");
    setPreferenceReason("");
    qualification.reset();
    preference.reset();
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Suppliers")}</h1>
          <p className="text-sm text-gray-500 mt-1">{suppliers.length} {tx("total")}</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal module="suppliers" onSuccess={() => qc.invalidateQueries({ queryKey: ["suppliers"] })} />
          <PermissionGuard permission="suppliers.create">
            <Button onClick={() => setOpen(true)}>{tx("+ Add Supplier")}</Button>
          </PermissionGuard>
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
            { header: tx("Code"), accessor: "code", className: "font-mono text-xs" },
            { header: tx("Name"), accessor: "name" },
            { header: tx("Contact"), accessor: (r) => r.contact_person ?? "—" },
            { header: tx("Email"), accessor: (r) => r.email ?? "—" },
            { header: tx("Country"), accessor: (r) => r.country ?? "—" },
            { header: tx("Payment Terms"), accessor: (r) => `${r.payment_terms_days} days` },
            {
              header: tx("Qualification"),
              accessor: (r) => {
                const value = r.qualification_status ?? "LEGACY / UNRECORDED";
                const variant = value === "APPROVED" ? "green" : ["SUSPENDED", "REJECTED"].includes(value) ? "red" : "yellow";
                return <Badge label={value} variant={variant} />;
              },
            },
            { header: tx("Preferred"), accessor: (r) => r.is_preferred ? <Badge label={tx("Preferred")} variant="green" /> : "—" },
            { header: tx("Status"), accessor: (r) => <Badge label={r.is_active ? tx("Active") : tx("Inactive")} variant={r.is_active ? "green" : "red"} /> },
            {
              header: "",
              accessor: (r) => (
                <div className="flex items-center gap-3">
                  <PermissionGuard permission="procurement.approve">
                    <button onClick={() => openGovernance(r.id)} className="text-xs text-indigo-600 hover:underline">{tx("Governance")}</button>
                  </PermissionGuard>
                  <PermissionGuard permission="suppliers.delete">
                    <button onClick={() => setDeletingId(r.id)} className="text-xs text-red-500 hover:text-red-700 hover:underline">{tx("Delete")}</button>
                  </PermissionGuard>
                </div>
              ),
            },
          ]}
        />
      )}

      {/* Add Supplier Modal */}
      <Modal open={open} onClose={() => setOpen(false)} title={tx("Add Supplier")}>
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Code *")} value={form.code} onChange={(e) => set("code", e.target.value)} required />
            <Input label={tx("Name *")} value={form.name} onChange={(e) => set("name", e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Contact Person")} onChange={(e) => set("contact_person", e.target.value)} />
            <Input label={tx("Email")} type="email" onChange={(e) => set("email", e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label={tx("Phone")} onChange={(e) => set("phone", e.target.value)} />
            <Input label={tx("Country")} onChange={(e) => set("country", e.target.value)} />
          </div>
          <Input label={tx("Payment Terms (days)")} type="number" value={form.payment_terms_days}
            onChange={(e) => set("payment_terms_days", parseInt(e.target.value))} />
          {create.error && <p className="text-sm text-red-600">{tx("Failed to create supplier.")}</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>{tx("Cancel")}</Button>
            <Button type="submit" loading={create.isPending}>{tx("Create")}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!governanceId} onClose={() => setGovernanceId(null)} title={`Supplier governance: ${governanceSupplier?.name ?? ""}`}>
        <div className="space-y-5">
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-gray-800">{tx("Qualification decision")}</h2>
            <label className="block text-sm text-gray-700">
              {tx("Status")}
              <select className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2" value={qualificationStatus}
                onChange={(e) => setQualificationStatus(e.target.value as SupplierQualificationStatus)}>
                {["PENDING", "APPROVED", "CONDITIONAL", "SUSPENDED", "REJECTED"].map((value) => <option key={value}>{value}</option>)}
              </select>
            </label>
            {qualificationStatus === "APPROVED" && <div className="grid grid-cols-2 gap-3">
              <Input label={tx("Approval starts")} type="date" value={approvedFrom} onChange={(e) => setApprovedFrom(e.target.value)} />
              <Input label={tx("Approval ends (optional)")} type="date" value={approvedUntil} onChange={(e) => setApprovedUntil(e.target.value)} />
            </div>}
            <Input label={tx("Decision reason *")} value={qualificationReason} onChange={(e) => setQualificationReason(e.target.value)} required />
            {qualification.error && <p className="text-sm text-red-600">{tx("Qualification decision was not saved. Check your permission and decision details.")}</p>}
            <Button loading={qualification.isPending} disabled={qualificationReason.trim().length < 3}
              onClick={() => qualification.mutate()}>{tx("Save qualification")}</Button>
          </section>
          <section className="space-y-3 border-t border-gray-200 pt-4">
            <h2 className="text-sm font-semibold text-gray-800">{tx("Preferred supplier")}</h2>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={preferredValue} onChange={(e) => setPreferredValue(e.target.checked)} />
              {tx("Preferred (requires active, currently approved qualification)")}
            </label>
            <Input label={tx("Preference reason *")} value={preferenceReason} onChange={(e) => setPreferenceReason(e.target.value)} required />
            {preference.error && <p className="text-sm text-red-600">{tx("Preference decision was not saved. Check your permission and supplier eligibility.")}</p>}
            <Button variant="secondary" loading={preference.isPending} disabled={preferenceReason.trim().length < 3}
              onClick={() => preference.mutate()}>{tx("Save preference")}</Button>
          </section>
        </div>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title={tx("Delete Supplier")}>
        <p className="text-sm text-gray-600 mb-4">
          {tx("Are you sure you want to delete")}{" "}
          <span className="font-semibold text-gray-900">{deletingSupplier?.name}</span>{tx("? This action cannot be undone.")}
        </p>
        {deleteMutation.error && <p className="text-sm text-red-600 mb-3">{tx("Failed to delete supplier.")}</p>}
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setDeletingId(null)}>{tx("Cancel")}</Button>
          <Button
            variant="danger"
            loading={deleteMutation.isPending}
            onClick={() => deletingId && deleteMutation.mutate(deletingId)}
          >
            {tx("Delete")}
          </Button>
        </div>
      </Modal>
    </div>
  );
}

export default function SuppliersPage() {
  const tabs = [
    { key: "suppliers", label: tx("Suppliers"), permission: "suppliers.view", content: <SuppliersListTab /> },
  ];
  return (
    <ModuleWorkspace
      title={tx("Suppliers")}
      description="Supplier master, contacts, performance, approved vendors"
      permission="suppliers.view"
      tabs={tabs}
      defaultTab="suppliers"
    />
  );
}
