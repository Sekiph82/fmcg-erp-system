"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { returnsApi, ReturnOrder, ReturnStatus, ReturnReason } from "@/lib/returns";
import { salesApi } from "@/lib/sales";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

const STATUS_COLORS: Record<ReturnStatus, "green" | "blue" | "yellow" | "gray" | "red"> = {
  DRAFT: "gray",
  SUBMITTED: "yellow",
  APPROVED: "blue",
  REJECTED: "red",
  PROCESSED: "green",
};

const REASONS: ReturnReason[] = [
  "DAMAGED", "EXPIRED", "WRONG_ITEM", "OVERSTOCKED", "QUALITY_ISSUE", "CUSTOMER_REFUSED", "OTHER",
];

const REASON_ICONS: Record<ReturnReason, string> = {
  DAMAGED: "💥",
  EXPIRED: "⏰",
  WRONG_ITEM: "❌",
  OVERSTOCKED: "📦",
  QUALITY_ISSUE: "🔍",
  CUSTOMER_REFUSED: "🚫",
  OTHER: "📝",
};

const emptyForm = {
  return_no: "",
  customer_id: "",
  original_so_id: "",
  return_date: new Date().toISOString().split("T")[0],
  reason: "DAMAGED" as ReturnReason,
  notes: "",
};

export default function ReturnsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<ReturnOrder | null>(null);
  const [filterStatus, setFilterStatus] = useState<ReturnStatus | "ALL">("ALL");
  const [form, setForm] = useState(emptyForm);

  const { data: returns = [], isLoading } = useQuery({
    queryKey: ["returns", filterStatus],
    queryFn: () => returnsApi.list(filterStatus !== "ALL" ? { status: filterStatus } : {}),
  });

  const { data: customers = [] } = useQuery({
    queryKey: ["customers-list"],
    queryFn: () => salesApi.listCustomers(),
  });

  const create = useMutation({
    mutationFn: () =>
      returnsApi.create({
        ...form,
        original_so_id: form.original_so_id || undefined,
        notes: form.notes || undefined,
        lines: [],
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["returns"] });
      setOpen(false);
      setForm(emptyForm);
    },
  });

  const approve = useMutation({
    mutationFn: (id: string) => returnsApi.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["returns"] });
      setSelected(null);
    },
  });

  const set = (k: keyof typeof emptyForm, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const statuses: (ReturnStatus | "ALL")[] = ["ALL", "DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "PROCESSED"];

  const pending = returns.filter((r) => r.status === "SUBMITTED").length;
  const approved = returns.filter((r) => r.status === "APPROVED").length;
  const processed = returns.filter((r) => r.status === "PROCESSED").length;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Returns</h1>
          <p className="text-sm text-gray-500 mt-1">Damaged · Expired · Wrong item · Customer refused</p>
        </div>
        <Button onClick={() => setOpen(true)}>+ New Return</Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { label: "Awaiting Approval", value: pending, color: "text-yellow-600" },
          { label: "Approved", value: approved, color: "text-blue-600" },
          { label: "Processed", value: processed, color: "text-green-600" },
        ].map((k) => (
          <div key={k.label} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm text-center">
            <p className={`text-3xl font-bold ${k.color}`}>{k.value}</p>
            <p className="text-xs text-gray-500 mt-1">{k.label}</p>
          </div>
        ))}
      </div>

      {/* Status filter */}
      <div className="flex flex-wrap gap-2 mb-5">
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filterStatus === s ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : returns.length === 0 ? (
        <p className="text-gray-400 text-sm py-8 text-center">No returns found.</p>
      ) : (
        <div className="space-y-3">
          {returns.map((r) => (
            <div
              key={r.id}
              onClick={() => setSelected(r)}
              className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm cursor-pointer hover:border-indigo-200 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{REASON_ICONS[r.reason]}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-gray-900">{r.return_no}</span>
                      <Badge label={r.status} variant={STATUS_COLORS[r.status]} />
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {r.customer_name} · {r.return_date} · {r.reason.replace("_", " ")}
                    </p>
                    {r.credit_note_no && (
                      <p className="text-xs text-blue-600 mt-0.5">Credit Note: {r.credit_note_no}</p>
                    )}
                  </div>
                </div>
                <div className="text-right text-xs text-gray-400">
                  {r.line_count} line{r.line_count !== 1 ? "s" : ""}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Return Detail Modal */}
      {selected && (
        <Modal open={!!selected} onClose={() => setSelected(null)} title={`Return: ${selected.return_no}`}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-500">Customer:</span> <span className="font-medium">{selected.customer_name}</span></div>
              <div><span className="text-gray-500">Date:</span> <span className="font-medium">{selected.return_date}</span></div>
              <div><span className="text-gray-500">Reason:</span> <span className="font-medium">{selected.reason.replace("_", " ")}</span></div>
              <div><span className="text-gray-500">Status:</span> <Badge label={selected.status} variant={STATUS_COLORS[selected.status]} /></div>
            </div>

            {selected.notes && (
              <div className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">{selected.notes}</div>
            )}

            {selected.lines.length > 0 && (
              <div>
                <p className="text-sm font-semibold text-gray-700 mb-2">Lines</p>
                <div className="space-y-1.5">
                  {selected.lines.map((l) => (
                    <div key={l.id} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-xs">
                      <div>
                        <span className="font-medium">{l.product_name}</span>
                        {l.return_reason && <span className="text-gray-400 ml-2">· {l.return_reason.replace("_", " ")}</span>}
                      </div>
                      <div className="flex items-center gap-3 text-gray-600">
                        <span>{l.quantity} {l.unit}</span>
                        <span className={`rounded px-2 py-0.5 ${
                          l.condition === "RESALEABLE" ? "bg-green-100 text-green-700" :
                          l.condition === "DAMAGED" ? "bg-red-100 text-red-700" :
                          "bg-yellow-100 text-yellow-700"
                        }`}>{l.condition}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selected.status === "SUBMITTED" && (
              <div className="flex justify-end gap-3 pt-2">
                <Button
                  variant="secondary"
                  onClick={() => returnsApi.update(selected.id, { status: "REJECTED" }).then(() => {
                    qc.invalidateQueries({ queryKey: ["returns"] });
                    setSelected(null);
                  })}
                >
                  Reject
                </Button>
                <Button onClick={() => approve.mutate(selected.id)} loading={approve.isPending}>
                  Approve
                </Button>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Create Return Modal */}
      <Modal open={open} onClose={() => setOpen(false)} title="New Return Order">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Return No *"
              value={form.return_no}
              onChange={(e) => set("return_no", e.target.value)}
              required
              placeholder="RET-001"
            />
            <Input
              label="Return Date *"
              type="date"
              value={form.return_date}
              onChange={(e) => set("return_date", e.target.value)}
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Return Reason *</label>
            <div className="grid grid-cols-2 gap-2">
              {REASONS.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => set("reason", r)}
                  className={`rounded-lg border px-3 py-2 text-left text-xs font-medium transition-colors ${
                    form.reason === r
                      ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                      : "border-gray-200 text-gray-600 hover:border-gray-300"
                  }`}
                >
                  {REASON_ICONS[r]} {r.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          <Input
            label="Original Sales Order (optional)"
            value={form.original_so_id}
            onChange={(e) => set("original_so_id", e.target.value)}
            placeholder="Order ID or order number"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              rows={2}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {create.error && <p className="text-sm text-red-600">Failed to create return.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create Return</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
