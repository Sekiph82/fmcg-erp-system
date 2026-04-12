"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { aiApi, AIRecommendation } from "@/lib/aiApi";

const PRIORITY_PILL: Record<string, string> = {
  low: "bg-gray-100 text-gray-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

const CONFIDENCE_BADGE: Record<string, string> = {
  low: "bg-red-50 text-red-600",
  medium: "bg-yellow-50 text-yellow-700",
  high: "bg-green-50 text-green-700",
};

const CATEGORY_ICON: Record<string, string> = {
  pricing: "💰",
  stock_optimization: "📦",
  supplier_selection: "🤝",
  production_planning: "🏭",
  margin_improvement: "📈",
  default: "💡",
};

export default function RecommendationsPage() {
  const qc = useQueryClient();
  const [categoryFilter, setCategoryFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [showActioned, setShowActioned] = useState(false);
  const [focusArea, setFocusArea] = useState("");

  const { data = [], isLoading } = useQuery<AIRecommendation[]>({
    queryKey: ["ai-recommendations", categoryFilter, priorityFilter, showActioned],
    queryFn: () => aiApi.listRecommendations({
      category: categoryFilter || undefined,
      priority: priorityFilter || undefined,
      include_actioned: showActioned,
    }),
  });

  const generate = useMutation({
    mutationFn: () => aiApi.generateRecommendations(focusArea || undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-recommendations"] }),
  });

  const action = useMutation({
    mutationFn: (id: string) => aiApi.actionRecommendation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-recommendations"] }),
  });

  const dismiss = useMutation({
    mutationFn: (id: string) => aiApi.dismissRecommendation(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-recommendations"] }),
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recommendations</h1>
          <p className="text-sm text-gray-500 mt-0.5">AI-powered actions to optimize your operations</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={focusArea}
            onChange={(e) => setFocusArea(e.target.value)}
            placeholder="Focus area (optional)"
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 w-48 focus:outline-none focus:ring-2 focus:ring-purple-300"
          />
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="px-4 py-2 text-sm font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {generate.isPending ? "Generating…" : "Generate Recommendations"}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-purple-300"
        >
          <option value="">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-purple-300"
        >
          <option value="">All Categories</option>
          <option value="pricing">Pricing</option>
          <option value="stock_optimization">Stock Optimization</option>
          <option value="supplier_selection">Supplier Selection</option>
          <option value="production_planning">Production Planning</option>
          <option value="margin_improvement">Margin Improvement</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showActioned}
            onChange={(e) => setShowActioned(e.target.checked)}
            className="rounded"
          />
          Show actioned
        </label>
        <span className="ml-auto text-sm text-gray-400">{data.length} items</span>
      </div>

      {/* Cards */}
      {isLoading ? (
        <p className="text-center text-gray-400 py-8">Loading recommendations…</p>
      ) : data.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 p-12 text-center">
          <p className="text-gray-400 mb-4">No recommendations yet. Click "Generate Recommendations" to get AI-powered insights.</p>
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="px-4 py-2 text-sm font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {generate.isPending ? "Generating…" : "Generate Now"}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.map((r) => (
            <div
              key={r.id}
              className={`bg-white rounded-xl border shadow-sm p-5 space-y-3 ${r.is_actioned ? "opacity-60 border-gray-100" : "border-gray-200"}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{CATEGORY_ICON[r.category] ?? CATEGORY_ICON.default}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_PILL[r.priority ?? ""] ?? "bg-gray-100 text-gray-600"}`}>
                        {r.priority ?? "—"}
                      </span>
                      <span className="text-xs text-gray-400 capitalize">{r.category.replace(/_/g, " ")}</span>
                    </div>
                    <p className="text-sm font-semibold text-gray-800 mt-0.5">{r.title}</p>
                  </div>
                </div>
                {r.confidence_level && (
                  <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${CONFIDENCE_BADGE[r.confidence_level] ?? "bg-gray-100 text-gray-600"}`}>
                    {r.confidence_level} conf.
                  </span>
                )}
              </div>

              {r.reason && (
                <p className="text-xs text-gray-600 bg-gray-50 rounded p-2">{r.reason}</p>
              )}

              {r.expected_impact && (
                <div className="flex items-start gap-1">
                  <span className="text-xs text-green-600 font-semibold flex-shrink-0">Impact:</span>
                  <span className="text-xs text-gray-600">{r.expected_impact}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-gray-400">{new Date(r.created_at).toLocaleDateString()}</span>
                {!r.is_actioned && !r.is_dismissed && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => action.mutate(r.id)}
                      className="text-xs px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Mark Actioned
                    </button>
                    <button
                      onClick={() => dismiss.mutate(r.id)}
                      className="text-xs px-3 py-1 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
                    >
                      Dismiss
                    </button>
                  </div>
                )}
                {r.is_actioned && <span className="text-xs text-green-600 font-medium">✓ Actioned</span>}
                {r.is_dismissed && <span className="text-xs text-gray-400">Dismissed</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
