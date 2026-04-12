"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { inventoryApi, MovementType } from "@/lib/inventory";
import { productsApi } from "@/lib/products";
import { warehousesApi } from "@/lib/warehouses";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";

const movementVariant = (t: MovementType): "green" | "red" | "blue" | "yellow" | "gray" => ({
  RECEIPT: "green", ISSUE: "red", TRANSFER: "blue",
  ADJUSTMENT: "yellow", RETURN: "gray", WRITE_OFF: "red",
} as Record<MovementType, "green" | "red" | "blue" | "yellow" | "gray">)[t];

export default function MovementsPage() {
  const [filterProduct, setFilterProduct] = useState("");
  const [filterWarehouse, setFilterWarehouse] = useState("");

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

  return (
    <div>
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
          ]}
        />
      )}
    </div>
  );
}
