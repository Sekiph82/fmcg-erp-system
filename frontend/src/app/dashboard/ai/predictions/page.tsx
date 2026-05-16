"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { aiApi, AIPrediction } from "@/lib/aiApi";
import { RequirePermission } from "@/components/PermissionGuard";

const RISK_PILL: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

const PREDICTION_TYPES = [
  "sales_forecast",
  "demand_forecast",
  "stock_depletion",
  "production_planning",
  "cost_trend",
  "supplier_risk",
];

const TREND_ICON: Record<string, string> = {
  up: "↑",
  down: "↓",
  stable: "→",
};

export default function PredictionsPage() {
  const qc = useQueryClient();
  const [riskFilter, setRiskFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data = [], isLoading } = useQuery<AIPrediction[]>({
    queryKey: ["ai-predictions", riskFilter, typeFilter],
    queryFn: () => aiApi.listPredictions({
      risk_level: riskFilter || undefined,
      prediction_type: typeFilter || undefined,
      limit: 100,
    }),
  });

  const generate = useMutation({
    mutationFn: () => aiApi.generatePredictions(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-predictions"] }),
  });

  const archive = useMutation({
    mutationFn: (id: string) => aiApi.archivePrediction(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-predictions"] }),
  });

  return (
    <RequirePermission permission="ai.view">
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Predictions</h1>
          <p className="text-sm text-gray-500 mt-0.5">AI-generated forecasts from live ERP data</p>
        </div>
        <button
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {generate.isPending ? "Generating…" : "Generate New Predictions"}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">All Risk Levels</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
        >
          <option value="">All Types</option>
          {PREDICTION_TYPES.map((t) => (
            <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <p className="p-8 text-center text-gray-400">Loading predictions…</p>
        ) : data.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-400 mb-4">No predictions found. Generate predictions to get started.</p>
            <button
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {generate.isPending ? "Generating…" : "Generate Predictions"}
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Subject</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Period</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Forecast</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Confidence</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Risk</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Trend</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.map((p) => (
                <>
                  <tr
                    key={p.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setExpanded(expanded === p.id ? null : p.id)}
                  >
                    <td className="px-4 py-3 font-medium text-gray-800 capitalize">{p.prediction_type.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3 text-gray-600">{p.subject_name ?? "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{p.period ?? "—"}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-800">
                      {p.forecast_value != null ? p.forecast_value.toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {p.confidence_score != null ? (
                        <div className="flex flex-col items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-1.5 mb-0.5">
                            <div
                              className="bg-indigo-500 h-1.5 rounded-full"
                              style={{ width: `${(p.confidence_score * 100).toFixed(0)}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">{(p.confidence_score * 100).toFixed(0)}%</span>
                        </div>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {p.risk_level ? (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${RISK_PILL[p.risk_level] ?? "bg-gray-100 text-gray-600"}`}>
                          {p.risk_level}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-base font-bold ${p.trend === "up" ? "text-green-600" : p.trend === "down" ? "text-red-500" : "text-gray-400"}`}>
                        {TREND_ICON[p.trend ?? ""] ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={(e) => { e.stopPropagation(); archive.mutate(p.id); }}
                        className="text-xs text-gray-400 hover:text-red-500"
                      >
                        Archive
                      </button>
                    </td>
                  </tr>
                  {expanded === p.id && (
                    <tr key={`${p.id}-exp`} className="bg-indigo-50">
                      <td colSpan={8} className="px-6 py-4">
                        <div className="space-y-2">
                          {p.summary && <p className="text-sm text-gray-700 font-medium">{p.summary}</p>}
                          {p.details && Object.keys(p.details).length > 0 && (
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-2">
                              {Object.entries(p.details).map(([k, v]) => (
                                <div key={k} className="bg-white rounded p-2 text-xs">
                                  <span className="text-gray-400 block capitalize">{k.replace(/_/g, " ")}</span>
                                  <span className="text-gray-800 font-medium">{String(v)}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          <p className="text-xs text-gray-400">Created: {new Date(p.created_at).toLocaleString()}</p>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
    </RequirePermission>
  );
}
