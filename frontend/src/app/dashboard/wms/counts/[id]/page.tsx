"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { wmsApi, StockCountLine } from "@/lib/wms";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";

const statusVariant = (s: string) =>
  s === "APPROVED" ? "green"
  : s === "PENDING_APPROVAL" || s === "IN_PROGRESS" ? "blue"
  : s === "CANCELLED" ? "red"
  : "blue";

export default function StockCountDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [editingLine, setEditingLine] = useState<string | null>(null);
  const [countedQty, setCountedQty] = useState<string>("");
  const [search, setSearch] = useState("");

  const { data: count, isLoading } = useQuery({
    queryKey: ["wms-count", id],
    queryFn: () => wmsApi.getCount(id),
    enabled: !!id,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["wms-count", id] });

  const recordLine = useMutation({
    mutationFn: ({ lineId, qty }: { lineId: string; qty: number }) =>
      wmsApi.recordLine(id, lineId, { counted_quantity: qty }),
    onSuccess: () => { invalidate(); setEditingLine(null); setCountedQty(""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const submit = useMutation({
    mutationFn: () => wmsApi.submitCount(id),
    onSuccess: () => { invalidate(); toast("success", "Submitted", "Count pending approval."); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const approve = useMutation({
    mutationFn: () => wmsApi.approveCount(id),
    onSuccess: () => { invalidate(); toast("success", "Approved", "Variances applied as adjustments."); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  const cancel = useMutation({
    mutationFn: () => wmsApi.cancelCount(id),
    onSuccess: () => { invalidate(); toast("success", "Cancelled", ""); },
    onError: (e) => toast("error", "Failed", extractApiError(e)),
  });

  if (isLoading) return <div className="flex justify-center py-24"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>;
  if (!count) return <div className="text-center py-16 text-gray-500">Count not found.</div>;

  const isInProgress = count.status === "IN_PROGRESS";
  const isPending = count.status === "PENDING_APPROVAL";

  const filtered = (count.lines ?? []).filter((l) => {
    const term = search.toLowerCase();
    return (
      !term ||
      (l.product_name ?? "").toLowerCase().includes(term) ||
      (l.product_sku ?? "").toLowerCase().includes(term) ||
      (l.material_name ?? "").toLowerCase().includes(term) ||
      (l.lot_number ?? "").toLowerCase().includes(term) ||
      (l.location_code ?? "").toLowerCase().includes(term)
    );
  });

  const uncounted = (count.lines ?? []).filter((l) => !l.is_counted).length;
  const variances = (count.lines ?? []).filter((l) => l.is_counted && l.variance !== 0 && l.variance != null);

  return (
    <div className="space-y-6">
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <button className="text-sm text-indigo-600 hover:underline mb-2 block" onClick={() => router.push("/dashboard/wms/counts")}>
              ← Back to Stock Counts
            </button>
            <h1 className="text-2xl font-bold text-gray-900 font-mono">{count.count_no}</h1>
            <p className="text-sm text-gray-500 mt-1">
              {count.count_type === "CYCLE" ? "Cycle Count" : "Full Count"} · {count.warehouse_name}
              {count.zone_name && ` · Zone: ${count.zone_name}`}
            </p>
          </div>
          <div className="flex flex-col items-end gap-3">
            <Badge label={count.status.replace(/_/g, " ")} variant={statusVariant(count.status)} />
            <div className="flex gap-2">
              {isPending && (
                <Button onClick={() => approve.mutate()} loading={approve.isPending}>
                  Approve & Apply
                </Button>
              )}
              {isInProgress && uncounted === 0 && (
                <Button onClick={() => submit.mutate()} loading={submit.isPending}>
                  Submit for Approval
                </Button>
              )}
              {(isInProgress || count.status === "DRAFT") && (
                <Button variant="secondary" onClick={() => cancel.mutate()} loading={cancel.isPending}>
                  Cancel
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Progress */}
        <div className="mt-4 grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
          <div>
            <p className="text-xs text-gray-500">Total Lines</p>
            <p className="text-xl font-bold">{count.total_lines}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Counted</p>
            <p className="text-xl font-bold text-green-600">{count.counted_lines}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Variances</p>
            <p className={`text-xl font-bold ${variances.length > 0 ? "text-amber-600" : "text-gray-400"}`}>
              {variances.length}
            </p>
          </div>
        </div>

        {/* Progress bar */}
        {count.total_lines > 0 && (
          <div className="mt-3">
            <div className="h-2 rounded-full bg-gray-200">
              <div
                className="h-2 rounded-full bg-indigo-600 transition-all"
                style={{ width: `${(count.counted_lines / count.total_lines) * 100}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">
              {Math.round((count.counted_lines / count.total_lines) * 100)}% complete
            </p>
          </div>
        )}
      </div>

      {/* Variance summary */}
      {variances.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800 mb-2">{variances.length} lines with variance</p>
          <div className="space-y-1">
            {variances.map((l) => (
              <p key={l.id} className="text-xs text-amber-700">
                {l.product_name || l.material_name}
                {l.lot_number && ` (Lot: ${l.lot_number})`}
                {" — "}
                System: {l.system_quantity} · Counted: {l.counted_quantity} ·{" "}
                <span className={Number(l.variance) > 0 ? "text-green-700 font-medium" : "text-red-700 font-medium"}>
                  {Number(l.variance) > 0 ? "+" : ""}{l.variance} {l.unit}
                </span>
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Count lines */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Count Lines</h2>
          <Input
            placeholder="Search by product, lot, location…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
        </div>
        <Table
          keyField="id"
          data={filtered}
          emptyMessage="No lines generated. Start the count to snapshot current stock."
          columns={[
            {
              header: "Item",
              accessor: (l) => (
                <span>
                  {l.product_sku && <span className="font-mono text-xs text-gray-400 mr-1">{l.product_sku}</span>}
                  {l.product_name || l.material_name || "—"}
                </span>
              ),
            },
            { header: "Lot", accessor: (l) => l.lot_number ? <span className="font-mono text-xs">{l.lot_number}</span> : "—" },
            { header: "Location", accessor: (l) => l.location_code ? <span className="font-mono text-xs">{l.location_code}</span> : "—" },
            { header: "System Qty", accessor: (l) => `${Number(l.system_quantity).toFixed(3)} ${l.unit}` },
            {
              header: "Counted Qty",
              accessor: (l) => {
                if (!isInProgress) {
                  return l.counted_quantity != null
                    ? `${Number(l.counted_quantity).toFixed(3)} ${l.unit}`
                    : "—";
                }
                if (editingLine === l.id) {
                  return (
                    <div className="flex gap-2 items-center">
                      <input
                        type="number"
                        step="0.001"
                        autoFocus
                        className="w-24 rounded border border-gray-300 px-2 py-1 text-sm"
                        value={countedQty}
                        onChange={(e) => setCountedQty(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            recordLine.mutate({ lineId: l.id, qty: parseFloat(countedQty) || 0 });
                          }
                          if (e.key === "Escape") { setEditingLine(null); setCountedQty(""); }
                        }}
                      />
                      <Button
                        onClick={() => recordLine.mutate({ lineId: l.id, qty: parseFloat(countedQty) || 0 })}
                        loading={recordLine.isPending}
                      >
                        Save
                      </Button>
                    </div>
                  );
                }
                return (
                  <button
                    className="text-left text-indigo-600 hover:underline text-sm"
                    onClick={() => {
                      setEditingLine(l.id);
                      setCountedQty(l.counted_quantity != null ? String(l.counted_quantity) : String(l.system_quantity));
                    }}
                  >
                    {l.counted_quantity != null ? `${Number(l.counted_quantity).toFixed(3)} ${l.unit}` : "Click to count"}
                  </button>
                );
              },
            },
            {
              header: "Variance",
              accessor: (l) => {
                if (l.variance == null) return "—";
                const v = Number(l.variance);
                return (
                  <span className={v > 0.0005 ? "text-green-600 font-medium" : v < -0.0005 ? "text-red-500 font-medium" : "text-gray-400"}>
                    {v > 0 ? "+" : ""}{v.toFixed(3)} {l.unit}
                  </span>
                );
              },
            },
            {
              header: "",
              accessor: (l) => (
                <Badge
                  label={l.is_counted ? "Counted" : "Pending"}
                  variant={l.is_counted ? "green" : "blue"}
                />
              ),
            },
          ]}
        />
      </div>
    </div>
  );
}
