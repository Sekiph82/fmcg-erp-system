"use client";

import { useCallback, useEffect, useState } from "react";
import { esgApi, ESGDashboard, EmissionSummary, ESGInsight } from "@/lib/esg";
import Link from "next/link";

const SCOPE_COLORS: Record<string, string> = {
  SCOPE1: "bg-red-100 text-red-700",
  SCOPE2: "bg-orange-100 text-orange-700",
  SCOPE3: "bg-yellow-100 text-yellow-700",
};

const SCOPE_LABELS: Record<string, string> = {
  SCOPE1: "Scope 1 (Direct)",
  SCOPE2: "Scope 2 (Electricity)",
  SCOPE3: "Scope 3 (Value Chain)",
};

export default function ESGDashboardPage() {
  const [dashboard, setDashboard] = useState<ESGDashboard | null>(null);
  const [summary, setSummary] = useState<EmissionSummary[]>([]);
  const [insights, setInsights] = useState<ESGInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const [importMsg, setImportMsg] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { date_from: dateFrom || undefined, date_to: dateTo || undefined };
      const [dash, sum] = await Promise.all([
        esgApi.getDashboard(params),
        esgApi.emissionSummary(params),
      ]);
      setDashboard(dash);
      setSummary(sum);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  const runAI = async () => {
    setAiLoading(true);
    try {
      const params = { date_from: dateFrom || undefined, date_to: dateTo || undefined };
      const [hotspot, reduction, quality] = await Promise.all([
        esgApi.aiHotspot(params),
        esgApi.aiReduction(params),
        esgApi.aiDataQuality(params),
      ]);
      setInsights([hotspot, reduction, quality]);
    } finally {
      setAiLoading(false);
    }
  };

  const handleImportFleet = async () => {
    setImportLoading(true);
    try {
      const result = await esgApi.importFleet();
      setImportMsg(result.message);
      load();
    } finally {
      setImportLoading(false);
    }
  };

  const handleSeedFactors = async () => {
    const result = await esgApi.seedFactors();
    alert(result.message);
  };

  const fmt = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 1 });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ESG Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Environmental · Social · Governance reporting</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link href="/dashboard/esg/activities" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
            Activities
          </Link>
          <Link href="/dashboard/esg/factors" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
            Emission Factors
          </Link>
          <Link href="/dashboard/esg/targets" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
            Targets
          </Link>
          <Link href="/dashboard/esg/reports" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
            Reports
          </Link>
          <Link href="/dashboard/esg/intelligence" className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50">
            Intelligence
          </Link>
          <button
            onClick={handleSeedFactors}
            className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg"
          >
            Seed Default Factors
          </button>
          <button
            onClick={handleImportFleet}
            disabled={importLoading}
            className="px-3 py-2 text-sm bg-green-100 text-green-700 hover:bg-green-200 rounded-lg disabled:opacity-50"
          >
            {importLoading ? "Importing…" : "Import Fleet Fuel"}
          </button>
        </div>
      </div>

      {importMsg && (
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2 text-sm text-green-700">
          {importMsg}
        </div>
      )}

      {/* Date filters */}
      <div className="flex gap-3 items-end flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">From</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">To</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border rounded-lg px-3 py-2 text-sm" />
        </div>
        <button
          onClick={runAI}
          disabled={aiLoading}
          className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          {aiLoading ? "Analyzing…" : "Run AI Analysis"}
        </button>
      </div>

      {/* Emission KPIs */}
      {dashboard && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total Emissions", value: `${fmt(dashboard.total_emissions_kgco2e)} kg`, sub: `${(dashboard.total_emissions_kgco2e / 1000).toFixed(2)} tCO₂e`, color: "text-red-600" },
              { label: "Scope 1 (Direct)", value: `${fmt(dashboard.scope1_kgco2e)} kg`, sub: "Direct combustion", color: "text-red-500" },
              { label: "Scope 2 (Electricity)", value: `${fmt(dashboard.scope2_kgco2e)} kg`, sub: "Grid & generation", color: "text-orange-500" },
              { label: "Scope 3 (Value Chain)", value: `${fmt(dashboard.scope3_kgco2e)} kg`, sub: "Upstream/downstream", color: "text-yellow-600" },
            ].map((k) => (
              <div key={k.label} className="bg-white rounded-lg border p-4">
                <p className="text-xs text-gray-500">{k.label}</p>
                <p className={`text-xl font-bold mt-1 ${k.color}`}>{k.value}</p>
                <p className="text-xs text-gray-400 mt-0.5">{k.sub}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Total Energy", value: `${fmt(dashboard.total_energy_kwh)} kWh`, color: "text-blue-600" },
              { label: "Total Water", value: `${fmt(dashboard.total_water_m3)} m³`, color: "text-cyan-600" },
              { label: "Total Waste", value: `${fmt(dashboard.total_waste_kg)} kg`, color: "text-gray-600" },
            ].map((k) => (
              <div key={k.label} className="bg-white rounded-lg border p-4">
                <p className="text-xs text-gray-500">{k.label}</p>
                <p className={`text-xl font-bold mt-1 ${k.color}`}>{k.value}</p>
              </div>
            ))}
          </div>

          {/* Recycling rate */}
          {dashboard.recycling_rate_pct != null && (
            <div className="bg-white rounded-lg border p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">Recycling Rate</span>
                <span className="text-lg font-bold text-green-600">{Number(dashboard.recycling_rate_pct).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${Math.min(Number(dashboard.recycling_rate_pct), 100)}%` }}
                />
              </div>
            </div>
          )}
        </>
      )}

      {/* Scope breakdown table */}
      {summary.length > 0 && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h2 className="font-semibold text-gray-800">Emissions by Scope</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Scope</th>
                <th className="px-4 py-3 text-right">kgCO₂e</th>
                <th className="px-4 py-3 text-right">tCO₂e</th>
                <th className="px-4 py-3 text-right">Activities</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {summary.map((row) => (
                <tr key={row.scope} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SCOPE_COLORS[row.scope]}`}>
                      {SCOPE_LABELS[row.scope]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">{fmt(Number(row.total_kgco2e))}</td>
                  <td className="px-4 py-3 text-right">{Number(row.total_tco2e).toFixed(3)}</td>
                  <td className="px-4 py-3 text-right text-gray-500">{row.activity_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* AI Insights */}
      {insights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {insights.map((insight, i) => (
            <div key={i} className={`rounded-lg border p-4 ${i === 0 ? "bg-red-50 border-red-200" : i === 1 ? "bg-green-50 border-green-200" : "bg-blue-50 border-blue-200"}`}>
              <h3 className={`text-sm font-semibold mb-2 ${i === 0 ? "text-red-800" : i === 1 ? "text-green-800" : "text-blue-800"}`}>
                {insight.agent}
              </h3>
              <ul className="space-y-1">
                {insight.insights.slice(0, 4).map((ins, j) => (
                  <li key={j} className={`text-xs ${i === 0 ? "text-red-700" : i === 1 ? "text-green-700" : "text-blue-700"}`}>
                    • {ins}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
