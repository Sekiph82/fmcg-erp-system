"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { warehousesApi, WarehouseCreate, WarehouseType } from "@/lib/warehouses";
import { extractApiError } from "@/lib/inventory";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ToastContainer } from "@/components/ui/Toast";
import { useToast } from "@/hooks/useToast";
import { ImportModal } from "@/components/import/ImportModal";

const TYPES: { value: string; label: string }[] = [
  { value: "FINISHED_GOODS", label: "Finished Goods" },
  { value: "RAW_MATERIAL", label: "Raw Material" },
  { value: "TRANSIT", label: "Transit" },
  { value: "RETURNS", label: "Returns" },
];

const typeVariant = (t: WarehouseType): "blue" | "yellow" | "gray" | "red" => {
  const map: Record<WarehouseType, "blue" | "yellow" | "gray" | "red"> = {
    FINISHED_GOODS: "blue", RAW_MATERIAL: "yellow", TRANSIT: "gray", RETURNS: "red",
  };
  return map[t];
};

const empty: WarehouseCreate = { code: "", name: "", warehouse_type: "FINISHED_GOODS", is_active: true };

export default function WarehousesPage() {
  const qc = useQueryClient();
  const { toasts, toast, dismiss } = useToast();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<WarehouseCreate>(empty);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: warehouses = [], isLoading } = useQuery({
    queryKey: ["warehouses"],
    queryFn: () => warehousesApi.list(0, 200),
  });

  const create = useMutation({
    mutationFn: warehousesApi.create,
    onSuccess: (w) => {
      qc.invalidateQueries({ queryKey: ["warehouses"] });
      setOpen(false);
      setForm(empty);
      toast("success", "Warehouse created", `${w.name} (${w.code}) added.`);
    },
    onError: (err) => toast("error", "Failed to create warehouse", extractApiError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => warehousesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["warehouses"] });
      toast("success", "Warehouse deleted", "Warehouse removed successfully.");
      setDeletingId(null);
    },
    onError: (err) => toast("error", "Failed to delete warehouse", extractApiError(err)),
  });

  const set = (key: keyof WarehouseCreate, value: unknown) => setForm((f) => ({ ...f, [key]: value }));

  const deletingWarehouse = warehouses.find((w) => w.id === deletingId);

  return (
    <div>
      <ToastContainer toasts={toasts} onDismiss={dismiss} />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Warehouses</h1>
          <p className="text-sm text-gray-500 mt-1">{warehouses.length} total</p>
        </div>
        <div className="flex items-center gap-2">
          <ImportModal module="warehouses" onSuccess={() => qc.invalidateQueries({ queryKey: ["warehouses"] })} />
          <Button onClick={() => setOpen(true)}>+ Add Warehouse</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
      ) : (
        <Table
          keyField="id"
          data={warehouses}
          emptyMessage="No warehouses yet. Add your first warehouse."
          columns={[
            { header: "Code", accessor: "code", className: "font-mono text-xs font-medium" },
            { header: "Name", accessor: "name" },
            { header: "Type", accessor: (r) => <Badge label={r.warehouse_type.replace("_", " ")} variant={typeVariant(r.warehouse_type)} /> },
            { header: "City", accessor: (r) => r.city ?? "—" },
            { header: "Country", accessor: (r) => r.country ?? "—" },
            { header: "Capacity (m²)", accessor: (r) => r.capacity_sqm ? Number(r.capacity_sqm).toLocaleString() : "—" },
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

      {/* Add Warehouse Modal */}
      <Modal open={open} onClose={() => { setOpen(false); setForm(empty); }} title="Add Warehouse">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Code *" value={form.code} onChange={(e) => set("code", e.target.value)} required placeholder="WH-01" />
            <Input label="Name *" value={form.name} onChange={(e) => set("name", e.target.value)} required placeholder="Main Warehouse" />
          </div>
          <Select label="Type" options={TYPES} value={form.warehouse_type}
            onChange={(e) => set("warehouse_type", e.target.value as WarehouseType)} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="City" onChange={(e) => set("city", e.target.value)} placeholder="Jakarta" />
            <Input label="Country" onChange={(e) => set("country", e.target.value)} placeholder="Indonesia" />
          </div>
          <Input label="Capacity (m²)" type="number" step="0.01" onChange={(e) => set("capacity_sqm", parseFloat(e.target.value) || undefined)} />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => { setOpen(false); setForm(empty); }}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create Warehouse</Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirm Modal */}
      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title="Delete Warehouse">
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete{" "}
          <span className="font-semibold text-gray-900">{deletingWarehouse?.name}</span>{" "}
          <span className="font-mono text-xs text-gray-500">({deletingWarehouse?.code})</span>?
          This action cannot be undone.
        </p>
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
