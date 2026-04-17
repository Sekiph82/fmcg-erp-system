"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  inventoryApi, MovementType, MovementDetail,
  extractApiError, extractStructuredError,
  MovementDeleteBlockedError,
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
import { PermissionGuard } from "@/components/PermissionGuard";

const movementVariant = (t: MovementType): "green" | "red" | "blue" | "yellow" | "gray" => ({
  RECEIPT: "green", ISSUE: "red", TRANSFER: "blue",
  ADJUSTMENT: "yellow", RETURN: "gray", WRITE_OFF: "red",
} as Record<MovementType, "green" | "red" | "blue" | "yellow" | "gray">)[t];

export default function MovementsPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();

  const [filterProduct, setFilterProduct] = useState("");
  const [filterWarehouse, setFilterWarehouse] = useState("");

  // ── Edit/Delete state ────────────────────────────────────────────────────────
  const [editingMovement, setEditingMovement] = useState<MovementDetail | null>(null);
  const [editRef, setEditRef] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [deletingMovement, setDeletingMovement] = useState<MovementDetail | null>(null);
  const [deleteBlockedError, setDeleteBlockedError] = useState<MovementDeleteBlockedError | null>(null);

  const { data: products = [] } = useQuery({ queryKey: ["products"], queryFn: () => productsApi.list(0, 200) });
  const { data: warehouses = [] } = useQuery({ queryKey: ["warehouses"], queryFn: () => warehousesApi.list(0, 200) });

  const { data: movements = [], isLoading } = useQuery({
    queryKey: ["movements-detail", filterProduct, filterWarehouse],
    queryFn: () => inventoryApi.movementDetail({
      product_id: filterProduct || undefined,
      warehouse_id: filterWarehouse || undefined,
    }),
  });

  const productOptions = [
    { value: "", label: "All products" },
    ...products.map((p) => ({ value: p.id, label: `${p.sku} — ${p.name}` })),
  ];
  const warehouseOptions = [
    { value: "", label: "All warehouses" },
    ...warehouses.map((w) => ({ value: w.id, label: `${w.code} — ${w.name}` })),
  ];

  // ── Edit movement ────────────────────────────────────────────────────────────
  const editMut = useMutation({
    mutationFn: ({ id, ref, notes }: { id: string; ref: string; notes: string }) =>
      inventoryApi.updateMovement(id, { reference_number: ref, notes: notes || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["movements-detail"] });
      setEditingMovement(null);
      toast("success", "Movement updated", "Reference and notes saved.");
    },
    onError: (err) => toast("error", "Update failed", extractApiError(err)),
  });

  // ── Delete movement ──────────────────────────────────────────────────────────
  const deleteMut = useMutation({
    mutationFn: (id: string) => inventoryApi.deleteMovement(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["movements-detail"] });
      qc.invalidateQueries({ queryKey: ["stock-summary"] });
      setDeletingMovement(null);
      toast("success", "Movement deleted", "The movement and its stock impact have been reversed.");
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        const structured = extractStructuredError(err) as MovementDeleteBlockedError | null;
        setDeletingMovement(null);
        setDeleteBlockedError(structured);
      } else if (status === 403) {
        toast("error", "Permission denied", "You do not have permission to delete movements.");
        setDeletingMovement(null);
      } else {
        toast("error", "Delete failed", extractApiError(err));
        setDeletingMovement(null);
      }
    },
  });

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Movement History</h1>
        <p className="text-sm text-gray-500 mt-1">{movements.length} records</p>
      </div>

      {/* Filters */}
      <div className="mb-5 flex gap-4">
        <div className="w-72">
          <Select options={productOptions} value={filterProduct}
            onChange={(e) => setFilterProduct(e.target.value)} />
        </div>
        <div className="w-72">
          <Select options={warehouseOptions} value={filterWarehouse}
            onChange={(e) => setFilterWarehouse(e.target.value)} />
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : (
        <Table
          keyField="id"
          data={movements}
          emptyMessage="No movements recorded yet."
          columns={[
            { header: "Date", accessor: "movement_date" },
            { header: "Ref #", accessor: "reference_number", className: "font-mono text-xs" },
            { header: "Type", accessor: (r) => <Badge label={r.movement_type} variant={movementVariant(r.movement_type)} /> },
            { header: "Product", accessor: (r) => r.product_name ? `${r.product_sku} — ${r.product_name}` : "—" },
            {
              header: "From",
              accessor: (r) => r.source_warehouse_name
                ? <span className="text-red-700">{r.source_warehouse_name}</span>
                : <span className="text-gray-400">—</span>,
            },
            {
              header: "To",
              accessor: (r) => r.destination_warehouse_name
                ? <span className="text-green-700">{r.destination_warehouse_name}</span>
                : <span className="text-gray-400">—</span>,
            },
            {
              header: "Qty",
              accessor: (r) => <span className="font-semibold tabular-nums">{Number(r.quantity).toLocaleString()}</span>,
            },
            {
              header: "Unit Cost",
              accessor: (r) => r.unit_cost
                ? <span className="tabular-nums">Rp {Number(r.unit_cost).toLocaleString()}</span>
                : "—",
            },
            { header: "By", accessor: (r) => r.created_by_username ?? "—" },
            { header: "Notes", accessor: (r) => r.notes ? <span className="text-gray-500 text-xs">{r.notes}</span> : "—" },
            {
              header: "Actions",
              accessor: (r) => (
                <div className="flex items-center gap-2">
                  <PermissionGuard permission="stock_movement.edit">
                    <button
                      onClick={() => {
                        setEditingMovement(r);
                        setEditRef(r.reference_number);
                        setEditNotes(r.notes ?? "");
                      }}
                      className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
                    >
                      Edit
                    </button>
                  </PermissionGuard>
                  <PermissionGuard permission="stock_movement.delete">
                    <button
                      onClick={() => setDeletingMovement(r)}
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
      )}

      {/* ── Edit Movement Modal ── */}
      <Modal
        open={!!editingMovement}
        onClose={() => setEditingMovement(null)}
        title="Edit Movement"
      >
        {editingMovement && (
          <div className="space-y-4">
            <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
              <p className="font-semibold">
                <Badge label={editingMovement.movement_type} variant={movementVariant(editingMovement.movement_type)} />
                <span className="ml-2">{editingMovement.product_name ?? "—"}</span>
              </p>
              <p className="text-xs mt-1">Qty: {Number(editingMovement.quantity).toLocaleString()} &nbsp;|&nbsp; Date: {editingMovement.movement_date}</p>
              <p className="text-xs mt-1 text-blue-600">Only reference number and notes can be edited. Quantity and type are immutable.</p>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                editMut.mutate({ id: editingMovement.id, ref: editRef, notes: editNotes });
              }}
              className="space-y-3"
            >
              <Input
                label="Reference #"
                value={editRef}
                onChange={(e) => setEditRef(e.target.value)}
                required
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  rows={3}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Optional notes…"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <Button variant="secondary" type="button" onClick={() => setEditingMovement(null)}>Cancel</Button>
                <Button type="submit" loading={editMut.isPending}>Save Changes</Button>
              </div>
            </form>
          </div>
        )}
      </Modal>

      {/* ── Delete Movement Confirm ── */}
      <Modal
        open={!!deletingMovement}
        onClose={() => setDeletingMovement(null)}
        title="Delete Movement"
      >
        {deletingMovement && (
          <div className="space-y-4">
            <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 text-sm">
              <p><span className="font-semibold">Ref:</span> {deletingMovement.reference_number}</p>
              <p><span className="font-semibold">Type:</span> {deletingMovement.movement_type}</p>
              <p><span className="font-semibold">Product:</span> {deletingMovement.product_name ?? "—"}</p>
              <p><span className="font-semibold">Qty:</span> {Number(deletingMovement.quantity).toLocaleString()}</p>
            </div>
            <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              <strong>Warning:</strong> Deleting this movement will reverse its stock impact.
              If this would cause stock to go below zero, the deletion will be blocked.
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setDeletingMovement(null)}>Cancel</Button>
              <Button
                variant="danger"
                loading={deleteMut.isPending}
                onClick={() => deleteMut.mutate(deletingMovement.id)}
              >
                Delete &amp; Reverse
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Delete Blocked Error ── */}
      <Modal
        open={!!deleteBlockedError}
        onClose={() => setDeleteBlockedError(null)}
        title="Cannot Delete Movement"
      >
        {deleteBlockedError && (
          <div className="space-y-4">
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
              <p className="font-semibold">{deleteBlockedError.message}</p>
              {deleteBlockedError.details?.hint && (
                <p className="text-xs mt-1">{deleteBlockedError.details.hint}</p>
              )}
            </div>
            <div className="flex justify-end">
              <Button variant="secondary" onClick={() => setDeleteBlockedError(null)}>Close</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
