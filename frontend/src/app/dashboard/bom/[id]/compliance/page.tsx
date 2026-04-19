"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { bomApi, ComplianceSummary } from "@/lib/bom";

const ALLERGEN_ICONS: Record<string, string> = {
  dairy: "🥛", soy: "🫘", nuts: "🥜", gluten: "🌾", eggs: "🥚",
  sesame: "🌿", sulfites: "⚗️", shellfish: "🦐", fish: "🐟", other: "⚠️",
};

export default function CompliancePage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading } = useQuery<ComplianceSummary>({
    queryKey: ["bom-compliance", id],
    queryFn: () => bomApi.compliance(id),
  });

  if (isLoading) return <div className="p-8 text-center text-gray-400">Checking compliance…</div>;
  if (!data) return null;

  const presentAllergens = Object.entries(data.allergen_flags).filter(([, v]) => v).map(([k]) => k);
  const absentAllergens = Object.entries(data.allergen_flags).filter(([, v]) => !v).map(([k]) => k);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <a href={`/dashboard/bom/${id}`} className="text-sm text-gray-400 hover:text-gray-600">← BOM Detail</a>
        <h1 className="text-xl font-bold text-gray-900">Compliance & Allergen Summary</h1>
      </div>

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <h3 className="font-semibold text-amber-800 mb-2">Warnings ({data.warnings.length})</h3>
          <ul className="space-y-1">
            {data.warnings.map((w, i) => (
              <li key={i} className="text-sm text-amber-700 flex items-start gap-2"><span>⚠</span>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Allergen Grid */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Allergen Profile</h3>
          {presentAllergens.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-medium text-red-600 mb-2">CONTAINS</p>
              <div className="flex flex-wrap gap-2">
                {presentAllergens.map((a) => (
                  <span key={a} className="flex items-center gap-1 bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm font-medium">
                    <span>{ALLERGEN_ICONS[a] || "⚠️"}</span>
                    <span className="capitalize">{a}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          {absentAllergens.length > 0 && (
            <div>
              <p className="text-xs font-medium text-green-600 mb-2">FREE FROM</p>
              <div className="flex flex-wrap gap-2">
                {absentAllergens.map((a) => (
                  <span key={a} className="flex items-center gap-1 bg-green-50 text-green-700 px-2 py-0.5 rounded-full text-xs">
                    <span>{ALLERGEN_ICONS[a] || "✓"}</span>
                    <span className="capitalize">{a}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
          {presentAllergens.length === 0 && absentAllergens.length === 0 && (
            <p className="text-sm text-gray-400">No allergen data available.</p>
          )}
        </div>

        {/* Cross-Contact Risks */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-3">Cross-Contact Risks</h3>
          {data.cross_contact_risks.length === 0 ? (
            <p className="text-sm text-green-600">No cross-contact risks identified.</p>
          ) : (
            <ul className="space-y-2">
              {data.cross_contact_risks.map((r, i) => (
                <li key={i} className="text-sm text-orange-700 bg-orange-50 rounded-lg px-3 py-2 flex items-start gap-2">
                  <span>⚡</span>{r}
                </li>
              ))}
            </ul>
          )}
          <h3 className="font-semibold text-gray-800 mt-5 mb-3">Critical Components</h3>
          {data.critical_components.length === 0 ? (
            <p className="text-sm text-gray-400">None flagged.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {data.critical_components.map((c, i) => (
                <span key={i} className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">! {c}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Nutrition */}
      {data.nutrition_per_100g && Object.keys(data.nutrition_per_100g).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Nutrition per 100g</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(data.nutrition_per_100g).map(([key, value]) => (
              <div key={key} className="text-center bg-gray-50 rounded-lg p-3">
                <p className="text-2xl font-bold text-gray-800">{Number(value).toFixed(1)}</p>
                <p className="text-xs text-gray-500 mt-0.5 capitalize">{key}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
