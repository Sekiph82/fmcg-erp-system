"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { procurementApi } from "@/lib/procurement";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function DeliveryPlanningPage() {
  const router = useRouter();
  const [daysAhead, setDaysAhead] = useState("30");

  const { data: schedule = [], isFetching: loadingSchedule } = useQuery({
    queryKey: ["inbound-schedule", daysAhead],
    queryFn: () => procurementApi.inboundSchedule(Number(daysAhead) || 30),
  });

  const { data: alerts = [], isFetching: loadingAlerts } = useQuery({
    queryKey: ["delivery-alerts"],
    queryFn: () => procurementApi.deliveryAlerts(),
  });

  const overdue = schedule.filter((r) => r.is_overdue);
  const upcoming = schedule.filter((r) => !r.is_overdue);

  const alertVariant = (type: string) =>
    type === "OVERDUE" ? "red" : type === "APPROACHING" ? "blue" : "blue";

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Delivery Planning</h1>
        <p className="text-sm text-gray-500 mt-1">Inbound schedule, overdue POs, and shortage alerts</p>
      </div>

      {/* Alert bar */}
      {alerts.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800 mb-2">{alerts.length} delivery alert(s)</p>
          <div className="space-y-1.5">
            {alerts.map((a, i) => (
              <div key={i} className="flex items-center gap-3">
                <Badge
                  label={a.alert_type.replace(/_/g, " ")}
                  variant={alertVariant(a.alert_type)}
                />
                <span className="text-xs text-amber-700">{a.message}</span>
                <button
                  className="ml-auto text-xs text-indigo-600 hover:underline"
                  onClick={() => router.push(`/dashboard/procurement/orders/${a.po_id}`)}
                >
                  View PO
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Overdue POs</p>
          <p className={`text-2xl font-bold ${overdue.length > 0 ? "text-red-600" : "text-gray-400"}`}>{overdue.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Expected (next {daysAhead}d)</p>
          <p className="text-2xl font-bold text-gray-900">{upcoming.length}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-gray-500">Without Shipment</p>
          <p className={`text-2xl font-bold ${schedule.filter((r) => !r.has_shipment).length > 0 ? "text-amber-600" : "text-gray-400"}`}>
            {schedule.filter((r) => !r.has_shipment).length}
          </p>
        </div>
      </div>

      {/* Schedule */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Inbound Schedule</h2>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Days ahead:</span>
            <Input
              type="number"
              value={daysAhead}
              onChange={(e) => setDaysAhead(e.target.value)}
              className="w-20"
            />
          </div>
        </div>

        {loadingSchedule ? (
          <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" /></div>
        ) : (
          <Table
            keyField="po_id"
            data={schedule}
            emptyMessage="No active POs due within this period."
            columns={[
              {
                header: "PO No",
                accessor: (r) => (
                  <button className="font-mono text-xs font-medium text-indigo-600 hover:underline" onClick={() => router.push(`/dashboard/procurement/orders/${r.po_id}`)}>
                    {r.po_no}
                  </button>
                ),
              },
              { header: "Supplier", accessor: "supplier_name" },
              {
                header: "Expected Delivery",
                accessor: (r) => (
                  <span className={r.is_overdue ? "text-red-600 font-semibold" : r.days_until_delivery <= 7 ? "text-amber-600" : ""}>
                    {new Date(r.expected_delivery_date).toLocaleDateString()}
                    <span className="ml-1 text-xs text-gray-400">
                      {r.is_overdue ? `(${Math.abs(r.days_until_delivery)}d overdue)` : `(in ${r.days_until_delivery}d)`}
                    </span>
                  </span>
                ),
              },
              {
                header: "Status",
                accessor: (r) => (
                  <div className="flex items-center gap-2">
                    <Badge label={r.status.replace(/_/g, " ")} variant={r.is_overdue ? "red" : "blue"} />
                    {r.is_overdue && <Badge label="OVERDUE" variant="red" />}
                  </div>
                ),
              },
              {
                header: "Shipment",
                accessor: (r) => r.has_shipment
                  ? <span className="text-green-600 text-xs font-medium">{r.shipment_eta ? `ETA ${new Date(r.shipment_eta).toLocaleDateString()}` : "Linked"}</span>
                  : <span className="text-amber-600 text-xs">No shipment</span>,
              },
              {
                header: "Value",
                accessor: (r) => r.total_value != null
                  ? Number(r.total_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                  : "—",
              },
              {
                header: "",
                accessor: (r) => <Button variant="secondary" onClick={() => router.push(`/dashboard/procurement/orders/${r.po_id}`)}>View</Button>,
              },
            ]}
          />
        )}
      </div>
    </div>
  );
}
