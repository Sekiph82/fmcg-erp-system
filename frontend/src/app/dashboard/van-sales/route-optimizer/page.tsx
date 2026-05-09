"use client";
import { useEffect, useState } from "react";

interface Route { id: string; route_name?: string; name?: string; is_active: boolean; }
interface OptimizedStop {
  stop_id: string;
  new_sequence: number;
  original_sequence: number;
  customer_id: string;
  customer_name: string | null;
  lat: number | null;
  lng: number | null;
  google_maps_link: string | null;
}
interface OptimizeResult {
  route_id: string;
  optimized: boolean;
  total_distance_km?: number;
  reason?: string;
  stops_without_gps?: string[];
  sequence: OptimizedStop[];
}
interface ProfitResult {
  route_id: string;
  stop_count: number;
  estimated_distance_km: number;
  fuel_cost_estimate_kes: number;
  fuel_cost_per_km: number;
}

export default function RouteOptimizerPage() {
  const [routes, setRoutes] = useState<Route[]>([]);
  const [selectedRoute, setSelectedRoute] = useState("");
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [profit, setProfit] = useState<ProfitResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [fuelRate, setFuelRate] = useState("15");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/field-sales/routes")
      .then((r) => r.json())
      .then(setRoutes)
      .catch(() => {});
  }, []);

  const optimize = async () => {
    if (!selectedRoute) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setProfit(null);
    setApplied(false);
    try {
      const [optRes, profRes] = await Promise.all([
        fetch(`/api/v1/field-sales/routes/${selectedRoute}/optimize`),
        fetch(`/api/v1/field-sales/routes/${selectedRoute}/profitability?fuel_cost_per_km=${fuelRate}`),
      ]);
      if (!optRes.ok) throw new Error(await optRes.text());
      setResult(await optRes.json());
      if (profRes.ok) setProfit(await profRes.json());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const applyOptimization = async () => {
    if (!result || !result.optimized) return;
    setApplying(true);
    try {
      const stopOrder = result.sequence.map((s) => s.stop_id);
      const r = await fetch(`/api/v1/field-sales/routes/${selectedRoute}/apply-optimization`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(stopOrder),
      });
      if (!r.ok) throw new Error(await r.text());
      setApplied(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setApplying(false);
    }
  };

  const sequenceChanged = result?.sequence.some((s) => s.new_sequence !== s.original_sequence);

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Route Optimizer</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Nearest-neighbor algorithm. Reorders stops to minimize total travel distance using customer GPS.
        </p>
      </div>

      {error && <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">{error}</div>}
      {applied && <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-700">Optimization applied — stop sequences updated in database.</div>}

      {/* Controls */}
      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 block mb-1">Select Route</label>
            <select value={selectedRoute} onChange={(e) => { setSelectedRoute(e.target.value); setResult(null); setProfit(null); setApplied(false); }}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500">
              <option value="">— Select route —</option>
              {routes.map((r) => (
                <option key={r.id} value={r.id}>{r.route_name ?? r.name ?? r.id}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Fuel Cost (KES/km)</label>
            <input type="number" min={1} step={0.5} value={fuelRate} onChange={(e) => setFuelRate(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>
        <button onClick={optimize} disabled={loading || !selectedRoute}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-5 py-2 rounded disabled:opacity-50">
          {loading ? "Optimizing…" : "Run Optimization"}
        </button>
      </div>

      {/* Profitability summary */}
      {profit && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Stops", value: profit.stop_count, color: "text-gray-800" },
            { label: "Est. Distance", value: `${profit.estimated_distance_km} km`, color: "text-blue-600" },
            { label: "Fuel Cost Est.", value: `KES ${profit.fuel_cost_estimate_kes.toLocaleString()}`, color: "text-orange-600" },
            { label: "Per km Rate", value: `KES ${profit.fuel_cost_per_km}`, color: "text-gray-500" },
          ].map((k) => (
            <div key={k.label} className="bg-white border rounded-lg p-3 shadow-sm">
              <p className="text-xs text-gray-500">{k.label}</p>
              <p className={`text-lg font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Optimization result */}
      {result && (
        <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-700">
                Optimized Sequence
                {result.optimized && result.total_distance_km !== undefined && (
                  <span className="ml-2 font-normal text-gray-400">
                    {result.total_distance_km} km total distance
                  </span>
                )}
              </h2>
              {!result.optimized && result.reason && (
                <p className="text-xs text-amber-600 mt-0.5">{result.reason}</p>
              )}
              {result.stops_without_gps && result.stops_without_gps.length > 0 && (
                <p className="text-xs text-gray-400 mt-0.5">
                  {result.stops_without_gps.length} stops without GPS — placed at end
                </p>
              )}
            </div>
            {result.optimized && sequenceChanged && !applied && (
              <button onClick={applyOptimization} disabled={applying}
                className="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded disabled:opacity-50">
                {applying ? "Applying…" : "Apply to Route"}
              </button>
            )}
            {(!sequenceChanged && result.optimized) && (
              <span className="text-xs text-green-600 bg-green-50 border border-green-200 rounded px-3 py-1">Route already optimal</span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">New #</th>
                  <th className="text-left px-4 py-2">Customer</th>
                  <th className="text-left px-4 py-2">Original #</th>
                  <th className="text-left px-4 py-2">GPS</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {result.sequence.map((s) => {
                  const moved = s.new_sequence !== s.original_sequence;
                  return (
                    <tr key={s.stop_id} className={moved ? "bg-blue-50" : ""}>
                      <td className="px-4 py-2.5">
                        <span className={`font-bold text-sm ${moved ? "text-blue-700" : "text-gray-700"}`}>
                          #{s.new_sequence}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 font-medium text-gray-900">
                        {s.customer_name || `Customer ${s.customer_id.slice(0, 8)}`}
                      </td>
                      <td className="px-4 py-2.5 text-gray-400 text-xs">
                        {moved ? <span className="line-through">#{s.original_sequence}</span> : `#${s.original_sequence}`}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-gray-400">
                        {s.lat !== null ? `${s.lat?.toFixed(4)}, ${s.lng?.toFixed(4)}` : "No GPS"}
                      </td>
                      <td className="px-4 py-2.5">
                        {s.google_maps_link && (
                          <a href={s.google_maps_link} target="_blank" rel="noopener noreferrer"
                            className="text-xs text-blue-500 hover:text-blue-700">Map ↗</a>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
        <p className="font-semibold mb-1">Algorithm: Nearest Neighbor</p>
        <p className="text-xs">
          Starts from the first stop and greedily picks the closest unvisited stop using Haversine distance.
          Stops without GPS coordinates are appended at the end. For best results, ensure customer GPS
          coordinates are populated in the Customers master data.
        </p>
      </div>
    </div>
  );
}
