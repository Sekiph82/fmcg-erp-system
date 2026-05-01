"use client";

import { useState, useEffect } from "react";
import { esgApi, EmissionSummary, EmissionBySource, ResourceSummary, SOURCE_TYPE_LABELS } from "@/lib/esg";

const SCOPE_COLORS: Record<string, string> = {
  SCOPE1: "bg-red-50 border-red-200 text-red-700",
  SCOPE2: "bg-orange-50 border-orange-200 text-orange-700",
  SCOPE3: "bg-yellow-50 border-yellow-200 text-yellow-700",
};

export default function ESGReportsPage() {
  const [summary, setSummary] = useState<EmissionSummary[]>([]);
  const [bySource, setBySource] = useState<EmissionBySource[]>([]);
  const [resources, setResources] = useState<ResourceSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [tab, setTab] = useState<"scope" | "source" | "resources">("scope");

  const load = async () => {
    setLoading(true);
    try {
      const params = { date_from: dateFrom || undefined, date_to: dateTo || undefined };
      const [s, bs, r] = await Promise.all([
        esgApi.emissionSummary(params),
        esgApi.emissionBySource(params),
        esgApi.resourceSummary(params),
      ]);
      setSummary(s);
      setBySource(bs);
      setResources(r);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [dateFrom, dateTo]);

  const totalKg = summary.reduce((s, r) => s + Number(r.total_kgco2e), 0);

  const exportCSV = (data: any[], filename: string) => {
    if (!data.length) return;
    const keys = Object.keys(data[0]);
    const csv = [keys.join(","), ...data.map((row) => keys.map((k) => row[k]).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ESG Reports</h1>
          <p className="text-sm text-gray-500 mt-1">GHG Protocol aligned reporting · Scope 1, 2, 3</p>
        </div>
      </div>

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
        <button onClick={load} disabled={loading} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {/* Summary cards */}
      {summary.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {summary.map((s) => (
            <div key={s.scope} className={`rounded-lg border p-4 ${SCOPE_COLORS[s.scope]}`}>
              <p className="text-xs font-semibold mb-1">{s.scope}</p>
              <p className="text-2xl font-bold">{Number(s.total_kgco2e).toLocaleString(undefined, { maximumFractionDigits: 0 })} kg</p>
              <p className="text-xs mt-1">{Number(s.total_tco2e).toFixed(3)} tCO₂e · {s.activity_count} activities</p>
              <p className="text-xs mt-0.5">{totalKg > 0 ? ((Number(s.total_kgco2e) / totalKg) * 100).toFixed(1) : 0}% of total</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b flex gap-4">
        {(["scope", "source", "resources"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`pb-2 text-sm font-medium capitalize border-b-2 -mb-px ${tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t === "scope" ? "By Scope" : t === "source" ? "By Source" : "Energy/Water/Waste"}
          </button>
        ))}
      </div>

      {/* By Scope */}
      {tab === "scope" && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <div className="flex justify-end px-4 py-2 border-b">
            <button onClick={() => exportCSV(summary, "esg-scope-report")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Scope</th>
                <th className="px-4 py-3 text-right">kgCO₂e</th>
                <th className="px-4 py-3 text-right">tCO₂e</th>
                <th className="px-4 py-3 text-right">Activities</th>
                <th className="px-4 py-3 text-right">% of Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {summary.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No emission records yet</td></tr>
              ) : (
                summary.map((r) => (
                  <tr key={r.scope} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-semibold">{r.scope}</td>
                    <td className="px-4 py-2 text-right">{Number(r.total_kgco2e).toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                    <td className="px-4 py-2 text-right">{Number(r.total_tco2e).toFixed(3)}</td>
                    <td className="px-4 py-2 text-right">{r.activity_count}</td>
                    <td className="px-4 py-2 text-right">{totalKg > 0 ? ((Number(r.total_kgco2e) / totalKg) * 100).toFixed(1) : 0}%</td>
                  </tr>
                ))
              )}
              {summary.length > 0 && (
                <tr className="bg-gray-50 font-semibold">
                  <td className="px-4 py-2">TOTAL</td>
                  <td className="px-4 py-2 text-right">{totalKg.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                  <td className="px-4 py-2 text-right">{(totalKg / 1000).toFixed(3)}</td>
                  <td className="px-4 py-2 text-right">{summary.reduce((s, r) => s + r.activity_count, 0)}</td>
                  <td className="px-4 py-2 text-right">100%</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* By Source */}
      {tab === "source" && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <div className="flex justify-end px-4 py-2 border-b">
            <button onClick={() => exportCSV(bySource, "esg-source-report")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Source Type</th>
                <th className="px-4 py-3 text-left">Scope</th>
                <th className="px-4 py-3 text-right">kgCO₂e</th>
                <th className="px-4 py-3 text-right">Activities</th>
                <th className="px-4 py-3 text-right">% of Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {bySource.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No data</td></tr>
              ) : (
                bySource.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2">{SOURCE_TYPE_LABELS[r.source_type] || r.source_type}</td>
                    <td className="px-4 py-2 text-xs">
                      <span className={`px-2 py-0.5 rounded-full ${r.scope === "SCOPE1" ? "bg-red-100 text-red-700" : r.scope === "SCOPE2" ? "bg-orange-100 text-orange-700" : "bg-yellow-100 text-yellow-700"}`}>
                        {r.scope}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right font-semibold">{Number(r.total_kgco2e).toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                    <td className="px-4 py-2 text-right">{r.activity_count}</td>
                    <td className="px-4 py-2 text-right">{totalKg > 0 ? ((Number(r.total_kgco2e) / totalKg) * 100).toFixed(1) : 0}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Resources */}
      {tab === "resources" && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <div className="flex justify-end px-4 py-2 border-b">
            <button onClick={() => exportCSV(resources, "esg-resources-report")} className="text-xs text-blue-600 hover:underline">Export CSV</button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Metric</th>
                <th className="px-4 py-3 text-right">Total Quantity</th>
                <th className="px-4 py-3 text-left">Unit</th>
                <th className="px-4 py-3 text-left">Period</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {resources.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No resource metrics. Log energy, water, and waste usage.</td></tr>
              ) : (
                resources.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{r.metric_type}</td>
                    <td className="px-4 py-2 text-right font-semibold">{Number(r.total_quantity).toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                    <td className="px-4 py-2 text-gray-500">{r.unit}</td>
                    <td className="px-4 py-2 text-xs text-gray-400">{r.period}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Standards Note */}
      <div className="bg-gray-50 rounded-lg border p-4 text-xs text-gray-500">
        <p className="font-semibold text-gray-600 mb-1">Standards & Methodology</p>
        <p>Emissions calculated per GHG Protocol. Scope 1 = direct combustion. Scope 2 = purchased electricity. Scope 3 = upstream/downstream value chain. Factors sourced from GHG Protocol 2023, DEFRA 2023, IPCC AR6, and Kenya KPLC Grid Factor.</p>
      </div>
    </div>
  );
}
