"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { salesApi, CustomerChannel } from "@/lib/sales";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const CHANNEL_OPTS = ["RETAIL", "WHOLESALE", "DISTRIBUTOR", "DIRECT", "EXPORT", "ONLINE"].map((c) => ({ value: c, label: c }));
const CURRENCY_OPTS = ["USD", "EUR", "GBP", "JPY", "CNY", "SGD"].map((c) => ({ value: c, label: c }));
const TERMS_OPTS = [7, 14, 30, 45, 60, 90].map((d) => ({ value: String(d), label: `Net ${d}` }));

const channelVariant = (c: CustomerChannel) =>
  c === "EXPORT" ? "blue" : c === "RETAIL" ? "green" : c === "ONLINE" ? "yellow" : "blue";

type EditForm = {
  name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  country: string;
  delivery_address: string;
  delivery_city: string;
  delivery_country: string;
  channel: string;
  payment_terms_days: string;
  credit_limit: string;
  tax_id: string;
  currency: string;
  notes: string;
};

const defaultForm = (): EditForm => ({
  name: "",
  contact_person: "",
  email: "",
  phone: "",
  address: "",
  city: "",
  country: "",
  delivery_address: "",
  delivery_city: "",
  delivery_country: "",
  channel: "WHOLESALE",
  payment_terms_days: "30",
  credit_limit: "",
  tax_id: "",
  currency: "USD",
  notes: "",
});

export default function CustomersPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<EditForm>(defaultForm());
  const [codeField, setCodeField] = useState("");

  const { data: customers = [], isLoading } = useQuery({
    queryKey: ["sales-customers"],
    queryFn: () => salesApi.listCustomers(false),
  });

  const createMut = useMutation({
    mutationFn: () =>
      salesApi.createCustomer({
        code: codeField,
        name: form.name,
        contact_person: form.contact_person || undefined,
        email: form.email || undefined,
        phone: form.phone || undefined,
        address: form.address || undefined,
        city: form.city || undefined,
        country: form.country || undefined,
        delivery_address: form.delivery_address || undefined,
        delivery_city: form.delivery_city || undefined,
        delivery_country: form.delivery_country || undefined,
        channel: form.channel as CustomerChannel,
        payment_terms_days: parseInt(form.payment_terms_days) || 30,
        credit_limit: form.credit_limit ? Number(form.credit_limit) : undefined,
        tax_id: form.tax_id || undefined,
        currency: form.currency,
        notes: form.notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sales-customers"] });
      setShowCreate(false);
      setForm(defaultForm());
      setCodeField("");
      toast("success", "Customer created");
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const updateMut = useMutation({
    mutationFn: () =>
      salesApi.updateCustomer(editId!, {
        name: form.name,
        contact_person: form.contact_person || undefined,
        email: form.email || undefined,
        phone: form.phone || undefined,
        channel: form.channel as CustomerChannel,
        payment_terms_days: parseInt(form.payment_terms_days) || 30,
        credit_limit: form.credit_limit ? Number(form.credit_limit) : undefined,
        currency: form.currency,
        notes: form.notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sales-customers"] });
      setEditId(null);
      toast("success", "Customer updated");
    },
    onError: (e) => toast("error", extractApiError(e)),
  });

  const openEdit = (c: typeof customers[0]) => {
    setForm({
      name: c.name,
      contact_person: c.contact_person || "",
      email: c.email || "",
      phone: c.phone || "",
      address: c.address || "",
      city: c.city || "",
      country: c.country || "",
      delivery_address: c.delivery_address || "",
      delivery_city: c.delivery_city || "",
      delivery_country: c.delivery_country || "",
      channel: c.channel,
      payment_terms_days: String(c.payment_terms_days),
      credit_limit: c.credit_limit !== undefined && c.credit_limit !== null ? String(c.credit_limit) : "",
      tax_id: c.tax_id || "",
      currency: c.currency,
      notes: c.notes || "",
    });
    setEditId(c.id);
  };

  const columns = [
    { header: "Code", accessor: (r: typeof customers[0]) => r.code },
    { header: "Name", accessor: (r: typeof customers[0]) => <span className="font-medium">{r.name}</span> },
    { header: "Channel", accessor: (r: typeof customers[0]) => (
      <Badge label={r.channel} variant={channelVariant(r.channel)} />
    )},
    { header: "Contact", accessor: (r: typeof customers[0]) => r.contact_person || "—" },
    { header: "Email", accessor: (r: typeof customers[0]) => r.email || "—" },
    { header: "Payment Terms", accessor: (r: typeof customers[0]) => `Net ${r.payment_terms_days}` },
    { header: "Credit Limit", accessor: (r: typeof customers[0]) =>
      r.credit_limit != null ? `${r.currency} ${Number(r.credit_limit).toLocaleString()}` : "—"
    },
    { header: "Status", accessor: (r: typeof customers[0]) => (
      <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "red"} />
    )},
    { header: "", accessor: (r: typeof customers[0]) => (
      <Button variant="secondary" onClick={() => openEdit(r)}>Edit</Button>
    )},
  ];

  const FormFields = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <Input label="Contact Person" value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Select label="Channel" options={CHANNEL_OPTS} value={form.channel} onChange={(e) => setForm({ ...form, channel: e.target.value })} />
        <Select label="Payment Terms" options={TERMS_OPTS} value={form.payment_terms_days} onChange={(e) => setForm({ ...form, payment_terms_days: e.target.value })} />
        <Select label="Currency" options={CURRENCY_OPTS} value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
      </div>
      <Input label="Credit Limit (optional)" type="number" value={form.credit_limit} onChange={(e) => setForm({ ...form, credit_limit: e.target.value })} />
      <Input label="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
    </div>
  );

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
          <p className="text-sm text-gray-500 mt-1">{customers.length} customers</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ Add Customer</Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : (
        <Table columns={columns} data={customers} keyField="id" emptyMessage="No customers found." />
      )}

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => { setShowCreate(false); setForm(defaultForm()); setCodeField(""); }} title="New Customer">
        <div className="space-y-4">
          <Input label="Customer Code" value={codeField} onChange={(e) => setCodeField(e.target.value)} required />
          <FormFields />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => { setShowCreate(false); setForm(defaultForm()); setCodeField(""); }}>Cancel</Button>
            <Button onClick={() => createMut.mutate()} disabled={createMut.isPending || !codeField || !form.name}>
              {createMut.isPending ? "Creating..." : "Create"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal open={!!editId} onClose={() => setEditId(null)} title="Edit Customer">
        <div className="space-y-4">
          <FormFields />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setEditId(null)}>Cancel</Button>
            <Button onClick={() => updateMut.mutate()} disabled={updateMut.isPending || !form.name}>
              {updateMut.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
