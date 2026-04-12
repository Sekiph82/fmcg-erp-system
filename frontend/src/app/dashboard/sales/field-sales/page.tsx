"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fieldSalesApi, SalesRep, SalesRoute, VehicleType } from "@/lib/field_sales";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

type Tab = "reps" | "routes" | "visits" | "targets";

const VEHICLE_ICONS: Record<VehicleType, string> = {
  MOTORBIKE: "🏍️",
  VAN: "🚐",
  TRUCK: "🚛",
  FOOT: "🚶",
  OTHER: "🚗",
};

export default function FieldSalesPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("reps");
  const [repOpen, setRepOpen] = useState(false);
  const [routeOpen, setRouteOpen] = useState(false);
  const [repForm, setRepForm] = useState({ code: "", name: "", phone: "", region: "", vehicle_type: "MOTORBIKE" as VehicleType });
  const [routeForm, setRouteForm] = useState({ code: "", name: "", region: "", description: "" });

  const today = new Date().toISOString().split("T")[0];

  const { data: reps = [], isLoading: repsLoading } = useQuery({
    queryKey: ["sales-reps"],
    queryFn: () => fieldSalesApi.listReps(),
  });

  const { data: routes = [], isLoading: routesLoading } = useQuery({
    queryKey: ["sales-routes"],
    queryFn: () => fieldSalesApi.listRoutes(),
  });

  const { data: visits = [], isLoading: visitsLoading } = useQuery({
    queryKey: ["visits-today"],
    queryFn: () => fieldSalesApi.listVisits({ visit_date: today }),
  });

  const { data: targets = [] } = useQuery({
    queryKey: ["targets-today"],
    queryFn: () => fieldSalesApi.listTargets({ from_date: today, to_date: today }),
  });

  const createRep = useMutation({
    mutationFn: fieldSalesApi.createRep,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-reps"] }); setRepOpen(false); },
  });

  const createRoute = useMutation({
    mutationFn: (data: typeof routeForm) => fieldSalesApi.createRoute({ ...data, stops: [] }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sales-routes"] }); setRouteOpen(false); },
  });

  const tabs: { id: Tab; label: string }[] = [
    { id: "reps", label: "Sales Reps" },
    { id: "routes", label: "Routes" },
    { id: "visits", label: "Today's Visits" },
    { id: "targets", label: "Targets" },
  ];

  const outcomeColor: Record<string, string> = {
    ORDERED: "bg-green-100 text-green-700",
    NO_ORDER: "bg-gray-100 text-gray-600",
    CUSTOMER_CLOSED: "bg-red-100 text-red-700",
    CREDIT_HOLD: "bg-yellow-100 text-yellow-700",
    NOT_FOUND: "bg-orange-100 text-orange-700",
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Field Sales</h1>
          <p className="text-sm text-gray-500 mt-1">Motorbike reps · Routes · Daily tracking</p>
        </div>
        <div className="flex gap-2">
          {tab === "reps" && <Button onClick={() => setRepOpen(true)}>+ Add Rep</Button>}
          {tab === "routes" && <Button onClick={() => setRouteOpen(true)}>+ Add Route</Button>}
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: "Active Reps", value: reps.filter((r) => r.is_active).length, icon: "🏍️" },
          { label: "Active Routes", value: routes.filter((r) => r.is_active).length, icon: "🗺️" },
          { label: "Visits Today", value: visits.length, icon: "📍" },
          { label: "Orders Today", value: visits.filter((v) => v.outcome === "ORDERED").length, icon: "📋" },
        ].map((kpi) => (
          <div key={kpi.label} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">{kpi.icon}</span>
              <span className="text-2xl font-bold text-gray-900">{kpi.value}</span>
            </div>
            <p className="text-xs text-gray-500">{kpi.label}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-5">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Reps Tab */}
      {tab === "reps" && (
        repsLoading ? <Spinner /> :
        <Table
          keyField="id"
          data={reps}
          columns={[
            { header: "Code", accessor: "code", className: "font-mono text-xs" },
            { header: "Name", accessor: (r) => (
              <span>{VEHICLE_ICONS[r.vehicle_type]} {r.name}</span>
            )},
            { header: "Phone", accessor: (r) => r.phone ?? "—" },
            { header: "Region", accessor: (r) => r.region ?? "—" },
            { header: "Vehicle", accessor: "vehicle_type" },
            { header: "Status", accessor: (r) => (
              <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "red"} />
            )},
          ]}
        />
      )}

      {/* Routes Tab */}
      {tab === "routes" && (
        routesLoading ? <Spinner /> :
        <Table
          keyField="id"
          data={routes}
          columns={[
            { header: "Code", accessor: "code", className: "font-mono text-xs" },
            { header: "Name", accessor: "name" },
            { header: "Region", accessor: (r) => r.region ?? "—" },
            { header: "Assigned Rep", accessor: (r) => r.rep_name ?? "—" },
            { header: "Stops", accessor: (r) => `${r.stop_count} customers` },
            { header: "Status", accessor: (r) => (
              <Badge label={r.is_active ? "Active" : "Inactive"} variant={r.is_active ? "green" : "red"} />
            )},
          ]}
        />
      )}

      {/* Visits Tab */}
      {tab === "visits" && (
        visitsLoading ? <Spinner /> :
        visits.length === 0 ? (
          <p className="text-gray-400 text-sm py-8 text-center">No visits recorded today.</p>
        ) : (
          <div className="space-y-2">
            {visits.map((v) => (
              <div key={v.id} className="flex items-center justify-between rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-indigo-50 flex items-center justify-center text-xs font-bold text-indigo-600">
                    {v.rep_name?.charAt(0) ?? "?"}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-800">{v.customer_name}</p>
                    <p className="text-xs text-gray-400">{v.rep_name} · {v.visited_at ? new Date(v.visited_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {v.gps_lat && <span className="text-xs text-gray-400">📍 GPS</span>}
                  <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${outcomeColor[v.outcome] ?? "bg-gray-100 text-gray-600"}`}>
                    {v.outcome.replace("_", " ")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {/* Targets Tab */}
      {tab === "targets" && (
        targets.length === 0 ? (
          <p className="text-gray-400 text-sm py-8 text-center">No targets set for today.</p>
        ) : (
          <div className="space-y-3">
            {targets.map((t) => {
              const pct = t.target_amount > 0
                ? Math.min(((t.actual_amount ?? 0) / t.target_amount) * 100, 100)
                : 0;
              return (
                <div key={t.id} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="font-medium text-gray-800">{t.rep_name}</p>
                      <p className="text-xs text-gray-400">{t.route_name ?? "No route"}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-gray-900">
                        {t.currency} {(t.actual_amount ?? 0).toLocaleString()} / {t.target_amount.toLocaleString()}
                      </p>
                      <p className="text-xs text-gray-400">{pct.toFixed(0)}% achieved</p>
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-gray-100">
                    <div
                      className={`h-2 rounded-full transition-all ${pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-400" : "bg-red-400"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )
      )}

      {/* Add Rep Modal */}
      <Modal open={repOpen} onClose={() => setRepOpen(false)} title="Add Sales Rep">
        <form onSubmit={(e) => { e.preventDefault(); createRep.mutate(repForm); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Code *" value={repForm.code} onChange={(e) => setRepForm((f) => ({ ...f, code: e.target.value }))} required />
            <Input label="Name *" value={repForm.name} onChange={(e) => setRepForm((f) => ({ ...f, name: e.target.value }))} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input label="Phone" value={repForm.phone} onChange={(e) => setRepForm((f) => ({ ...f, phone: e.target.value }))} />
            <Input label="Region" value={repForm.region} onChange={(e) => setRepForm((f) => ({ ...f, region: e.target.value }))} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Vehicle Type</label>
            <select
              value={repForm.vehicle_type}
              onChange={(e) => setRepForm((f) => ({ ...f, vehicle_type: e.target.value as VehicleType }))}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {Object.keys(VEHICLE_ICONS).map((v) => (
                <option key={v} value={v}>{VEHICLE_ICONS[v as VehicleType]} {v}</option>
              ))}
            </select>
          </div>
          {createRep.error && <p className="text-sm text-red-600">Failed to create rep.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setRepOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createRep.isPending}>Create</Button>
          </div>
        </form>
      </Modal>

      {/* Add Route Modal */}
      <Modal open={routeOpen} onClose={() => setRouteOpen(false)} title="Add Sales Route">
        <form onSubmit={(e) => { e.preventDefault(); createRoute.mutate(routeForm); }} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Code *" value={routeForm.code} onChange={(e) => setRouteForm((f) => ({ ...f, code: e.target.value }))} required />
            <Input label="Name *" value={routeForm.name} onChange={(e) => setRouteForm((f) => ({ ...f, name: e.target.value }))} required />
          </div>
          <Input label="Region" value={routeForm.region} onChange={(e) => setRouteForm((f) => ({ ...f, region: e.target.value }))} placeholder="e.g. Nairobi West" />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={routeForm.description}
              onChange={(e) => setRouteForm((f) => ({ ...f, description: e.target.value }))}
              rows={2}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {createRoute.error && <p className="text-sm text-red-600">Failed to create route.</p>}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" type="button" onClick={() => setRouteOpen(false)}>Cancel</Button>
            <Button type="submit" loading={createRoute.isPending}>Create</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex justify-center py-12">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
    </div>
  );
}
