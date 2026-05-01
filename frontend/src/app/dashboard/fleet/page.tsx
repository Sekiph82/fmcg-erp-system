"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getDashboard, FleetDashboard, VEHICLE_STATUS_BADGE } from "@/lib/fleet";

export default function FleetDashboardPage() {
  const [data, setData] = useState<FleetDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const navLinks = [
    { href: "/dashboard/fleet/vehicles",    label: "Vehicles",      desc: "Fleet register" },
    { href: "/dashboard/fleet/drivers",     label: "Drivers",       desc: "Driver roster" },
    { href: "/dashboard/fleet/trips",       label: "Trips",         desc: "Trip planning & tracking" },
    { href: "/dashboard/fleet/fuel",        label: "Fuel Log",      desc: "Fuel fill-up records" },
    { href: "/dashboard/fleet/maintenance", label: "Maintenance",   desc: "Service tracker" },
    { href: "/dashboard/fleet/incidents",   label: "Incidents",     desc: "Accident & damage log" },
    { href: "/dashboard/fleet/reports",     label: "Reports & AI",  desc: "Analytics + AI insights" },
  ];

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>;

  const kpis = data ? [
    { label: "Total Vehicles",   value: data.total_vehicles },
    { label: "Active",           value: data.active_vehicles, color: "text-green-700" },
    { label: "In Maintenance",   value: data.in_maintenance, color: "text-amber-600", alert: data.in_maintenance > 0 },
    { label: "Trips Today",      value: data.trips_today },
    { label: "In Progress",      value: data.trips_in_progress, color: "text-blue-700" },
    { label: "Open Incidents",   value: data.open_incidents, color: "text-red-600", alert: data.open_incidents > 0 },
    { label: "Available Drivers", value: data.available_drivers, color: "text-green-700" },
    { label: "Fuel Cost (Mo.)",  value: `KES ${data.fuel_cost_this_month.toLocaleString()}` },
    { label: "Maint. Cost (Mo.)", value: `KES ${data.maintenance_cost_this_month.toLocaleString()}` },
  ] : [];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Fleet Management</h1>
        <p className="text-sm text-gray-500 mt-1">Vehicles, drivers, trips, fuel, and maintenance</p>
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-3">
        {kpis.map((k) => (
          <div key={k.label} className={`bg-white rounded-xl border p-3 ${(k as { alert?: boolean }).alert ? "border-amber-300" : "border-gray-200"}`}>
            <div className={`text-xl font-bold ${(k as { color?: string }).color || "text-gray-900"}`}>{k.value}</div>
            <div className="text-xs text-gray-500 mt-1 leading-tight">{k.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {navLinks.map((l) => (
          <Link key={l.href} href={l.href} className="bg-white border border-gray-200 rounded-xl p-4 hover:border-indigo-300 hover:bg-indigo-50 transition-colors">
            <div className="font-semibold text-gray-900 text-sm">{l.label}</div>
            <div className="text-xs text-gray-500 mt-1">{l.desc}</div>
          </Link>
        ))}
      </div>

      {data && data.upcoming_maintenance.length > 0 && (
        <div className="bg-white rounded-2xl border border-amber-200 p-6">
          <h2 className="text-sm font-semibold text-amber-700 mb-3">Upcoming Maintenance (Next 14 Days)</h2>
          <div className="space-y-2">
            {data.upcoming_maintenance.map((m, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold text-gray-900">{String(m.plate_number)}</span>
                  <span className="capitalize text-gray-600">{String(m.maintenance_type)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">{String(m.next_due_date)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${Number(m.days_until) <= 3 ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>
                    {Number(m.days_until)}d
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data && data.recent_trips.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Recent Trips</h2>
          <div className="space-y-2">
            {data.recent_trips.map((t, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="font-mono text-indigo-700">{String(t.trip_no)}</span>
                <span className="text-gray-500">{String(t.trip_date)}</span>
                <span className="capitalize text-gray-600">{String(t.purpose || "—")}</span>
                <span className={`text-xs px-2 py-0.5 rounded capitalize font-medium bg-gray-100 text-gray-700`}>
                  {String(t.status)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
