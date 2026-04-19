"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { planningApi, ChangeoverRow } from "@/lib/planning";

interface WorkCenter { id: string; name: string; }

export default function ChangeoverPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    work_center_id: "",
    from_family: "",
    to_family: "",
    changeover_minutes: "",
    notes: "",
  });
  const [filterWC, setFilterWC] = useState("");

  const { data: matrix = [] } = useQuery<ChangeoverRow[]>({
    queryKey: ["changeover-matrix", filterWC],
    queryFn: () => planningApi.listChangeover(filterWC || undefined) as Promise<ChangeoverRow[]>,
  });

  const createRow = useMutation({
    mutationFn: () => planningApi.createChangeover({
      work_center_id: form.work_center_id,
      from_family: form.from_family.toUpperCase(),
      to_family: form.to_family.toUpperCase(),
      changeover_minutes: Number(form.changeover_minutes),
      notes: form.notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["changeover-matrix"] });
      setShowForm(false);
      setForm({ work_center_id: "", from_family: "", to_family: "", changeover_minutes: "", notes: "" });
    },
  });

  // Build unique product families from matrix
  const families = Array.from(new Set([...matrix.map((r) => r.from_family), ...matrix.map((r) => r.to_family)])).sort();

  // Build grid: rows = from_family, cols = to_family
  const grid: Record<string, Record<string, number | null>> = {};
  for (const f of families) {
    grid[f] = {};
    for (const t of families) {
      grid[f][t] = null;
    }
  }
  for (const row of matrix) {
    if (!grid[row.from_family]) grid[row.from_family] = {};
    grid[row.from_family][row.to_family] = row.changeover_minutes;
  }

  function cellColor(mins: number | null): string {
    if (mins == null) return "bg-gray-50 text-gray-300";
    if (mins === 0) return "bg-green-50 text-green-600";
    if (mins <= 30) return "bg-yellow-50 text-yellow-700";
    if (mins <= 60) return "bg-orange-50 text-orange-700";
    return "bg-red-50 text-red-700";
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Changeover Matrix</h1>
        <div className="flex items-center gap-3">
          <a href="/dashboard/planning" className="text-xs text-blue-600 hover:underline">← Planning Dashboard</a>
          <button
            onClick={() => setShowForm(true)}
            className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700"
          >
            + Add Entry
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>Changeover time:</span>
        {[["0 min", "bg-green-200"], ["≤30 min", "bg-yellow-200"], ["≤60 min", "bg-orange-200"], [">60 min", "bg-red-200"]].map(([l, c]) => (
          <div key={l} className="flex items-center gap-1">
            <div className={`w-3 h-3 rounded ${c}`} />
            <span>{l}</span>
          </div>
        ))}
      </div>

      {/* Flat table */}
      {matrix.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center text-sm text-gray-400">
          No changeover rules defined. Add entries to define transition times between product families.
        </div>
      ) : (
        <>
          {/* Grid view */}
          {families.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-50">
                <h2 className="text-sm font-semibold text-gray-700">Transition Matrix (minutes)</h2>
                <p className="text-xs text-gray-400 mt-0.5">Rows = FROM family · Columns = TO family</p>
              </div>
              <div className="overflow-x-auto p-4">
                <table className="text-xs border-collapse">
                  <thead>
                    <tr>
                      <th className="px-3 py-2 text-left text-gray-400 font-medium">FROM \ TO</th>
                      {families.map((f) => (
                        <th key={f} className="px-3 py-2 text-center text-gray-600 font-semibold min-w-[80px]">{f}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {families.map((from) => (
                      <tr key={from}>
                        <td className="px-3 py-2 font-semibold text-gray-700">{from}</td>
                        {families.map((to) => {
                          const mins = from === to ? 0 : (grid[from]?.[to] ?? null);
                          return (
                            <td key={to} className={`px-3 py-2 text-center rounded ${cellColor(mins)}`}>
                              {from === to ? <span className="text-gray-300">—</span> : mins != null ? `${mins}m` : "?"}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Flat list */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">All Entries ({matrix.length})</h2>
            </div>
            <table className="w-full text-xs">
              <thead className="bg-gray-50">
                <tr>
                  {["Work Center", "From Family", "To Family", "Minutes", "Notes"].map((h) => (
                    <th key={h} className="px-4 py-2 text-left font-medium text-gray-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {matrix.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-500 font-mono text-xs">{row.work_center_id.slice(0, 8)}…</td>
                    <td className="px-4 py-2 font-semibold text-gray-700">{row.from_family}</td>
                    <td className="px-4 py-2 font-semibold text-gray-700">{row.to_family}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded font-medium ${cellColor(row.changeover_minutes)}`}>
                        {row.changeover_minutes}m
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-400">{row.notes || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Add form modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Add Changeover Rule</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500">Work Center ID (UUID)</label>
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-1"
                  placeholder="e.g. 550e8400-e29b-41d4-a716-…"
                  value={form.work_center_id}
                  onChange={(e) => setForm({ ...form, work_center_id: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500">From Family (e.g. MILK)</label>
                  <input
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-1"
                    placeholder="MILK"
                    value={form.from_family}
                    onChange={(e) => setForm({ ...form, from_family: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">To Family</label>
                  <input
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-1"
                    placeholder="JUICE"
                    value={form.to_family}
                    onChange={(e) => setForm({ ...form, to_family: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500">Changeover minutes</label>
                <input
                  type="number"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-1"
                  placeholder="45"
                  value={form.changeover_minutes}
                  onChange={(e) => setForm({ ...form, changeover_minutes: e.target.value })}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Notes (optional)</label>
                <input
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mt-1"
                  placeholder="Clean-in-place required"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => createRow.mutate()}
                disabled={!form.work_center_id || !form.from_family || !form.to_family || !form.changeover_minutes || createRow.isPending}
                className="flex-1 bg-indigo-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-40"
              >
                {createRow.isPending ? "Saving…" : "Save"}
              </button>
              <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
