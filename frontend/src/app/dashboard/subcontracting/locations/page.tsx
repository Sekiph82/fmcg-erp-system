"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scApi } from "@/lib/subcontracting";

export default function LocationsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ supplier_id: "", warehouse_id: "", notes: "" });

  const { data, isLoading } = useQuery({ queryKey: ["sc-locations"], queryFn: scApi.listLocations });

  const create = useMutation({
    mutationFn: () => scApi.createLocation(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sc-locations"] }); setShowForm(false); setForm({ supplier_id: "", warehouse_id: "", notes: "" }); },
  });

  return (
    <div className="p-6 space-y-5">
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-96 space-y-3 shadow-xl">
            <h2 className="font-semibold">Create Subcontractor Location</h2>
            <p className="text-xs text-gray-500">A virtual warehouse representing the subcontractor's premises.</p>
            {[["Supplier ID","supplier_id"],["Warehouse ID","warehouse_id"],["Notes","notes"]].map(([label, key]) => (
              <div key={key}><label className="text-xs text-gray-600">{label}</label>
                <input value={(form as Record<string,string>)[key]} onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className="w-full border rounded px-2 py-1.5 text-sm mt-0.5" />
              </div>
            ))}
            <div className="flex gap-2 pt-2">
              <button onClick={() => create.mutate()} disabled={!form.supplier_id || !form.warehouse_id || create.isPending}
                className="flex-1 py-2 bg-blue-600 text-white rounded text-sm disabled:opacity-50">
                {create.isPending ? "Creating…" : "Create"}
              </button>
              <button onClick={() => setShowForm(false)} className="flex-1 py-2 border rounded text-sm hover:bg-gray-50">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Subcontractor Locations</h1>
          <p className="text-sm text-gray-500">Virtual warehouses representing external subcontractor sites</p>
        </div>
        <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700">
          + Add Location
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="text-left px-4 py-2">Supplier</th>
              <th className="text-left px-4 py-2">Virtual Warehouse</th>
              <th className="text-left px-4 py-2">Code</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>}
            {!isLoading && !data?.length && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                No locations configured. Create one to enable material tracking at subcontractor sites.
              </td></tr>
            )}
            {(data ?? []).map((l) => (
              <tr key={l.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{l.supplier_name ?? l.supplier_id}</td>
                <td className="px-4 py-2">{l.warehouse_name ?? l.warehouse_id}</td>
                <td className="px-4 py-2 font-mono text-gray-500">{l.warehouse_code ?? "—"}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${l.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {l.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-4 py-2 text-gray-500 text-xs">{l.notes ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
