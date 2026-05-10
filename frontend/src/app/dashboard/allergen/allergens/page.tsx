"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allergenApi, type AllergenMaster } from "@/lib/allergen";

export default function AllergenMasterPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ allergen_code: "", allergen_name: "", regulatory_name: "", category: "MAJOR", sort_order: 0, notes: "" });

  const { data: allergens } = useQuery({ queryKey: ["allergens"], queryFn: () => allergenApi.listAllergens(false) });
  const create = useMutation({ mutationFn: allergenApi.createAllergen, onSuccess: () => { qc.invalidateQueries({ queryKey: ["allergens"] }); setShowForm(false); } });
  const toggle = useMutation({ mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => allergenApi.updateAllergen(id, { is_active }), onSuccess: () => qc.invalidateQueries({ queryKey: ["allergens"] }) });
  const seed = useMutation({ mutationFn: allergenApi.seedDefaults, onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["allergens"] }); alert(`Seeded ${r.added} allergens`); } });

  const categoryColors: Record<string, string> = { MAJOR: "bg-red-50 text-red-700", MINOR: "bg-orange-50 text-orange-700", CUSTOM: "bg-gray-100 text-gray-600" };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Allergen Master</h1>
        <div className="flex gap-2">
          <button onClick={() => seed.mutate()} disabled={seed.isPending} className="px-3 py-1.5 text-sm border rounded hover:bg-gray-50">Seed Defaults</button>
          <button onClick={() => setShowForm(true)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">+ Add Allergen</button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-gray-700">New Allergen</h2>
          <div className="grid grid-cols-3 gap-3">
            {[["Code", "allergen_code"], ["Name", "allergen_name"], ["Regulatory Name", "regulatory_name"]].map(([label, key]) => (
              <div key={key}>
                <label className="text-xs text-gray-500">{label}</label>
                <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={(form as unknown as Record<string, string>)[key]} onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))} />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500">Category</label>
              <select className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.category} onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}>
                {["MAJOR", "MINOR", "CUSTOM"].map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Sort Order</label>
              <input type="number" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.sort_order} onChange={(e) => setForm((p) => ({ ...p, sort_order: Number(e.target.value) }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Notes</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.notes} onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => create.mutate(form as Partial<AllergenMaster>)} disabled={create.isPending} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Save</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>{["Code", "Name", "Regulatory Name", "Category", "Sort", "Active"].map((h) => <th key={h} className="px-4 py-2 text-left">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!allergens?.length && <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No allergens. Click &quot;Seed Defaults&quot; to load standard allergens.</td></tr>}
            {allergens?.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs font-medium">{a.allergen_code}</td>
                <td className="px-4 py-2 font-medium">{a.allergen_name}</td>
                <td className="px-4 py-2 text-gray-500">{a.regulatory_name || "—"}</td>
                <td className="px-4 py-2"><span className={`text-xs px-2 py-0.5 rounded font-medium ${categoryColors[a.category] || ""}`}>{a.category}</span></td>
                <td className="px-4 py-2 text-gray-400">{a.sort_order}</td>
                <td className="px-4 py-2">
                  <button onClick={() => toggle.mutate({ id: a.id, is_active: !a.is_active })} className={`text-xs px-2 py-0.5 rounded ${a.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {a.is_active ? "Active" : "Inactive"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
