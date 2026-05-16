"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { aiApi, AIFormulation, FormulationIngredient } from "@/lib/aiApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PRODUCT_CATEGORIES = [
  "liquid_detergent",
  "powder_detergent",
  "dishwashing_liquid",
  "hand_soap",
  "body_wash",
  "shampoo",
  "conditioner",
  "surface_cleaner",
  "fabric_softener",
  "toilet_cleaner",
];

const PERFORMANCE_PRIORITIES = [
  { value: "balanced", label: "Balanced" },
  { value: "cost", label: "Cost-First" },
  { value: "performance", label: "Performance-First" },
  { value: "eco", label: "Eco-Friendly" },
  { value: "premium", label: "Premium" },
];

const TARGET_PROPERTY_OPTIONS = [
  "foam_level",
  "cleaning_efficiency",
  "rinse_ability",
  "skin_mildness",
  "antibacterial",
  "biodegradability",
  "viscosity",
  "fragrance_strength",
  "shelf_life_months",
  "ph_target",
];

function IngredientRow({ ing }: { ing: FormulationIngredient }) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-3 py-2 text-sm font-medium text-gray-800">{ing.ingredient_name}</td>
      <td className="px-3 py-2 text-xs text-gray-500">{ing.inci_name ?? "—"}</td>
      <td className="px-3 py-2 text-xs text-gray-500 font-mono">{ing.cas_number ?? "—"}</td>
      <td className="px-3 py-2 text-center">
        <div className="flex items-center gap-1">
          <div className="flex-1 bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-indigo-500 h-1.5 rounded-full"
              style={{ width: `${Math.min(ing.percentage, 100)}%` }}
            />
          </div>
          <span className="text-xs font-mono text-gray-700 w-10 text-right">{ing.percentage.toFixed(1)}%</span>
        </div>
      </td>
      <td className="px-3 py-2 text-xs text-gray-500">{ing.function}</td>
      <td className="px-3 py-2 text-xs text-right text-gray-700 font-mono">
        {ing.approx_cost_per_kg_usd != null ? `$${ing.approx_cost_per_kg_usd.toFixed(2)}/kg` : "—"}
      </td>
    </tr>
  );
}

