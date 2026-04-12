"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { deliveryApi, TripStatus, DeliveryTrip } from "@/lib/delivery";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

const STATUS_COLORS: Record<TripStatus, "green" | "blue" | "yellow" | "gray" | "red"> = {
  PLANNED: "gray",
  LOADING: "yellow",
  IN_TRANSIT: "blue",
  COMPLETED: "green",
  CANCELLED: "red",
};

const STATUS_ICONS: Record<TripStatus, string> = {
  PLANNED: "📋",
  LOADING: "📦",
  IN_TRANSIT: "🚛",
  COMPLETED: "✅",
  CANCELLED: "❌",
};

const ORDER_STATUS_COLOR: Record<string, string> = {
  PENDING: "bg-gray-100 text-gray-600",
  DELIVERED: "bg-green-100 text-green-700",
  PARTIAL: "bg-yellow-100 text-yellow-700",
  FAILED: "bg-red-100 text-red-700",
  RESCHEDULED: "bg-blue-100 text-blue-700",
};

const emptyTrip = {
  trip_no: "", trip_date: new Date().toISOString().split("T")[0],
  vehicle_plate: "", driver_name: "", driver_phone: "", vehicle_type: "MOTORBIKE",
};

export default function DeliveryPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<TripStatus | "ALL">("ALL");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedTrip, setSelectedTrip] = useState<DeliveryTrip | null>(null);
  const [form, setForm] = useState(emptyTrip);

  const { data: trips = [], isLoading } = useQuery({
    queryKey: ["delivery-trips", filter],
    queryFn: () => deliveryApi.listTrips(filter !== "ALL" ? { status: filter } : {}),
  });

  const create = useMutation({
    mutationFn: (data: typeof form) => deliveryApi.createTrip({ ...data, orders: [] }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["delivery-trips"] }); setCreateOpen(false); setForm(emptyTrip); },
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TripStatus }) =>
      deliveryApi.updateTrip(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["delivery-trips"] }),
  });

  const statuses: (TripStatus | "ALL")[] = ["ALL", "PLANNED", "LOADING", "IN_TRANSIT", "COMPLETED", "CANCELLED"];

  const planned = trips.filter((t) => t.status === "PLANNED").length;
  const inTransit = trips.filter((t) => t.status === "IN_TRANSIT").length;
  const today = new Date().toISOString().split("T")[0];
  const todayTrips = trips.filter((t) => t.trip_date === today).length;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Delivery Planning</h1>
          <p className="text-sm text-gray-500 mt-1">Vehicle trips · Route management · Status tracking</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>+ New Trip</Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { label: "Planned", value: planned, color: "text-gray-700" },
          { label: "In Transit", value: inTransit, color: "text-blue-600" },
          { label: "Today's Trips", value: todayTrips, color: "text-indigo-600" },
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
            onClick={() => setFilter(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === s
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {s !== "ALL" && STATUS_ICONS[s]} {s}
          </button>
        ))}
      </div>

      {/* Trip cards */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
        </div>
      ) : trips.length === 0 ? (
        <p className="text-gray-400 text-sm py-8 text-center">No trips found.</p>
      ) : (
        <div className="space-y-3">
          {trips.map((trip) => (
            <div
              key={trip.id}
              className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm cursor-pointer hover:border-indigo-200 transition-colors"
              onClick={() => setSelectedTrip(trip)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="text-2xl">{STATUS_ICONS[trip.status]}</div>
                  <div>
                    <p className="font-semibold text-gray-900">{trip.trip_no}</p>
                    <p className="text-xs text-gray-500">
                      {trip.trip_date} · {trip.driver_name ?? "No driver"} · {trip.vehicle_plate ?? "No plate"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">{trip.order_count} orders</span>
                  <Badge label={trip.status} variant={STATUS_COLORS[trip.status]} />
                </div>
              </div>
              {trip.status === "PLANNED" && (
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="secondary"
                    onClick={(e) => { e.stopPropagation(); updateStatus.mutate({ id: trip.id, status: "LOADING" }); }}
                  >
                    Start Loading
                  </Button>
                </div>
              )}
              {trip.status === "LOADING" && (
                <div className="mt-3">
                  <Button
                    onClick={(e) => { e.stopPropagation(); updateStatus.mutate({ id: trip.id, status: "IN_TRANSIT" }); }}
                  >
                    Dispatch Trip
                  </Button>
                </div>
              )}
              {trip.status === "IN_TRANSIT" && (
                <div className="mt-3">
                  <Button
                    onClick={(e) => { e.stopPropagation(); updateStatus.mutate({ id: trip.id, status: "COMPLETED" }); }}
                  >
                    Mark Completed
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Trip Detail Panel */}
      {selectedTrip && (
        <Modal open={!!selectedTrip} onClose={() => setSelectedTrip(null)} title={`Trip: ${selectedTrip.trip_no}`}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-gray-500">Date:</span> <span className="font-medium">{selectedTrip.trip_date}</span></div>
              <div><span className="text-gray-500">Driver:</span> <span className="font-medium">{selectedTrip.driver_name ?? "—"}</span></div>
              <div><span className="text-gray-500">Vehicle:</span> <span className="font-medium">{selectedTrip.vehicle_plate ?? "—"}</span></div>
              <div><span className="text-gray-500">Phone:</span> <span className="font-medium">{selectedTrip.driver_phone ?? "—"}</span></div>
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-700 mb-2">Delivery Orders ({selectedTrip.orders.length})</p>
              {selectedTrip.orders.length === 0 ? (
                <p className="text-xs text-gray-400">No orders assigned.</p>
              ) : (
                <div className="space-y-1.5">
                  {selectedTrip.orders.map((o) => (
                    <div key={o.id} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-sm">
                      <div>
                        <span className="font-mono text-xs font-medium">{o.shipment_no ?? o.shipment_id.slice(0, 8)}</span>
                        {o.customer_name && <span className="text-gray-500 ml-2">· {o.customer_name}</span>}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">#{o.delivery_sequence}</span>
                        <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${ORDER_STATUS_COLOR[o.status]}`}>
                          {o.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedTrip.route_notes && (
              <div>
                <p className="text-xs text-gray-500 font-medium mb-1">Route Notes</p>
                <p className="text-sm text-gray-700 bg-gray-50 rounded-lg px-3 py-2">{selectedTrip.route_notes}</p>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Create Trip Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New Delivery Trip">
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(form); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Trip No *" value={form.trip_no} onChange={(e) => setForm((f) => ({ ...f, trip_no: e.target.value }))} required />
            <Input label="Date *" type="date" value={form.trip_date} onChange={(e) => setForm((f) => ({ ...f, trip_date: e.target.value }))} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Vehicle Plate" value={form.vehicle_plate} onChange={(e) => setForm((f) => ({ ...f, vehicle_plate: e.target.value }))} />
            <Input label="Vehicle Type" value={form.vehicle_type} onChange={(e) => setForm((f) => ({ ...f, vehicle_type: e.target.value }))} placeholder="MOTORBIKE / VAN / TRUCK" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Driver Name" value={form.driver_name} onChange={(e) => setForm((f) => ({ ...f, driver_name: e.target.value }))} />
            <Input label="Driver Phone" value={form.driver_phone} onChange={(e) => setForm((f) => ({ ...f, driver_phone: e.target.value }))} />
          </div>
          {create.error && <p className="text-sm text-red-600">Failed to create trip.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create Trip</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
