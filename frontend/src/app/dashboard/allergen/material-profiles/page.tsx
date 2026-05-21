"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { allergenApi, presenceColor, riskColor, type MaterialAllergenProfile } from "@/lib/allergen";

export default function MaterialProfilesPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<boolean | undefined>(undefined);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    material_id: "",
    cross_contact_risk_level: "NONE",
    supplier_allergen_statement_ref: "",
    allergen_review_date: "",
    approved_by: "",
    notes: "",
    lines: [] as Array<{ allergen_id: string; presence_type: string; declaration_required: boolean; critical_flag: boolean }>,
  });
  const [selected, setSelected] = useState<MaterialAllergenProfile | null>(null);

  const { data: profiles } = useQuery({ queryKey: ["allergen-profiles", filter], queryFn: () => allergenApi.listAllergenProfiles(filter) });
  const { data: allergens } = useQuery({ queryKey: ["allergens"], queryFn: () => allergenApi.listAllergens() });

  const create = useMutation({
    mutationFn: () => allergenApi.upsertAllergenProfile(form.material_id, form as Partial<MaterialAllergenProfile>),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["allergen-profiles"] }); setShowForm(false); },
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Material Allergen Profiles</h1>
          <p className="text-sm text-gray-500">Allergen declarations per raw material</p>
        </div>
        <button onClick={() => setShowForm(true)} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">+ Add Profile</button>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {[["All", undefined], ["Has Allergens", true], ["Allergen-Free", false]].map(([label, val]) => (
          <button key={String(label)} onClick={() => setFilter(val as boolean | undefined)} className={`px-3 py-1 text-xs rounded border ${filter === val ? "bg-gray-900 text-white border-gray-900" : "bg-white hover:bg-gray-50"}`}>{label as string}</button>
        ))}
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-sm font-medium text-gray-700">New / Update Material Allergen Profile</h2>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-1">
              <label className="text-xs text-gray-500">Material ID (UUID) *</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm font-mono" value={form.material_id} onChange={(e) => setForm((p) => ({ ...p, material_id: e.target.value }))} placeholder="material-uuid..." />
            </div>
            <div>
              <label className="text-xs text-gray-500">Cross-Contact Risk</label>
              <select className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.cross_contact_risk_level} onChange={(e) => setForm((p) => ({ ...p, cross_contact_risk_level: e.target.value }))}>
                {["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"].map((r) => <option key={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Review Date</label>
              <input type="date" className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.allergen_review_date} onChange={(e) => setForm((p) => ({ ...p, allergen_review_date: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Supplier Statement Ref</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.supplier_allergen_statement_ref} onChange={(e) => setForm((p) => ({ ...p, supplier_allergen_statement_ref: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Approved By</label>
              <input className="mt-0.5 w-full border rounded px-2 py-1.5 text-sm" value={form.approved_by} onChange={(e) => setForm((p) => ({ ...p, approved_by: e.target.value }))} />
            </div>
          </div>

          {/* Allergen Lines */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-gray-600 font-medium">Allergen Lines</p>
              <button
                onClick={() => setForm((p) => ({ ...p, lines: [...p.lines, { allergen_id: "", presence_type: "CONTAINS", declaration_required: true, critical_flag: false }] }))}
                className="text-xs text-blue-600 hover:underline"
              >+ Add Line</button>
            </div>
            <div className="space-y-2">
              {form.lines.map((line, i) => (
                <div key={i} className="flex items-center gap-2 bg-gray-50 rounded p-2">
                  <select className="flex-1 border rounded px-2 py-1 text-xs" value={line.allergen_id} onChange={(e) => {
                    const updated = [...form.lines];
                    updated[i] = { ...updated[i], allergen_id: e.target.value };
                    setForm((p) => ({ ...p, lines: updated }));
                  }}>
                    <option value="">Select allergen…</option>
                    {allergens?.map((a) => <option key={a.id} value={a.id}>{a.allergen_name}</option>)}
                  </select>
                  <select className="border rounded px-2 py-1 text-xs" value={line.presence_type} onChange={(e) => {
                    const updated = [...form.lines];
                    updated[i] = { ...updated[i], presence_type: e.target.value };
                    setForm((p) => ({ ...p, lines: updated }));
                  }}>
                    {["CONTAINS", "MAY_CONTAIN", "PRODUCED_IN_SAME_FACILITY", "FREE_FROM", "UNKNOWN"].map((t) => <option key={t}>{t}</option>)}
                  </select>
                  <label className="flex items-center gap-1 text-xs">
                    <input type="checkbox" checked={line.declaration_required} onChange={(e) => {
                      const updated = [...form.lines];
                      updated[i] = { ...updated[i], declaration_required: e.target.checked };
                      setForm((p) => ({ ...p, lines: updated }));
                    }} /> Declare
                  </label>
                  <label className="flex items-center gap-1 text-xs">
                    <input type="checkbox" checked={line.critical_flag} onChange={(e) => {
                      const updated = [...form.lines];
                      updated[i] = { ...updated[i], critical_flag: e.target.checked };
                      setForm((p) => ({ ...p, lines: updated }));
                    }} /> Critical
                  </label>
                  <button onClick={() => setForm((p) => ({ ...p, lines: p.lines.filter((_, idx) => idx !== i) }))} className="text-red-400 hover:text-red-600 text-xs">✕</button>
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <button onClick={() => create.mutate()} disabled={create.isPending || !form.material_id} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded disabled:opacity-50">Save Profile</button>
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-sm border rounded">Cancel</button>
          </div>
          {create.isError && <p className="text-red-600 text-xs">{(create.error as Error).message}</p>}
        </div>
      )}

      {/* Profiles Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>{["Material", "Contains", "May Contain", "Cross-Contact Risk", "Allergens", "Statement Ref", "Review Date"].map((h) => <th key={h} className="px-3 py-2 text-left">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!profiles?.length && <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">No allergen profiles yet</td></tr>}
            {profiles?.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => setSelected(p)}>
                <td className="px-3 py-2 font-medium">{p.material_name || p.material_id.slice(0, 8)}</td>
                <td className="px-3 py-2">{p.allergen_present_flag ? <span className="text-red-600 text-xs font-medium">YES</span> : <span className="text-gray-400 text-xs">—</span>}</td>
                <td className="px-3 py-2">{p.allergen_may_contain_flag ? <span className="text-orange-600 text-xs font-medium">YES</span> : <span className="text-gray-400 text-xs">—</span>}</td>
                <td className="px-3 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${riskColor[p.cross_contact_risk_level] || ""}`}>{p.cross_contact_risk_level}</span>
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {p.lines.slice(0, 3).map((l) => (
                      <span key={l.id} className={`text-xs px-1.5 py-0.5 rounded ${presenceColor[l.presence_type] || ""}`}>{l.allergen_name || l.allergen_id.slice(0, 8)}</span>
                    ))}
                    {p.lines.length > 3 && <span className="text-xs text-gray-400">+{p.lines.length - 3}</span>}
                  </div>
                </td>
                <td className="px-3 py-2 text-gray-500 text-xs">{p.supplier_allergen_statement_ref || "—"}</td>
                <td className="px-3 py-2 text-gray-400 text-xs">{p.allergen_review_date || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-lg p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-medium text-gray-900 mb-3">Allergen Profile — {selected.material_name}</h3>
            <div className="space-y-2">
              {selected.lines.map((l) => (
                <div key={l.id} className="flex items-center justify-between bg-gray-50 rounded p-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${presenceColor[l.presence_type] || ""}`}>{l.presence_type}</span>
                    <span className="font-medium">{l.allergen_name || l.allergen_id}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    {l.declaration_required && <span className="text-orange-600">Declare</span>}
                    {l.critical_flag && <span className="text-red-600 font-medium">Critical</span>}
                  </div>
                </div>
              ))}
              {selected.lines.length === 0 && <p className="text-gray-400 text-sm">No allergen lines</p>}
            </div>
            <button onClick={() => setSelected(null)} className="mt-3 px-3 py-1.5 text-sm border rounded">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
