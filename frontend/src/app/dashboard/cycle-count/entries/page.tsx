"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { listEntries, createEntry, CountEntry } from "@/lib/cycleCount";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

function EntriesContent() {
  const searchParams = useSearchParams();
  const taskId = searchParams.get("task_id") || "";

  const [entries, setEntries] = useState<CountEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<Record<string, string>>({ task_id: taskId, unit: "KG" });

  const load = useCallback(async () => {
    setLoading(true);
    try { setEntries(await listEntries(taskId ? { task_id: taskId } : undefined)); } catch {}
    setLoading(false);
  }, [taskId]);

  useEffect(() => { load(); }, [load]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(""); setSaving(true);
    try {
      await createEntry({
        task_id: form.task_id,
        counted_qty: Number(form.counted_qty),
        unit: form.unit,
        unit_cost: form.unit_cost ? Number(form.unit_cost) : undefined,
        root_cause: form.root_cause,
      });
      setShowForm(false); await load();
    } catch (err: unknown) {
      const e2 = err as { response?: { data?: { detail?: string } } };
      setError(e2?.response?.data?.detail || "Failed to record count");
    }
    setSaving(false);
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Count Entries</h1>
          <p className="text-sm text-gray-500 mt-1">
            {taskId ? `Task: ${taskId.slice(0, 8)}... · ` : ""}{entries.length} record(s)
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Record Count"}</Button>
      </div>

      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Record Physical Count</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <Input id="task" label="Task ID" value={form.task_id} onChange={(e) => setForm({ ...form, task_id: e.target.value })} required placeholder="UUID" />
            <Input id="qty" label="Counted Quantity" type="number" step="0.001" value={form.counted_qty || ""} onChange={(e) => setForm({ ...form, counted_qty: e.target.value })} required autoFocus />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })}>
                {["KG", "L", "PCS", "BOX", "CARTON"].map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
            <Input id="cost" label="Unit Cost (optional)" type="number" step="0.0001" value={form.unit_cost || ""} onChange={(e) => setForm({ ...form, unit_cost: e.target.value })} />
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Root Cause (if variance expected)</label>
              <textarea className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" rows={2} value={form.root_cause || ""} onChange={(e) => setForm({ ...form, root_cause: e.target.value })} />
            </div>
            {error && <div className="col-span-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}
            <div className="col-span-2 flex justify-end gap-3">
              <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button type="submit" loading={saving}>Save Count</Button>
            </div>
          </form>
        </div>
      )}

      {loading ? <div className="text-gray-500 py-8 text-center">Loading...</div> : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["System Qty", "Counted Qty", "Variance", "Variance %", "Value Impact", "Tolerance", "Counted At"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {entries.map((e) => (
                <tr key={e.id} className={`hover:bg-gray-50 ${!e.within_tolerance ? "bg-amber-50" : ""}`}>
                  <td className="px-4 py-3">{Number(e.system_qty).toFixed(3)} {e.unit}</td>
                  <td className="px-4 py-3 font-medium">{Number(e.counted_qty).toFixed(3)} {e.unit}</td>
                  <td className={`px-4 py-3 font-medium ${Number(e.variance_qty) < 0 ? "text-red-600" : Number(e.variance_qty) > 0 ? "text-amber-600" : "text-green-600"}`}>
                    {Number(e.variance_qty) > 0 ? "+" : ""}{Number(e.variance_qty).toFixed(3)}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{Number(e.variance_pct || 0).toFixed(2)}%</td>
                  <td className="px-4 py-3 text-gray-600">
                    {e.variance_value ? `KES ${Math.abs(Number(e.variance_value)).toLocaleString()}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${e.within_tolerance ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {e.within_tolerance ? "Within" : "Variance"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {e.counted_at ? new Date(e.counted_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
              {entries.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No count entries yet</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function EntriesPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-500">Loading...</div>}>
      <EntriesContent />
    </Suspense>
  );
}
