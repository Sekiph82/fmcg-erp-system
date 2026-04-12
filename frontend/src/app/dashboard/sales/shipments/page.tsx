"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { salesApi, ShipmentStatus } from "@/lib/sales";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";

const statusVariant = (s: ShipmentStatus) =>
  s === "DISPATCHED" || s === "DELIVERED" ? "green"
  : s === "PACKED" ? "blue"
  : s === "PICKING" ? "yellow"
  : s === "CANCELLED" ? "red"
  : "blue";

const STATUS_OPTS = [
  { value: "", label: "All" },
  { value: "PENDING", label: "Pending" },
  { value: "PICKING", label: "Picking" },
  { value: "PACKED", label: "Packed" },
  { value: "DISPATCHED", label: "Dispatched" },
  { value: "DELIVERED", label: "Delivered" },
  { value: "CANCELLED", label: "Cancelled" },
];

export default function ShipmentsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");

  const { data: shipments = [], isLoading } = useQuery({
    queryKey: ["sales-shipments", statusFilter],
    queryFn: () => salesApi.listShipments(statusFilter ? { status: statusFilter as ShipmentStatus } : {}),
  });

  const columns = [
    { header: "Shipment No", accessor: (r: typeof shipments[0]) => (
      <button onClick={() => router.push(`/dashboard/sales/shipments/${r.id}`)} className="text-blue-600 hover:underline font-medium">
        {r.shipment_no}
      </button>
    )},
    { header: "Sales Order", accessor: (r: typeof shipments[0]) => r.so_no || "—" },
    { header: "Customer", accessor: (r: typeof shipments[0]) => r.customer_name || "—" },
    { header: "Warehouse", accessor: (r: typeof shipments[0]) => r.warehouse_name || "—" },
    { header: "Scheduled", accessor: (r: typeof shipments[0]) => r.scheduled_date },
    { header: "Dispatched", accessor: (r: typeof shipments[0]) => r.dispatched_date || "—" },
    { header: "Picked", accessor: (r: typeof shipments[0]) => `${r.picked_count}/${r.line_count}` },
    { header: "Status", accessor: (r: typeof shipments[0]) => (
      <Badge label={r.status} variant={statusVariant(r.status)} />
    )},
    { header: "Carrier", accessor: (r: typeof shipments[0]) => r.carrier || "—" },
  ];

  // Stats
  const pending = shipments.filter((s) => s.status === "PENDING").length;
  const picking = shipments.filter((s) => s.status === "PICKING" || s.status === "PACKED").length;
  const dispatched = shipments.filter((s) => s.status === "DISPATCHED").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Shipments</h1>
          <p className="text-sm text-gray-500 mt-1">{shipments.length} shipments</p>
        </div>
        <Select options={STATUS_OPTS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Pending", value: pending, color: "text-gray-700" },
          { label: "In Progress (Picking/Packed)", value: picking, color: "text-yellow-700" },
          { label: "Dispatched", value: dispatched, color: "text-green-700" },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{stat.label}</p>
            <p className={`text-3xl font-bold mt-1 ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : (
        <Table columns={columns} data={shipments} keyField="id" emptyMessage="No shipments found." />
      )}
    </div>
  );
}
