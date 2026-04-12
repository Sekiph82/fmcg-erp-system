"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

export default function ReturnsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [storeId, setStoreId] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    product_id: "",
    store_id: "",
    return_date: new Date().toISOString().slice(0, 10),
    return_reason: "",
    return_count: "1",
    return_rate: "",
    notes: "",
  });
  const [error, setError] = useState("");

  const { data: stores = [] } = useQuery({
    queryKey: ["stores-all"],
    queryFn: () => marketingApi.stores.list({ limit: 100 }).then((r) => r.data),
  });

  const { data: records = [], isLoading } = useQuery({
    queryKey: ["returns", storeId],
    queryFn: () =>
      marketingApi.returns.list({ limit: 200, store_id: storeId || undefined }).then((r) => r.data),
  });

  const totalReturns = records.reduce((s, r) => s + r.return_count, 0);

  const createMut = useMutation({
    mutationFn: () =>
      marketingApi.returns.create({
        product_id: form.product_id,
        store_id: form.store_id || null,
        return_date: form.return_date,
        return_reason: form.return_reason || null,
        return_count: parseInt(form.return_count) || 1,
        return_rate: form.return_rate || null,
        notes: form.notes || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["returns"] });
      setShowForm(false);
      setForm({
        product_id: "", store_id: "", return_date: new Date().toISOString().slice(0, 10),
        return_reason: "", return_count: "1", return_rate: "", notes: "",
      });
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => marketingApi.returns.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["returns"] }),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const storeName = (id: string) => stores.find((s) => s.id === id)?.store_name ?? id.slice(0, 8);

  return (
    <RequirePermission permission="ecommerce.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">Return &amp; Feedback Analysis</h1>
            <p className="text-slate-400 text-sm mt-1">{records.length} records · {totalReturns} total returns</p>
          </div>
          <RequirePermission permission="ecommerce.edit">
            <button onClick={() => setShowForm((v) => !v)}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-sm font-medium">
              + Log Return
            </button>
          </RequirePermission>
        </div>

        {/* Log return form */}
        {showForm && (
          <div className="mb-6 bg-[#131c2e] border border-slate-700/50 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-300">Log Return Entry</h3>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Product ID *</label>
                <input type="text" value={form.product_id} onChange={(e) => set("product_id", e.target.value)}
                  placeholder="Product UUID"
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Store</label>
                <select value={form.store_id} onChange={(e) => set("store_id", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  <option value="">No specific store</option>
                  {stores.map((s) => <option key={s.id} value={s.id}>{s.store_name}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Date *</label>
                <input type="date" value={form.return_date} onChange={(e) => set("return_date", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Return Count</label>
                <input type="number" min="1" value={form.return_count} onChange={(e) => set("return_count", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Return Rate (%)</label>
                <input type="number" step="0.01" value={form.return_rate} onChange={(e) => set("return_rate", e.target.value)}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Return Reason</label>
              <input type="text" value={form.return_reason} onChange={(e) => set("return_reason", e.target.value)}
                placeholder="Damaged, Wrong item, Not as described…"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes</label>
              <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
                rows={2}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowForm(false)}
                className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
              <button onClick={() => createMut.mutate()}
                disabled={!form.product_id || createMut.isPending}
                className="px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-sm font-medium">
                {createMut.isPending ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex gap-3 mb-4">
          <select value={storeId} onChange={(e) => setStoreId(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All stores</option>
            {stores.map((s) => <option key={s.id} value={s.id}>{s.store_name}</option>)}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : records.length === 0 ? (
          <p className="text-slate-500 text-center py-16">No return records found.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-700/50">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50 bg-[#131c2e]">
                  {["Date", "Product ID", "Store", "Reason", "Count", "Rate", ""].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id} className="border-b border-slate-800 hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-slate-300">{r.return_date}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{r.product_id.slice(0, 8)}…</td>
                    <td className="px-4 py-3 text-slate-300">{r.store_id ? storeName(r.store_id) : "—"}</td>
                    <td className="px-4 py-3 text-slate-300">{r.return_reason ?? "—"}</td>
                    <td className="px-4 py-3 text-red-400 font-medium">{r.return_count}</td>
                    <td className="px-4 py-3 text-slate-300">
                      {r.return_rate ? `${Number(r.return_rate).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => router.push(`/dashboard/marketing/ecommerce/returns/${r.id}`)}
                        className="text-sky-400 hover:text-sky-300 text-xs">View</button>
                      <RequirePermission permission="ecommerce.edit">
                        <button onClick={() => { if (confirm("Delete this return record?")) deleteMut.mutate(r.id); }}
                          className="ml-3 text-red-400 hover:text-red-300 text-xs">Delete</button>
                      </RequirePermission>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
