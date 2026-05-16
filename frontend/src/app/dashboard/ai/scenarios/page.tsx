"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { aiApi, AIScenario } from "@/lib/aiApi";
import { RequirePermission } from "@/components/PermissionGuard";

const SCENARIO_TYPES = [
  { value: "price_change", label: "Price Change", icon: "💰", params: ["product_name", "current_price", "proposed_price", "market_segment"] },
  { value: "cost_change", label: "Cost Change", icon: "📉", params: ["material_name", "current_cost_per_kg", "new_cost_per_kg", "usage_kg_per_month"] },
  { value: "supplier_change", label: "Supplier Change", icon: "🤝", params: ["material_name", "current_supplier", "new_supplier", "price_difference_percent"] },
  { value: "production_change", label: "Production Change", icon: "🏭", params: ["product_name", "current_volume_units", "proposed_volume_units", "timeframe_months"] },
  { value: "demand_shift", label: "Demand Shift", icon: "📊", params: ["product_category", "demand_change_percent", "cause", "duration_months"] },
];

export default function ScenariosPage() {
  const qc = useQueryClient();
  const [selectedType, setSelectedType] = useState(SCENARIO_TYPES[0]);
  const [title, setTitle] = useState("");
  const [params, setParams] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AIScenario | null>(null);
  const [typeFilter, setTypeFilter] = useState("");

  const { data: scenarios = [], isLoading } = useQuery<AIScenario[]>({
    queryKey: ["ai-scenarios", typeFilter],
    queryFn: () => aiApi.listScenarios({ scenario_type: typeFilter || undefined }),
  });

  const simulate = useMutation({
    mutationFn: () => aiApi.simulateScenario({
      scenario_type: selectedType.value,
      parameters: Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== "").map(([k, v]) => [k, isNaN(Number(v)) ? v : Number(v)])
      ),
      title: title || undefined,
    }),
    onSuccess: (data) => {
      setResult(data);
      qc.invalidateQueries({ queryKey: ["ai-scenarios"] });
    },
  });

  const handleTypeSelect = (t: typeof SCENARIO_TYPES[0]) => {
    setSelectedType(t);
    setParams({});
    setResult(null);
  };

  return (
    <RequirePermission permission="ai.view">
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Scenario Simulator</h1>
        <p className="text-sm text-gray-500 mt-0.5">Model &quot;what if&quot; changes before committing to them</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Simulator Form */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
            <h2 className="font-semibold text-gray-800">Configure Scenario</h2>

            {/* Scenario Type */}
            <div className="grid grid-cols-1 gap-2">
              {SCENARIO_TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => handleTypeSelect(t)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition ${
                    selectedType.value === t.value
                      ? "border-indigo-400 bg-indigo-50 text-indigo-800"
                      : "border-gray-200 hover:border-gray-300 text-gray-700"
                  }`}
                >
                  <span className="text-xl">{t.icon}</span>
                  <span className="text-sm font-medium">{t.label}</span>
                </button>
              ))}
            </div>

            {/* Title */}
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Scenario Title (optional)</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={`e.g. "Q3 Price Increase for Detergent 5L"`}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              />
            </div>

            {/* Dynamic Params */}
            <div className="space-y-3">
              <p className="text-xs font-semibold text-gray-500">Parameters</p>
              {selectedType.params.map((param) => (
                <div key={param}>
                  <label className="block text-xs text-gray-500 mb-1 capitalize">{param.replace(/_/g, " ")}</label>
                  <input
                    value={params[param] ?? ""}
                    onChange={(e) => setParams((prev) => ({ ...prev, [param]: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                  />
                </div>
              ))}
            </div>

            <button
              onClick={() => simulate.mutate()}
              disabled={simulate.isPending}
              className="w-full py-2.5 text-sm font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {simulate.isPending ? "Simulating with AI…" : "Run Simulation"}
            </button>
          </div>
        </div>

        {/* Result + History */}
        <div className="lg:col-span-3 space-y-4">
          {/* Latest Result */}
          {simulate.isPending && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-6 text-center">
              <div className="animate-pulse text-indigo-600 font-medium">AI is analyzing your scenario…</div>
            </div>
          )}

          {result && (
            <div className="bg-white rounded-xl border border-indigo-200 shadow-sm p-5 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-800">{result.title}</h3>
                  <p className="text-xs text-gray-400 capitalize">{result.scenario_type.replace(/_/g, " ")} · {new Date(result.created_at).toLocaleString()}</p>
                </div>
                <button onClick={() => setResult(null)} className="text-gray-400 hover:text-gray-600 text-xs">✕</button>
              </div>

              {result.expected_impact && (
                <div className="bg-blue-50 rounded-lg p-3">
                  <p className="text-xs font-semibold text-blue-700 mb-1">Expected Impact</p>
                  <p className="text-sm text-gray-700">{typeof result.expected_impact === "object" ? JSON.stringify(result.expected_impact) : String(result.expected_impact ?? "")}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                {result.risks && result.risks.length > 0 && (
                  <div className="bg-red-50 rounded-lg p-3">
                    <p className="text-xs font-semibold text-red-700 mb-2">Risks</p>
                    <ul className="space-y-1">
                      {result.risks.map((r, i) => (
                        <li key={i} className="text-xs text-gray-700 flex gap-1"><span className="text-red-400">•</span>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.opportunities && result.opportunities.length > 0 && (
                  <div className="bg-green-50 rounded-lg p-3">
                    <p className="text-xs font-semibold text-green-700 mb-2">Opportunities</p>
                    <ul className="space-y-1">
                      {result.opportunities.map((o, i) => (
                        <li key={i} className="text-xs text-gray-700 flex gap-1"><span className="text-green-500">•</span>{o}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {result.simulation_data && Object.keys(result.simulation_data).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 mb-2">Simulation Data</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(result.simulation_data)
                      .filter(([, v]) => typeof v !== "object")
                      .map(([k, v]) => (
                        <div key={k} className="bg-gray-50 rounded p-2">
                          <span className="text-xs text-gray-400 block capitalize">{k.replace(/_/g, " ")}</span>
                          <span className="text-sm font-semibold text-gray-800">{String(v)}</span>
                        </div>
                      ))}
                  </div>
                  {Object.entries(result.simulation_data)
                    .filter(([, v]) => typeof v === "object" && v !== null)
                    .map(([k, v]) => (
                      <div key={k} className="mt-2">
                        <p className="text-xs font-semibold text-gray-500 mb-1 capitalize">{k.replace(/_/g, " ")}</p>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                          {Object.entries(v as Record<string, unknown>).map(([sk, sv]) => (
                            <div key={sk} className="bg-gray-50 rounded p-2">
                              <span className="text-xs text-gray-400 block capitalize">{sk.replace(/_/g, " ")}</span>
                              <span className="text-sm font-semibold text-gray-800">{String(sv)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}

          {/* History */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-50">
              <h2 className="font-semibold text-gray-800">Simulation History</h2>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="text-xs border border-gray-200 rounded px-2 py-1"
              >
                <option value="">All types</option>
                {SCENARIO_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            {isLoading ? (
              <p className="p-6 text-center text-gray-400 text-sm">Loading…</p>
            ) : scenarios.length === 0 ? (
              <p className="p-6 text-center text-gray-400 text-sm">No simulations yet.</p>
            ) : (
              <div className="divide-y divide-gray-50">
                {scenarios.slice(0, 10).map((s) => (
                  <div key={s.id} className="px-5 py-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-800">{s.title}</p>
                      <p className="text-xs text-gray-400 capitalize">{s.scenario_type.replace(/_/g, " ")} · {new Date(s.created_at).toLocaleDateString()}</p>
                      {s.expected_impact && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{typeof s.expected_impact === "object" ? JSON.stringify(s.expected_impact) : String(s.expected_impact)}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
    </RequirePermission>
  );
}
