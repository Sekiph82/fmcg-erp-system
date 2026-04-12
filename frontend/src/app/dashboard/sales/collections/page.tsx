"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  collectionsApi,
  Collection,
  CollectionMethod,
  CollectionStatus,
  METHOD_COLORS,
  METHOD_ICONS,
  STATUS_COLORS,
} from "@/lib/collections";
import { salesApi } from "@/lib/sales";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

const METHODS: CollectionMethod[] = ["CASH", "MPESA", "BANK_TRANSFER", "CHEQUE", "CREDIT_NOTE"];

const emptyForm = {
  collection_no: "",
  customer_id: "",
  sales_order_id: "",
  collection_date: new Date().toISOString().split("T")[0],
  method: "MPESA" as CollectionMethod,
  amount: "",
  currency: "KES",
  reference: "",
  mpesa_code: "",
  mpesa_phone: "",
  notes: "",
};

export default function CollectionsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [filterMethod, setFilterMethod] = useState<CollectionMethod | "ALL">("ALL");
  const [filterStatus, setFilterStatus] = useState<CollectionStatus | "ALL">("ALL");

  const { data: collections = [], isLoading } = useQuery({
    queryKey: ["collections", filterMethod, filterStatus],
    queryFn: () =>
      collectionsApi.list({
        ...(filterMethod !== "ALL" ? { method: filterMethod } : {}),
        ...(filterStatus !== "ALL" ? { status: filterStatus } : {}),
      }),
  });

  const { data: customers = [] } = useQuery({
    queryKey: ["customers-list"],
    queryFn: () => salesApi.listCustomers(),
  });

  const create = useMutation({
    mutationFn: () =>
      collectionsApi.create({
        ...form,
        amount: parseFloat(form.amount as string) || 0,
        sales_order_id: form.sales_order_id || undefined,
        reference: form.reference || undefined,
        mpesa_code: form.mpesa_code || undefined,
        mpesa_phone: form.mpesa_phone || undefined,
        notes: form.notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["collections"] });
      setOpen(false);
      setForm(emptyForm);
    },
  });

  const confirm = useMutation({
    mutationFn: (id: string) => collectionsApi.confirm(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collections"] }),
  });

  const reconcile = useMutation({
    mutationFn: (id: string) => collectionsApi.reconcile(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collections"] }),
  });

  const set = (k: keyof typeof emptyForm, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const totalAmount = collections.reduce((s, c) => s + c.amount, 0);
  const mpesaTotal = collections.filter((c) => c.method === "MPESA").reduce((s, c) => s + c.amount, 0);
  const cashTotal = collections.filter((c) => c.method === "CASH").reduce((s, c) => s + c.amount, 0);
  const pending = collections.filter((c) => c.status === "PENDING").length;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Collections</h1>
          <p className="text-sm text-gray-500 mt-1">Cash · M-Pesa · Bank receipts from the field</p>
        </div>
        <Button onClick={() => setOpen(true)}>+ Record Collection</Button>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Total Collected", value: `KES ${totalAmount.toLocaleString()}`, color: "text-indigo-600" },
          { label: "M-Pesa", value: `KES ${mpesaTotal.toLocaleString()}`, color: "text-emerald-600" },
          { label: "Cash", value: `KES ${cashTotal.toLocaleString()}`, color: "text-green-600" },
          { label: "Pending Confirmation", value: pending, color: pending > 0 ? "text-yellow-600" : "text-gray-500" },
        ].map((k) => (
          <div key={k.label} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
            <p className="text-xs text-gray-500 mt-1">{k.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <div className="flex gap-1">
          {(["ALL", ...METHODS] as const).map((m) => (
            <button
              key={m}
              onClick={() => setFilterMethod(m)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                filterMethod === m ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {m !== "ALL" ? `${METHOD_ICONS[m]} ${m}` : "ALL"}
            </button>
          ))}
        </div>
        <div className="flex gap-1 ml-auto">
          {(["ALL", "PENDING", "CONFIRMED", "RECONCILED"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s as CollectionStatus | "ALL")}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                filterStatus === s ? "bg-gray-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : collections.length === 0 ? (
        <p className="text-gray-400 text-sm py-8 text-center">No collections found.</p>
      ) : (
        <div className="space-y-2">
          {collections.map((c) => (
            <CollectionRow
              key={c.id}
              collection={c}
              onConfirm={() => confirm.mutate(c.id)}
              onReconcile={() => reconcile.mutate(c.id)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal open={open} onClose={() => setOpen(false)} title="Record Collection">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Collection No *"
              value={form.collection_no}
              onChange={(e) => set("collection_no", e.target.value)}
              required
              placeholder="COL-001"
            />
            <Input
              label="Date *"
              type="date"
              value={form.collection_date}
              onChange={(e) => set("collection_date", e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Customer *</label>
            <select
              value={form.customer_id}
              onChange={(e) => set("customer_id", e.target.value)}
              required
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select customer…</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Method *</label>
            <div className="grid grid-cols-3 gap-2">
              {METHODS.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => set("method", m)}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                    form.method === m
                      ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  {METHOD_ICONS[m]} {m}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Amount *"
              type="number"
              step="0.01"
              value={form.amount}
              onChange={(e) => set("amount", e.target.value)}
              required
              placeholder="0.00"
            />
            <Input
              label="Currency"
              value={form.currency}
              onChange={(e) => set("currency", e.target.value)}
              placeholder="KES"
            />
          </div>

          {form.method === "MPESA" && (
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="M-Pesa Code"
                value={form.mpesa_code}
                onChange={(e) => set("mpesa_code", e.target.value)}
                placeholder="e.g. QJK2X7ABC1"
              />
              <Input
                label="Phone"
                value={form.mpesa_phone}
                onChange={(e) => set("mpesa_phone", e.target.value)}
                placeholder="2547XXXXXXXX"
              />
            </div>
          )}

          {form.method !== "MPESA" && (
            <Input
              label="Reference / Cheque No"
              value={form.reference}
              onChange={(e) => set("reference", e.target.value)}
              placeholder="Bank ref or cheque number"
            />
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {create.error && <p className="text-sm text-red-600">Failed to record collection.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Record</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function CollectionRow({
  collection: c,
  onConfirm,
  onReconcile,
}: {
  collection: Collection;
  onConfirm: () => void;
  onReconcile: () => void;
}) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{METHOD_ICONS[c.method]}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-gray-700">{c.collection_no}</span>
              <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${METHOD_COLORS[c.method]}`}>
                {c.method}
              </span>
              <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[c.status]}`}>
                {c.status}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              {c.customer_name} · {c.collection_date}
              {c.rep_name && <span> · {c.rep_name}</span>}
              {c.mpesa_code && <span> · <span className="font-mono">{c.mpesa_code}</span></span>}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-lg font-bold text-gray-900">
            {c.currency} {c.amount.toLocaleString()}
          </p>
          {c.status === "PENDING" && (
            <Button variant="secondary" onClick={onConfirm}>Confirm</Button>
          )}
          {c.status === "CONFIRMED" && (
            <Button variant="secondary" onClick={onReconcile}>Reconcile</Button>
          )}
        </div>
      </div>
    </div>
  );
}
