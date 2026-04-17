"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  inventoryApi,
  StockSummary,
  StockEntryRequest, StockIssueRequest, StockTransferRequest,
  extractApiError, extractStructuredError, isInsufficientStock,
  InventoryDeleteBlockedError,
} from "@/lib/inventory";
import { productsApi } from "@/lib/products";
import { warehousesApi } from "@/lib/warehouses";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { RequirePermission, PermissionGuard } from "@/components/PermissionGuard";
import { ImportModal } from "@/components/import/ImportModal";

type Tab = "stock" | "entry" | "issue" | "transfer";

const today = new Date().toISOString().split("T")[0];

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-gray-800 mb-4">{title}</h2>
      {children}
    </div>
  );
}

const TABS: { key: Tab; label: string; color?: string }[] = [
  { key: "stock", label: "Current Stock" },
  { key: "entry", label: "Stock Entry (IN)", color: "text-green-700" },
  { key: "issue", label: "Stock Issue (OUT)", color: "text-red-700" },
  { key: "transfer", label: "Transfer", color: "text-blue-700" },
];

function InventoryContent() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [tab, setTab] = useState<Tab>("stock");

  // ── Edit/Delete state ────────────────────────────────────────────────────────
  const [adjustingStock, setAdjustingStock] = useState<StockSummary | null>(null);
  const [adjustQty, setAdjustQty] = useState("");
  const [adjustReason, setAdjustReason] = useState("");
  const [deletingStockId, setDeletingStockId] = useState<string | null>(null);
  const [deleteBlockedError, setDeleteBlockedError] = useState<InventoryDeleteBlockedError | null>(null);

  // ── Shared data ──────────────────────────────────────────────────────────────
  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: () => productsApi.list(0, 200) });
  const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses"], queryFn: () => warehousesApi.list(0, 200) });
  const { data: summary = [], isLoading: loadingSummary, refetch: refetchSummary } = useQuery({
    queryKey: ["stock-summary"],
    queryFn: () => inventoryApi.stockSummary(),
  });

  const productOptions = [
    { value: "", label: "— Select product —" },
    ...products.map((p) => ({ value: p.id, label: `${p.sku} — ${p.name}` })),
  ];
  const warehouseOptions = [
    { value: "", label: "— Select warehouse —" },
    ...warehouses.map((w) => ({ value: w.id, label: `${w.code} — ${w.name}` })),
  ];

  // ── Stock Entry ──────────────────────────────────────────────────────────────
  const [entry, setEntry] = useState<Partial<StockEntryRequest>>({ reference: `GR-${today}` });
  const setE = (k: keyof StockEntryRequest, v: unknown) => setEntry((f) => ({ ...f, [k]: v }));

  const entryMut = useMutation({
    mutationFn: (d: StockEntryRequest) => inventoryApi.stockEntry(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stock-summary"] });
      setEntry({ reference: `GR-${today}` });
      toast("success", "Stock received", "Inventory updated successfully.");
      setTab("stock");
    },
    onError: (err) => toast("error", "Entry failed", extractApiError(err)),
  });

  // ── Stock Issue ──────────────────────────────────────────────────────────────
  const [issue, setIssue] = useState<Partial<StockIssueRequest>>({ reference: `SO-${today}` });
  const setI = (k: keyof StockIssueRequest, v: unknown) => setIssue((f) => ({ ...f, [k]: v }));

  const issueMut = useMutation({
    mutationFn: (d: StockIssueRequest) => inventoryApi.stockIssue(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stock-summary"] });
      setIssue({ reference: `SO-${today}` });
      toast("success", "Stock issued", "Inventory updated successfully.");
      setTab("stock");
    },
    onError: (err) => {
      const insuf = isInsufficientStock(err);
      if (insuf) {
        toast("error", "Insufficient Stock", insuf.message);
      } else {
        toast("error", "Issue failed", extractApiError(err));
      }
    },
  });

  // ── Stock Transfer ───────────────────────────────────────────────────────────
  const [transfer, setTransfer] = useState<Partial<StockTransferRequest>>({ reference: `TRF-${today}` });
  const setT = (k: keyof StockTransferRequest, v: unknown) => setTransfer((f) => ({ ...f, [k]: v }));

  const transferMut = useMutation({
    mutationFn: (d: StockTransferRequest) => inventoryApi.stockTransfer(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stock-summary"] });
      setTransfer({ reference: `TRF-${today}` });
      toast("success", "Transfer complete", "Stock moved between warehouses.");
      setTab("stock");
    },
    onError: (err) => {
      const insuf = isInsufficientStock(err);
      if (insuf) {
        toast("error", "Insufficient Stock", insuf.message);
      } else {
        toast("error", "Transfer failed", extractApiError(err));
      }
    },
  });

  // ── Adjust Stock (Edit) ──────────────────────────────────────────────────────
  const adjustMut = useMutation({
    mutationFn: ({ id, qty, reason }: { id: string; qty: number; reason: string }) =>
      inventoryApi.adjustStock(id, { new_quantity: qty, reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stock-summary"] });
      setAdjustingStock(null);
      setAdjustQty("");
      setAdjustReason("");
      toast("success", "Stock adjusted", "Adjustment movement created and inventory updated.");
    },
    onError: (err) => toast("error", "Adjustment failed", extractApiError(err)),
  });

  // ── Delete Stock ─────────────────────────────────────────────────────────────
  const deletingStockRecord = summary.find((s) => s.id === deletingStockId);

  const deleteStockMut = useMutation({
    mutationFn: (id: string) => inventoryApi.deleteStock(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["stock-summary"] });
      setDeletingStockId(null);
      toast("success", "Stock record deleted", "The stock position has been removed.");
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        const structured = extractStructuredError(err) as InventoryDeleteBlockedError | null;
        setDeletingStockId(null);
        setDeleteBlockedError(structured);
      } else if (status === 403) {
        toast("error", "Permission denied", "You do not have permission to delete stock records.");
        setDeletingStockId(null);
      } else {
        toast("error", "Delete failed", extractApiError(err));
        setDeletingStockId(null);
      }
    },
  });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
          <p className="text-sm text-gray-500 mt-1">{summary.length} stock positions</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal
            module="inventory_stock"
            onSuccess={() => refetchSummary()}
          />
          <Button variant="secondary" onClick={() => refetchSummary()}>Refresh</Button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-white shadow-sm text-gray-900"
                : `text-gray-500 hover:text-gray-700 ${t.color ?? ""}`
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Stock Summary ── */}
      {tab === "stock" && (
        loadingSummary ? (
          <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
        ) : (
          <Table
            keyField="id"
            data={summary}
            emptyMessage="No stock records. Use Stock Entry to receive goods."
            columns={[
              { header: "SKU", accessor: (r) => <span className="font-mono text-xs">{r.product_sku ?? "—"}</span> },
              { header: "Product", accessor: (r) => r.product_name ?? "—" },
              { header: "Warehouse", accessor: (r) => `${r.warehouse_code} — ${r.warehouse_name}` },
              { header: "Lot", accessor: (r) => r.lot_number ?? <span className="text-gray-400">no lot</span> },
              { header: "Expiry", accessor: (r) => r.expiry_date ?? "—" },
              {
                header: "On Hand",
                accessor: (r) => (
                  <span className={r.is_below_reorder ? "font-bold text-red-600" : "font-semibold"}>
                    {Number(r.quantity_on_hand).toLocaleString()}
                    {r.is_below_reorder && <span className="ml-1 text-xs">⚠ low</span>}
                  </span>
                ),
              },
              {
                header: "Available",
                accessor: (r) => <span className="text-emerald-700 font-medium">{Number(r.quantity_available).toLocaleString()}</span>,
              },
              { header: "Reserved", accessor: (r) => Number(r.quantity_reserved).toLocaleString() },
              {
                header: "Actions",
                accessor: (r) => (
                  <div className="flex items-center gap-2">
                    <PermissionGuard permission="inventory.edit">
                      <button
                        onClick={() => {
                          setAdjustingStock(r);
                          setAdjustQty(String(Number(r.quantity_on_hand)));
                          setAdjustReason("");
                        }}
                        className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
                      >
                        Adjust
                      </button>
                    </PermissionGuard>
                    <PermissionGuard permission="inventory.delete">
                      <button
                        onClick={() => setDeletingStockId(r.id)}
                        className="text-xs text-red-500 hover:text-red-700 hover:underline"
                      >
                        Delete
                      </button>
                    </PermissionGuard>
                  </div>
                ),
              },
            ]}
          />
        )
      )}

      {/* ── Stock Entry (IN) ── */}
      {tab === "entry" && (
        <FormSection title="Receive Stock into Warehouse">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              entryMut.mutate(entry as StockEntryRequest);
            }}
            className="space-y-4 max-w-lg"
          >
            <Select label="Product *" options={productOptions} value={entry.product_id ?? ""}
              onChange={(e) => setE("product_id", e.target.value || undefined)} />
            <Select label="Warehouse *" options={warehouseOptions} value={entry.warehouse_id ?? ""}
              onChange={(e) => setE("warehouse_id", e.target.value || undefined)} />
            <div className="grid grid-cols-2 gap-4">
              <Input label="Quantity *" type="number" step="0.001" min="0.001"
                value={entry.quantity ?? ""}
                onChange={(e) => setE("quantity", parseFloat(e.target.value))} required />
              <Input label="Unit Cost (Rp)" type="number" step="0.01"
                value={entry.unit_cost ?? ""}
                onChange={(e) => setE("unit_cost", parseFloat(e.target.value) || undefined)} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input label="Lot Number" placeholder="LOT-2026-001"
                value={entry.lot_number ?? ""}
                onChange={(e) => setE("lot_number", e.target.value || undefined)} />
              <Input label="Expiry Date" type="date"
                value={entry.expiry_date ?? ""}
                onChange={(e) => setE("expiry_date", e.target.value || undefined)} />
            </div>
            <Input label="Reference # *" placeholder="PO-001" value={entry.reference ?? ""}
              onChange={(e) => setE("reference", e.target.value)} required />
            <Input label="Notes" onChange={(e) => setE("notes", e.target.value || undefined)} />
            <div className="flex gap-3 pt-2">
              <Button type="submit" loading={entryMut.isPending}>Receive Stock</Button>
              <Button variant="secondary" type="button" onClick={() => setEntry({ reference: `GR-${today}` })}>Reset</Button>
            </div>
          </form>
        </FormSection>
      )}

      {/* ── Stock Issue (OUT) ── */}
      {tab === "issue" && (
        <FormSection title="Issue Stock from Warehouse">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              issueMut.mutate(issue as StockIssueRequest);
            }}
            className="space-y-4 max-w-lg"
          >
            <Select label="Product *" options={productOptions} value={issue.product_id ?? ""}
              onChange={(e) => setI("product_id", e.target.value || undefined)} />
            <Select label="Warehouse *" options={warehouseOptions} value={issue.warehouse_id ?? ""}
              onChange={(e) => setI("warehouse_id", e.target.value || undefined)} />
            <div className="grid grid-cols-2 gap-4">
              <Input label="Quantity *" type="number" step="0.001" min="0.001"
                value={issue.quantity ?? ""}
                onChange={(e) => setI("quantity", parseFloat(e.target.value))} required />
              <Input label="Lot Number (optional)" placeholder="LOT-2026-001"
                value={issue.lot_number ?? ""}
                onChange={(e) => setI("lot_number", e.target.value || undefined)} />
            </div>
            <Input label="Reference # *" placeholder="SO-001" value={issue.reference ?? ""}
              onChange={(e) => setI("reference", e.target.value)} required />
            <Input label="Notes" onChange={(e) => setI("notes", e.target.value || undefined)} />
            <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              The system will reject this if available stock is insufficient.
            </div>
            <div className="flex gap-3 pt-2">
              <Button type="submit" loading={issueMut.isPending}>Issue Stock</Button>
              <Button variant="secondary" type="button" onClick={() => setIssue({ reference: `SO-${today}` })}>Reset</Button>
            </div>
          </form>
        </FormSection>
      )}

      {/* ── Transfer ── */}
      {tab === "transfer" && (
        <FormSection title="Transfer Stock Between Warehouses">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              transferMut.mutate(transfer as StockTransferRequest);
            }}
            className="space-y-4 max-w-lg"
          >
            <Select label="Product *" options={productOptions} value={transfer.product_id ?? ""}
              onChange={(e) => setT("product_id", e.target.value || undefined)} />
            <div className="grid grid-cols-2 gap-4">
              <Select label="From Warehouse *" options={warehouseOptions} value={transfer.from_warehouse_id ?? ""}
                onChange={(e) => setT("from_warehouse_id", e.target.value || undefined)} />
              <Select label="To Warehouse *" options={warehouseOptions} value={transfer.to_warehouse_id ?? ""}
                onChange={(e) => setT("to_warehouse_id", e.target.value || undefined)} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input label="Quantity *" type="number" step="0.001" min="0.001"
                value={transfer.quantity ?? ""}
                onChange={(e) => setT("quantity", parseFloat(e.target.value))} required />
              <Input label="Lot Number (optional)"
                value={transfer.lot_number ?? ""}
                onChange={(e) => setT("lot_number", e.target.value || undefined)} />
            </div>
            <Input label="Reference # *" placeholder="TRF-001" value={transfer.reference ?? ""}
              onChange={(e) => setT("reference", e.target.value)} required />
            <Input label="Notes" onChange={(e) => setT("notes", e.target.value || undefined)} />
            <div className="flex gap-3 pt-2">
              <Button type="submit" loading={transferMut.isPending}>Transfer Stock</Button>
              <Button variant="secondary" type="button" onClick={() => setTransfer({ reference: `TRF-${today}` })}>Reset</Button>
            </div>
          </form>
        </FormSection>
      )}

      {/* ── Adjust Stock Modal ── */}
      <Modal
        open={!!adjustingStock}
        onClose={() => { setAdjustingStock(null); setAdjustQty(""); setAdjustReason(""); }}
        title="Adjust Stock"
      >
        {adjustingStock && (
          <div className="space-y-4">
            <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
              <p className="font-semibold">{adjustingStock.product_name} ({adjustingStock.product_sku})</p>
              <p className="text-xs mt-1">
                Warehouse: {adjustingStock.warehouse_name} &nbsp;|&nbsp;
                Current on-hand: <strong>{Number(adjustingStock.quantity_on_hand).toLocaleString()}</strong>
              </p>
              <p className="text-xs mt-1 text-blue-600">
                This will create an ADJUSTMENT movement recording the change.
              </p>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const qty = parseFloat(adjustQty);
                if (isNaN(qty) || qty < 0) return;
                adjustMut.mutate({ id: adjustingStock.id, qty, reason: adjustReason });
              }}
              className="space-y-3"
            >
              <Input
                label="New Quantity *"
                type="number"
                step="0.001"
                min="0"
                value={adjustQty}
                onChange={(e) => setAdjustQty(e.target.value)}
                required
              />
              <Input
                label="Reason *"
                placeholder="e.g. Physical count correction, damaged goods write-off…"
                value={adjustReason}
                onChange={(e) => setAdjustReason(e.target.value)}
                required
              />
              {adjustQty !== "" && !isNaN(parseFloat(adjustQty)) && (
                <div className="text-xs text-gray-500">
                  Delta:{" "}
                  <span className={parseFloat(adjustQty) - Number(adjustingStock.quantity_on_hand) >= 0 ? "text-green-700 font-semibold" : "text-red-700 font-semibold"}>
                    {(parseFloat(adjustQty) - Number(adjustingStock.quantity_on_hand) >= 0 ? "+" : "") +
                      (parseFloat(adjustQty) - Number(adjustingStock.quantity_on_hand)).toLocaleString()}
                  </span>
                </div>
              )}
              <div className="flex justify-end gap-3 pt-2">
                <Button variant="secondary" type="button" onClick={() => { setAdjustingStock(null); setAdjustQty(""); setAdjustReason(""); }}>
                  Cancel
                </Button>
                <Button type="submit" loading={adjustMut.isPending}>Apply Adjustment</Button>
              </div>
            </form>
          </div>
        )}
      </Modal>

      {/* ── Delete Stock Confirm ── */}
      <Modal
        open={!!deletingStockId}
        onClose={() => setDeletingStockId(null)}
        title="Delete Stock Record"
      >
        <div className="space-y-4">
          {deletingStockRecord && (
            <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 text-sm">
              <p><span className="font-semibold">Product:</span> {deletingStockRecord.product_name} ({deletingStockRecord.product_sku})</p>
              <p><span className="font-semibold">Warehouse:</span> {deletingStockRecord.warehouse_name}</p>
              <p><span className="font-semibold">On Hand:</span> {Number(deletingStockRecord.quantity_on_hand).toLocaleString()}</p>
            </div>
          )}
          {deletingStockRecord && Number(deletingStockRecord.quantity_on_hand) !== 0 ? (
            <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              <strong>Warning:</strong> This stock record still has{" "}
              <strong>{Number(deletingStockRecord.quantity_on_hand).toLocaleString()}</strong> units on hand.
              You must adjust the quantity to zero before deleting this record.
            </div>
          ) : (
            <p className="text-sm text-gray-600">
              This will permanently delete this stock position. This action cannot be undone.
            </p>
          )}
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setDeletingStockId(null)}>Cancel</Button>
            <Button
              variant="danger"
              loading={deleteStockMut.isPending}
              onClick={() => deletingStockId && deleteStockMut.mutate(deletingStockId)}
              disabled={!!deletingStockRecord && Number(deletingStockRecord.quantity_on_hand) !== 0}
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>

      {/* ── Delete Blocked Error ── */}
      <Modal
        open={!!deleteBlockedError}
        onClose={() => setDeleteBlockedError(null)}
        title="Cannot Delete Stock Record"
      >
        {deleteBlockedError && (
          <div className="space-y-4">
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
              <p className="font-semibold">{deleteBlockedError.message}</p>
            </div>
            {deleteBlockedError.details?.references?.length > 0 && (
              <ul className="space-y-2">
                {deleteBlockedError.details.references.map((ref) => (
                  <li key={ref.module} className="text-sm flex gap-2">
                    <span className="font-semibold text-gray-800">{ref.module}</span>
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">{ref.count}</span>
                    <span className="text-gray-500 text-xs">{ref.hint}</span>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => setDeleteBlockedError(null)}>Close</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default function InventoryPage() {
  return (
    <RequirePermission permission="inventory.view">
      <InventoryContent />
    </RequirePermission>
  );
}
