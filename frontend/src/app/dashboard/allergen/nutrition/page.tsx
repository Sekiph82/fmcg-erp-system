"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allergenApi, DEFAULT_NUTRIENTS, type NutritionProfile } from "@/lib/allergen";

export default function NutritionProfilesPage() {
  const qc = useQueryClient();
  const [entityType, setEntityType] = useState<"material" | "product">("material");
  const [showForm, setShowForm] = useState(false);
  const [selected, setSelected] = useState<NutritionProfile | null>(null);
  const [form, setForm] = useState({
    entity_id: "", basis_type: "PER_100G", notes: "",
    lines: DEFAULT_NUTRIENTS.map((n) => ({ ...n, nutrient_code: n.code, nutrient_name: n.name, value: "", source_type: "MANUAL", approved_flag: false })),
  });
  const [addLine, setAddLine] = useState({ nutrient_code: "", nutrient_name: "", unit: "g", value: "", source_type: "MANUAL" });

  const { data: profiles } = useQuery({ queryKey: ["nutrition-profiles", entityType], queryFn: () => allergenApi.listNutritionProfiles(entityType) });

  const create = useMutation({
    mutationFn: () => {
      const lines = form.lines.filter((l) => l.value !== "").map((l) => ({ nutrient_code: l.nutrient_code, nutrient_name: l.nutrient_name, unit: l.unit, value: Number(l.value), source_type: l.source_type, approved_flag: l.approved_flag }));
      if (entityType === "material") {
        return allergenApi.createMaterialNutrition(form.entity_id, { basis_type: form.basis_type as NutritionProfile["basis_type"], notes: form.notes, lines } as unknown as Partial<NutritionProfile>);
      }
      return allergenApi.createProductNutrition(form.entity_id, { basis_type: form.basis_type as NutritionProfile["basis_type"], notes: form.notes, lines } as unknown as Partial<NutritionProfile>);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["nutrition-profiles"] }); setShowForm(false); },
  });

  const addNutrientLine = useMutation({
    mutationFn: ({ profileId, data }: { profileId: string; data: object }) => allergenApi.addNutritionLine(profileId, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["nutrition-profiles"] }); setSelected(null); },
  });

  const sourceColors: Record<string, string> = { SUPPLIER: "bg-blue-50 text-blue-700", LAB: "bg-purple-50 text-purple-700", MANUAL: "bg-gray-100 text-gray-600", CALCULATED: "bg-green-50 text-green-700" };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Nutrition Profiles</h1>
          <p className="text-sm text-gray-500">Nutritional data per 100g for raw materials and finished goods</p>
        </div>
        <button onClick={() => setShowForm(true)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">+ New Profile</button>
      </div>

      <div className="flex gap-2">
        {["material", "product"].map((t) => (
          <button key={t} onClick={() => setEntityType(t as "material" | "product")} className={`px-3 py-1 text-xs rounded border ${entityType === t ? "bg-gray-900 text-white border-gray-900" : "bg-white hover:bg-gray-50"}`}>
            {t === "material" ? "Raw Materials" : "Products"}
          </button>
        ))}
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-4">
          <h2 className="text-sm font-medium text-gray-700">New Nutrition Profile — {entityType}</h2>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="text-xs text-gray-500">{entityType === "material" ? "Material" : "Product"} ID (UUID) *</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={form.entity_id} onChange={(e) => setForm((p) => ({ ...p, entity_id: e.target.value }))} placeholder="uuid..." />
            </div>
            <div>
              <label className="text-xs text-gray-500">Basis</label>
              <select className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.basis_type} onChange={(e) => setForm((p) => ({ ...p, basis_type: e.target.value }))}>
                {["PER_100G", "PER_100ML", "PER_SERVING", "PER_UNIT"].map((b) => <option key={b}>{b}</option>)}
              </select>
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-600 font-medium mb-2">Nutritional Values (per 100g)</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {form.lines.map((line, i) => (
                <div key={line.nutrient_code} className="flex items-center gap-2 bg-gray-50 rounded p-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-500 truncate">{line.nutrient_name} ({line.unit})</p>
                    <input
                      type="number"
                      step="0.01"
                      className="w-full mt-0.5 border rounded px-1.5 py-1 text-xs"
                      value={form.lines[i].value}
                      onChange={(e) => {
                        const updated = [...form.lines];
                        updated[i] = { ...updated[i], value: e.target.value };
                        setForm((p) => ({ ...p, lines: updated }));
                      }}
                      placeholder="0.00"
                    />
                  </div>
                  <select
                    className="text-xs border rounded px-1 py-0.5"
                    value={form.lines[i].source_type}
                    onChange={(e) => {
                      const updated = [...form.lines];
                      updated[i] = { ...updated[i], source_type: e.target.value };
                      setForm((p) => ({ ...p, lines: updated }));
                    }}
                  >
                    {["MANUAL", "SUPPLIER", "LAB", "CALCULATED"].map((s) => <option key={s}>{s}</option>)}
                  </select>
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => create.mutate()} disabled={create.isPending || !form.entity_id} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Save Profile</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
          </div>
        </div>
      )}

      {/* Profiles Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {!profiles?.length && <div className="col-span-3 bg-white border rounded-lg p-8 text-center text-gray-400">No nutrition profiles yet</div>}
        {profiles?.map((p) => (
          <div key={p.id} className="bg-white border rounded-lg p-4 hover:shadow-sm cursor-pointer" onClick={() => setSelected(p)}>
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="text-sm font-medium text-gray-900">{p.entity_name || "Unknown"}</h3>
                <p className="text-xs text-gray-500">{p.basis_type} · {p.lines.length} nutrients</p>
              </div>
            </div>
            <div className="space-y-1">
              {p.lines.slice(0, 5).map((l) => (
                <div key={l.id} className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">{l.nutrient_name}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium">{l.value} {l.unit}</span>
                    <span className={`px-1 py-0.5 rounded text-xs ${sourceColors[l.source_type] || ""}`}>{l.source_type[0]}</span>
                    {l.approved_flag && <span className="text-green-600 text-xs">✓</span>}
                  </div>
                </div>
              ))}
              {p.lines.length > 5 && <p className="text-xs text-gray-400 text-right">+{p.lines.length - 5} more</p>}
            </div>
          </div>
        ))}
      </div>

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-lg p-6 max-w-xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-medium text-gray-900 mb-3">{selected.entity_name} — Nutrition ({selected.basis_type})</h3>
            <table className="w-full text-sm">
              <thead className="text-xs text-gray-500"><tr><th className="text-left py-1">Nutrient</th><th className="text-right py-1">Value</th><th className="text-left py-1 pl-2">Unit</th><th className="text-left py-1 pl-2">Source</th><th className="text-center py-1">Approved</th></tr></thead>
              <tbody className="divide-y divide-gray-100">
                {selected.lines.map((l) => (
                  <tr key={l.id}>
                    <td className="py-1.5">{l.nutrient_name}</td>
                    <td className="py-1.5 text-right font-mono font-medium">{l.value}</td>
                    <td className="py-1.5 pl-2 text-gray-500">{l.unit}</td>
                    <td className="py-1.5 pl-2"><span className={`text-xs px-1.5 py-0.5 rounded ${sourceColors[l.source_type] || ""}`}>{l.source_type}</span></td>
                    <td className="py-1.5 text-center">{l.approved_flag ? "✓" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Add line form */}
            <div className="mt-4 border-t pt-3">
              <p className="text-xs text-gray-600 font-medium mb-2">Add Nutrient Line</p>
              <div className="flex gap-2">
                <input className="flex-1 border rounded px-2 py-1 text-xs" placeholder="Code" value={addLine.nutrient_code} onChange={(e) => setAddLine((p) => ({ ...p, nutrient_code: e.target.value }))} />
                <input className="flex-1 border rounded px-2 py-1 text-xs" placeholder="Name" value={addLine.nutrient_name} onChange={(e) => setAddLine((p) => ({ ...p, nutrient_name: e.target.value }))} />
                <input className="w-16 border rounded px-2 py-1 text-xs" placeholder="Value" type="number" value={addLine.value} onChange={(e) => setAddLine((p) => ({ ...p, value: e.target.value }))} />
                <input className="w-12 border rounded px-2 py-1 text-xs" placeholder="Unit" value={addLine.unit} onChange={(e) => setAddLine((p) => ({ ...p, unit: e.target.value }))} />
                <button
                  onClick={() => addNutrientLine.mutate({ profileId: selected.id, data: { ...addLine, value: Number(addLine.value) } })}
                  disabled={addNutrientLine.isPending || !addLine.nutrient_code}
                  className="px-2 py-1 text-xs bg-blue-600 text-white rounded disabled:opacity-50"
                >Add</button>
              </div>
            </div>

            <button onClick={() => setSelected(null)} className="mt-3 px-3 py-1.5 text-sm border rounded">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
