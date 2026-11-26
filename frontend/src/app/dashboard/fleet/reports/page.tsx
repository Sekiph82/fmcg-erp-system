"use client";

import { useState } from "react";
import { getUtilizationReport, getFuelReport, getMaintenanceReport, getDriverReport, getRouteEfficiency, getFuelAnomaly, getMaintenancePredictor } from "@/lib/fleet";
import { Button } from "@/components/ui/Button";
import { tx } from "@/lib/i18n/core";

export default function FleetReportsPage() {
  const [days, setDays] = useState(30);
  const [utilization, setUtilization] = useState<unknown[]>([]);
  const [fuel, setFuel] = useState<unknown[]>([]);
  const [maintenance, setMaintenance] = useState<unknown[]>([]);
  const [driverRep, setDriverRep] = useState<unknown[]>([]);
  const [ai1, setAi1] = useState<unknown>(null);
  const [ai2, setAi2] = useState<unknown>(null);
  const [ai3, setAi3] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function loadAll() {
    setLoading(true);
    try {
      const [u, f, m, d, a1, a2, a3] = await Promise.all([
        getUtilizationReport(days),
        getFuelReport(days),
        getMaintenanceReport(days),
        getDriverReport(days),
        getRouteEfficiency(),
        getFuelAnomaly(),
        getMaintenancePredictor(),
      ]);
      setUtilization(u); setFuel(f); setMaintenance(m); setDriverRep(d);
      setAi1(a1); setAi2(a2); setAi3(a3);
    } catch {}
    setLoading(false);
  }

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-3">
      <h2 className="font-semibold text-gray-900">{title}</h2>
      {children}
    </div>
  );

  const Table = ({ data, cols }: { data: unknown[]; cols: { key: string; label: string }[] }) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>{cols.map((c) => <th key={c.key} className="text-left px-3 py-2 font-medium text-gray-700">{c.label}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {cols.map((c) => (
                <td key={c.key} className="px-3 py-2 text-gray-700">
                  {String((row as Record<string, unknown>)[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
          {data.length === 0 && <tr><td colSpan={cols.length} className="px-3 py-6 text-center text-gray-400">{tx("No data")}</td></tr>}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{tx("Fleet Reports & AI")}</h1>
          <p className="text-sm text-gray-500 mt-1">{tx("Utilization, fuel, maintenance, and AI insights")}</p>
        </div>
        <div className="flex items-center gap-3">
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>{tx("Last 7 days")}</option>
            <option value={30}>{tx("Last 30 days")}</option>
            <option value={90}>{tx("Last 90 days")}</option>
          </select>
          <Button onClick={loadAll} loading={loading}>{tx("Load Reports")}</Button>
        </div>
      </div>

      {utilization.length > 0 && (
        <Section title={tx("Fleet Utilization")}>
          <Table data={utilization} cols={[
            { key: "vehicle_code", label: tx("Code") },
            { key: "plate_number", label: tx("Plate") },
            { key: "vehicle_type", label: tx("Type") },
            { key: "trip_count", label: tx("Trips") },
            { key: "total_km", label: tx("Total km") },
            { key: "total_cost", label: tx("Cost (KES)") },
            { key: "utilization_pct", label: tx("Util %") },
          ]} />
        </Section>
      )}

      {fuel.length > 0 && (
        <Section title={tx("Fuel Consumption")}>
          <Table data={fuel} cols={[
            { key: "vehicle_code", label: tx("Code") },
            { key: "plate_number", label: tx("Plate") },
            { key: "total_liters", label: tx("Total L") },
            { key: "total_fuel_cost", label: tx("Cost (KES)") },
            { key: "avg_cost_per_liter", label: tx("Avg KES/L") },
          ]} />
        </Section>
      )}

      {maintenance.length > 0 && (
        <Section title={tx("Maintenance Costs")}>
          <Table data={maintenance} cols={[
            { key: "vehicle_code", label: tx("Code") },
            { key: "plate_number", label: tx("Plate") },
            { key: "maintenance_type", label: tx("Type") },
            { key: "count", label: tx("Count") },
            { key: "total_cost", label: tx("Cost (KES)") },
            { key: "total_downtime_days", label: tx("Downtime (d)") },
          ]} />
        </Section>
      )}

      {driverRep.length > 0 && (
        <Section title={tx("Driver Performance")}>
          <Table data={driverRep} cols={[
            { key: "driver_code", label: tx("Code") },
            { key: "full_name", label: tx("Name") },
            { key: "trip_count", label: tx("Trips") },
            { key: "total_km", label: tx("Total km") },
          ]} />
        </Section>
      )}

      {!!ai1 && (
        <Section title={tx("AI: Route Efficiency Optimizer")}>
          <pre className="text-xs bg-gray-900 text-green-300 rounded-lg p-4 overflow-auto max-h-64">{JSON.stringify(ai1, null, 2)}</pre>
        </Section>
      )}
      {!!ai2 && (
        <Section title={tx("AI: Fuel Anomaly Detector")}>
          <pre className="text-xs bg-gray-900 text-amber-300 rounded-lg p-4 overflow-auto max-h-64">{JSON.stringify(ai2, null, 2)}</pre>
        </Section>
      )}
      {!!ai3 && (
        <Section title={tx("AI: Maintenance Predictor")}>
          <pre className="text-xs bg-gray-900 text-blue-300 rounded-lg p-4 overflow-auto max-h-64">{JSON.stringify(ai3, null, 2)}</pre>
        </Section>
      )}

      {!utilization.length && !loading && (
        <div className="text-center py-16 text-gray-400">Click &ldquo;Load Reports&rdquo; to fetch data and AI insights.</div>
      )}
    </div>
  );
}
