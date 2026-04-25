"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allergenApi, riskColor } from "@/lib/allergen";

function Stat({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className={`bg-white border rounded-lg p-4 ${warn && value > 0 ? "border-orange-300" : ""}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${warn && value > 0 ? "text-orange-600" : "text-gray-900"}`}>{value}</p>
    </div>
  );
}

export default function AllergenDashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["an-dashboard"], queryFn: allergenApi.getDashboard });

  const runAll = useMutation({
    mutationFn: async () => {
      const [a, b, c] = await Promise.all([
        allergenApi.runAllergenMonitor(),
        allergenApi.runNutritionAnalyzer(),
        allergenApi.runLabelAssistant(),
      ]);
      return a.generated + b.generated + c.generated;
    },
    onSuccess: (n) => { qc.invalidateQueries({ queryKey: ["an-dashboard"] }); alert(`AI agents ran — ${n} recommendation(s) generated`); },
  });

  const seed = useMutation({
    mutationFn: allergenApi.seedDefaults,
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["an-dashboard"] }); alert(`Seeded ${r.added} default allergens`); },
  });

  if (isLoading) return <div className="p-8 text-gray-400">Loading…</div>;
  if (!data) return null;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Allergen + Nutrition Management</h1>
          <p className="text-sm text-gray-500">Allergen master · Roll-up engine · Nutrition panels · Label readiness</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => seed.mutate()} disabled={seed.isPending} className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50 disabled:opacity-50">
            Seed Allergens
          </button>
          <button onClick={() => runAll.mutate()} disabled={runAll.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
            {runAll.isPending ? "Running AI…" : "Run All AI Agents"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Stat label="Allergens" value={data.total_allergens} />
        <Stat label="Materials Profiled" value={data.materials_with_allergen_profiles} />
        <Stat label="Missing Profiles" value={data.materials_missing_profiles} warn />
        <Stat label="Product Allergen Summaries" value={data.products_with_allergen_summaries} />
        <Stat label="Product Nutrition Summaries" value={data.products_with_nutrition_summaries} />
        <Stat label="Stale Allergen Summaries" value={data.stale_allergen_summaries} warn />
        <Stat label="Stale Nutrition Summaries" value={data.stale_nutrition_summaries} warn />
        <Stat label="Open Change Logs" value={data.open_change_logs} warn />
        <Stat label="Pending Label Reviews" value={data.pending_label_reviews} warn />
        <Stat label="High Cross-Contact Risk" value={data.high_risk_cross_contact} warn />
        <Stat label="AI Pending" value={data.ai_pending} warn />
      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { title: "Missing allergen profiles", count: data.materials_missing_profiles, href: "/dashboard/allergen/material-profiles", color: "text-red-600", desc: "materials without allergen data" },
          { title: "Stale summaries", count: data.stale_allergen_summaries + data.stale_nutrition_summaries, href: "/dashboard/allergen/product-allergens", color: "text-orange-600", desc: "need recalculation" },
          { title: "Label reviews pending", count: data.pending_label_reviews, href: "/dashboard/allergen/change-logs", color: "text-purple-600", desc: "allergen changes to review" },
        ].map((card) => (
          <a key={card.title} href={card.href} className="bg-white border rounded-lg p-4 hover:shadow-sm transition-shadow block">
            <p className={`text-2xl font-bold ${card.color}`}>{card.count}</p>
            <p className="text-sm font-medium text-gray-700 mt-0.5">{card.title}</p>
            <p className="text-xs text-gray-400">{card.desc}</p>
          </a>
        ))}
      </div>

      {/* Quick Navigation */}
      <div className="bg-white border rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-700 mb-3">Quick Navigation</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2">
          {[
            ["Allergen Master", "/dashboard/allergen/allergens"],
            ["Material Profiles", "/dashboard/allergen/material-profiles"],
            ["Nutrition Profiles", "/dashboard/allergen/nutrition"],
            ["Product Allergens", "/dashboard/allergen/product-allergens"],
            ["Product Nutrition", "/dashboard/allergen/product-nutrition"],
            ["Roll-Up Viewer", "/dashboard/allergen/rollup"],
            ["Label Readiness", "/dashboard/allergen/label-readiness"],
            ["Change Logs", "/dashboard/allergen/change-logs"],
            ["Reports", "/dashboard/allergen/reports"],
            ["AI Agents", "/dashboard/allergen/ai"],
          ].map(([label, href]) => (
            <a key={label} href={href} className="px-3 py-2 text-xs text-center bg-gray-50 hover:bg-gray-100 rounded border text-gray-700 font-medium">
              {label}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