function FormulationCard({ f, onApprove, onFavorite, onSelect, isSelected, approvalDisabled }: {
  f: AIFormulation;
  onApprove: () => void;
  onFavorite: () => void;
  onSelect: () => void;
  isSelected: boolean;
  approvalDisabled: boolean;
}) {
  return (
    <div
      onClick={onSelect}
      className={`bg-white rounded-xl border shadow-sm p-4 cursor-pointer transition ${
        isSelected ? "border-indigo-400 ring-2 ring-indigo-100" : "border-gray-200 hover:border-gray-300"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-gray-800">{f.name}</p>
          <p className="text-xs text-gray-400 capitalize mt-0.5">{f.product_category.replace(/_/g, " ")} · v{f.version}</p>
        </div>
        <div className="flex gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); onFavorite(); }}
            className={`text-lg leading-none ${f.is_favorite ? "text-yellow-400" : "text-gray-300 hover:text-yellow-300"}`}
          >★</button>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-3">
        {f.estimated_cost_per_kg != null && (
          <span className="text-xs bg-teal-50 text-teal-700 px-2 py-0.5 rounded-full font-medium">
            ${f.estimated_cost_per_kg.toFixed(2)}/kg
          </span>
        )}
        {f.is_approved && (
          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">Approved</span>
        )}
        <span className="text-xs text-gray-400">{f.formulation_data.ingredients?.length ?? 0} ingredients</span>
      </div>
      {!f.is_approved && (
        <button
          onClick={(e) => { e.stopPropagation(); onApprove(); }}
          disabled={approvalDisabled}
          className="mt-2 w-full text-xs py-1 bg-green-50 text-green-700 rounded hover:bg-green-100 disabled:cursor-not-allowed disabled:opacity-50"
          title={approvalDisabled ? "Approval is disabled in AI mock mode" : undefined}
        >
          {approvalDisabled ? "Approval Disabled" : "Approve"}
        </button>
      )}
    </div>
  );
}

export default function FormulationsPage() {
  const qc = useQueryClient();

  // Form state
  const [category, setCategory] = useState("liquid_detergent");
  const [performancePriority, setPerformancePriority] = useState("balanced");
  const [costTarget, setCostTarget] = useState("");
  const [targetProps, setTargetProps] = useState<Record<string, string>>({});
  const [customProp, setCustomProp] = useState("");
  const [customVal, setCustomVal] = useState("");

  // UI state
  const [selected, setSelected] = useState<AIFormulation | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [showApprovedOnly, setShowApprovedOnly] = useState(false);
  const { data: aiStatus } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status(),
    staleTime: 30_000,
  });
  const approvalDisabled = aiStatus?.mode === "mock";

  const { data: formulations = [], isLoading } = useQuery<AIFormulation[]>({
    queryKey: ["ai-formulations", categoryFilter, showApprovedOnly],
    queryFn: () => aiApi.listFormulations({
      product_category: categoryFilter || undefined,
      is_approved: showApprovedOnly || undefined,
    }),
  });

  const generate = useMutation({
    mutationFn: () => {
      const allProps: Record<string, unknown> = {};
      Object.entries(targetProps).forEach(([k, v]) => { allProps[k] = isNaN(Number(v)) ? v : Number(v); });
      if (customProp && customVal) allProps[customProp] = customVal;
      return aiApi.generateFormulation({
        product_category: category,
        target_properties: allProps,
        cost_target: costTarget ? Number(costTarget) : undefined,
        performance_priority: performancePriority,
      });
    },
    onSuccess: (data) => {
      setSelected(data);
      qc.invalidateQueries({ queryKey: ["ai-formulations"] });
    },
  });

  const approve = useMutation({
    mutationFn: (id: string) => aiApi.approveFormulation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-formulations"] });
      if (selected) setSelected((prev) => prev ? { ...prev, is_approved: true } : null);
    },
  });

  const favorite = useMutation({
    mutationFn: (id: string) => aiApi.toggleFavorite(id),
    onSuccess: (data, id) => {
      qc.invalidateQueries({ queryKey: ["ai-formulations"] });
      if (selected?.id === id) setSelected((prev) => prev ? { ...prev, is_favorite: data.is_favorite } : null);
    },
  });

  const addTargetProp = (key: string) => {
    if (!targetProps[key]) setTargetProps((prev) => ({ ...prev, [key]: "" }));
  };

  const fd = selected?.formulation_data;
  const totalPct = fd?.ingredients?.reduce((s, i) => s + i.percentage, 0) ?? 0;

  return (
    <RequirePermission permission="ai.view">
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Formulation Engine</h1>
        <p className="text-sm text-gray-500 mt-0.5">AI-generated FMCG chemical formulations with real INCI names, CAS numbers, and cost estimates</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left: Input Form */}
        <div className="xl:col-span-3 space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
            <h2 className="font-semibold text-gray-800">Generate Formulation</h2>

            {/* Product Category */}
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Product Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-300"
              >
                {PRODUCT_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>

            {/* Performance Priority */}
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Optimization Priority</label>
              <div className="grid grid-cols-1 gap-1.5">
                {PERFORMANCE_PRIORITIES.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => setPerformancePriority(p.value)}
                    className={`text-sm px-3 py-2 rounded-lg border text-left transition ${
                      performancePriority === p.value
                        ? "border-teal-400 bg-teal-50 text-teal-800 font-medium"
                        : "border-gray-200 text-gray-600 hover:border-gray-300"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Cost Target */}
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Cost Target (USD/kg, optional)</label>
              <input
                type="number"
                step="0.1"
                value={costTarget}
                onChange={(e) => setCostTarget(e.target.value)}
                placeholder="e.g. 1.50"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-300"
              />
            </div>

            {/* Target Properties */}
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-2">Target Properties</label>
              <div className="flex flex-wrap gap-1 mb-2">
                {TARGET_PROPERTY_OPTIONS.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => addTargetProp(opt)}
                    className={`text-xs px-2 py-0.5 rounded border transition ${
                      opt in targetProps
                        ? "border-teal-400 bg-teal-50 text-teal-700"
                        : "border-gray-200 text-gray-500 hover:border-teal-300"
                    }`}
                  >
                    {opt.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
              {Object.entries(targetProps).map(([k, v]) => (
                <div key={k} className="flex items-center gap-1 mb-1">
                  <span className="text-xs text-gray-500 flex-1 capitalize">{k.replace(/_/g, " ")}</span>
                  <input
                    value={v}
                    onChange={(e) => setTargetProps((prev) => ({ ...prev, [k]: e.target.value }))}
                    placeholder="value"
                    className="text-xs border border-gray-200 rounded px-2 py-1 w-20 focus:outline-none"
                  />
                  <button onClick={() => setTargetProps((prev) => { const n = { ...prev }; delete n[k]; return n; })} className="text-gray-300 hover:text-red-400 text-xs">✕</button>
                </div>
              ))}
              <div className="flex gap-1 mt-1">
                <input
                  value={customProp}
                  onChange={(e) => setCustomProp(e.target.value)}
                  placeholder="custom property"
                  className="text-xs border border-gray-200 rounded px-2 py-1 flex-1 focus:outline-none"
                />
                <input
                  value={customVal}
                  onChange={(e) => setCustomVal(e.target.value)}
                  placeholder="value"
                  className="text-xs border border-gray-200 rounded px-2 py-1 w-16 focus:outline-none"
                />
              </div>
            </div>

            <button
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="w-full py-3 text-sm font-bold bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50"
            >
              {generate.isPending ? "AI Formulating…" : "🧪 Generate Formulation"}
            </button>
            {generate.isPending && (
              <p className="text-xs text-teal-600 text-center animate-pulse">
                Generating real chemical formulation with INCI names, CAS numbers, and cost analysis…
              </p>
            )}
          </div>

          {/* Saved Formulations List */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-50 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-800">Saved Formulations</h3>
              <span className="text-xs text-gray-400">{formulations.length}</span>
            </div>
            <div className="px-3 py-2 border-b border-gray-50 flex gap-2">
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="text-xs border border-gray-200 rounded px-2 py-1 flex-1"
              >
                <option value="">All categories</option>
                {PRODUCT_CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
              </select>
              <label className="flex items-center gap-1 text-xs text-gray-500">
                <input type="checkbox" checked={showApprovedOnly} onChange={(e) => setShowApprovedOnly(e.target.checked)} />
                Approved
              </label>
            </div>
            {isLoading ? (
              <p className="p-4 text-center text-xs text-gray-400">Loading…</p>
            ) : formulations.length === 0 ? (
              <p className="p-4 text-center text-xs text-gray-400">No formulations yet.</p>
            ) : (
              <div className="p-3 space-y-2">
                {formulations.map((f) => (
                  <FormulationCard
                    key={f.id}
                    f={f}
                    isSelected={selected?.id === f.id}
                    onSelect={() => setSelected(f)}
                    onApprove={() => approve.mutate(f.id)}
                    onFavorite={() => favorite.mutate(f.id)}
                    approvalDisabled={approvalDisabled}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Formulation Detail */}
        <div className="xl:col-span-9 space-y-4">
          {!selected && !generate.isPending && (
            <div className="bg-white rounded-xl border border-dashed border-gray-300 p-16 text-center">
              <p className="text-4xl mb-3">🧪</p>
              <p className="text-gray-500 font-medium">Select a saved formulation or generate a new one</p>
              <p className="text-sm text-gray-400 mt-1">AI will generate real INCI names, CAS numbers, percentages summing to 100%, cost estimates, and process instructions</p>
            </div>
          )}

          {generate.isPending && (
            <div className="bg-teal-50 border border-teal-200 rounded-xl p-12 text-center">
              <div className="animate-pulse">
                <p className="text-3xl mb-3">⚗️</p>
                <p className="text-teal-700 font-semibold">AI is formulating your product…</p>
                <p className="text-sm text-teal-500 mt-1">Calculating ingredient percentages, INCI names, cost estimates</p>
              </div>
            </div>
          )}

          {selected && fd && (
            <>
              {/* Header */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{fd.name}</h2>
                    <p className="text-sm text-gray-500 capitalize mt-0.5">
                      {fd.product_category.replace(/_/g, " ")} · Version {fd.version}
                    </p>
                    {fd.description && <p className="text-sm text-gray-600 mt-1">{fd.description}</p>}
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      onClick={() => favorite.mutate(selected.id)}
                      className={`text-xl ${selected.is_favorite ? "text-yellow-400" : "text-gray-300 hover:text-yellow-300"}`}
                    >★</button>
                    {!selected.is_approved && (
                      <button
                        onClick={() => approve.mutate(selected.id)}
                        disabled={approvalDisabled}
                        title={approvalDisabled ? "Approval is disabled in AI mock mode" : undefined}
                        className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {approvalDisabled ? "Approval Disabled" : "Approve"}
                      </button>
                    )}
                    {selected.is_approved && (
                      <span className="px-3 py-1.5 text-sm bg-green-100 text-green-700 rounded-lg font-medium">✓ Approved</span>
                    )}
                  </div>
                </div>

                {/* Quick stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                  {fd.estimated_ph && (
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <p className="text-xs text-gray-400">pH</p>
                      <p className="text-sm font-bold text-gray-800">{fd.estimated_ph}</p>
                    </div>
                  )}
                  {fd.estimated_viscosity_cP && (
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <p className="text-xs text-gray-400">Viscosity</p>
                      <p className="text-sm font-bold text-gray-800">{fd.estimated_viscosity_cP} cP</p>
                    </div>
                  )}
                  {fd.shelf_life && (
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <p className="text-xs text-gray-400">Shelf Life</p>
                      <p className="text-sm font-bold text-gray-800">{fd.shelf_life}</p>
                    </div>
                  )}
                  {fd.processing_temperature && (
                    <div className="bg-gray-50 rounded-lg p-2 text-center">
                      <p className="text-xs text-gray-400">Proc. Temp</p>
                      <p className="text-sm font-bold text-gray-800">{fd.processing_temperature}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Ingredients Table */}
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-800">Ingredients</h3>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">Total:</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${Math.abs(totalPct - 100) < 0.5 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {totalPct.toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-100">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Ingredient</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">INCI Name</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">CAS Number</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 w-32">%</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Function</th>
                        <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">Cost/kg</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {fd.ingredients?.map((ing, i) => <IngredientRow key={i} ing={ing} />)}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Cost + Performance */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {fd.cost_breakdown && (
                  <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                    <h3 className="font-semibold text-gray-800 mb-3">Cost Breakdown</h3>
                    <div className="space-y-2">
                      {[
                        ["Raw Materials", fd.cost_breakdown.raw_materials_per_kg_usd],
                        ["Packaging", fd.cost_breakdown.packaging_estimate_per_unit_usd],
                        ["Labor & Overhead", fd.cost_breakdown.labor_overhead_per_kg_usd],
                      ].map(([label, val]) => (
                        <div key={label as string} className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">{label as string}</span>
                          <span className="text-sm font-mono text-gray-800">${(val as number).toFixed(3)}/kg</span>
                        </div>
                      ))}
                      <div className="border-t border-gray-100 pt-2 flex items-center justify-between">
                        <span className="text-sm font-semibold text-gray-800">Total COGS</span>
                        <span className="text-sm font-bold text-teal-700 font-mono">${fd.cost_breakdown.total_cogs_per_kg_usd.toFixed(3)}/kg</span>
                      </div>
                    </div>
                  </div>
                )}

                {fd.performance_profile && (
                  <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                    <h3 className="font-semibold text-gray-800 mb-3">Performance Profile</h3>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(fd.performance_profile)
                        .filter(([, v]) => v)
                        .map(([k, v]) => (
                          <div key={k} className="bg-gray-50 rounded p-2">
                            <p className="text-xs text-gray-400 capitalize">{k.replace(/_/g, " ")}</p>
                            <p className="text-xs font-semibold text-gray-800">{v}</p>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Process Instructions */}
              {fd.process_instructions && fd.process_instructions.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                  <h3 className="font-semibold text-gray-800 mb-3">Process Instructions</h3>
                  <ol className="space-y-2">
                    {fd.process_instructions.map((step, i) => (
                      <li key={i} className="flex gap-3">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-100 text-teal-700 text-xs font-bold flex items-center justify-center">
                          {i + 1}
                        </span>
                        <p className="text-sm text-gray-700 pt-0.5">{step}</p>
                      </li>
                    ))}
                  </ol>
                  {(fd.mixing_speed || fd.processing_temperature) && (
                    <div className="flex gap-4 mt-3 pt-3 border-t border-gray-50">
                      {fd.processing_temperature && (
                        <span className="text-xs text-gray-500">🌡️ Temp: <strong>{fd.processing_temperature}</strong></span>
                      )}
                      {fd.mixing_speed && (
                        <span className="text-xs text-gray-500">⚙️ Mix: <strong>{fd.mixing_speed}</strong></span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Alternatives */}
              {fd.alternatives && (
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                  <h3 className="font-semibold text-gray-800 mb-3">Alternative Versions</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {fd.alternatives.low_cost && (
                      <div className="border border-gray-200 rounded-lg p-3">
                        <p className="text-xs font-bold text-gray-500 mb-1">💵 Low-Cost Version</p>
                        <p className="text-sm font-medium text-gray-800">{fd.alternatives.low_cost.name}</p>
                        <p className="text-xs text-gray-500 mt-1">Changes: {fd.alternatives.low_cost.key_changes}</p>
                        <p className="text-xs text-red-500 mt-1">Trade-offs: {fd.alternatives.low_cost.trade_offs}</p>
                      </div>
                    )}
                    {fd.alternatives.premium && (
                      <div className="border border-purple-200 rounded-lg p-3 bg-purple-50">
                        <p className="text-xs font-bold text-purple-500 mb-1">👑 Premium Version</p>
                        <p className="text-sm font-medium text-gray-800">{fd.alternatives.premium.name}</p>
                        <p className="text-xs text-gray-500 mt-1">Changes: {fd.alternatives.premium.key_changes}</p>
                        <p className="text-xs text-gray-500 mt-1">Trade-offs: {fd.alternatives.premium.trade_offs}</p>
                      </div>
                    )}
                    {fd.alternatives.eco && (
                      <div className="border border-green-200 rounded-lg p-3 bg-green-50">
                        <p className="text-xs font-bold text-green-600 mb-1">🌿 Eco Version</p>
                        <p className="text-sm font-medium text-gray-800">{fd.alternatives.eco.name}</p>
                        <p className="text-xs text-gray-500 mt-1">Changes: {fd.alternatives.eco.key_changes}</p>
                        <p className="text-xs text-gray-500 mt-1">Trade-offs: {fd.alternatives.eco.trade_offs}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Safety & Regulatory Notes */}
              {(fd.safety_notes?.length || fd.regulatory_notes) && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
                  <h3 className="font-semibold text-amber-800 mb-2">⚠️ Safety & Regulatory Notes</h3>
                  {fd.safety_notes && (
                    <ul className="space-y-1 mb-2">
                      {fd.safety_notes.map((note, i) => (
                        <li key={i} className="text-sm text-amber-700 flex gap-2"><span>•</span>{note}</li>
                      ))}
                    </ul>
                  )}
                  {fd.regulatory_notes && (
                    <p className="text-sm text-amber-700">{fd.regulatory_notes}</p>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
    </RequirePermission>
  );
}
