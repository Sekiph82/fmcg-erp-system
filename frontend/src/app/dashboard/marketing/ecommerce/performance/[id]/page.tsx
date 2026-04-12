"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi, StorePerformance } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className="text-sm text-white">{value ?? <span className="text-slate-600">—</span>}</p>
    </div>
  );
}

export default function StorePerformanceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<StorePerformance>>({});
  const [error, setError] = useState("");

  const { data: record, isLoading } = useQuery({
    queryKey: ["store-perf", id],
    queryFn: () => marketingApi.storePerformance.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const { data: stores = [] } = useQuery({
    queryKey: ["stores-all"],
    queryFn: () => marketingApi.stores.list({ limit: 100 }).then((r) => r.data),
  });

  const storeName = stores.find((s) => s.id === record?.store_id)?.store_name ?? record?.store_id?.slice(0, 8);

  const updateMut = useMutation({
    mutationFn: () => marketingApi.storePerformance.update(id, form as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["store-perf", id] });
      qc.invalidateQueries({ queryKey: ["store-performance"] });
      setEditing(false);
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.storePerformance.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/ecommerce/performance"),
  });

  if (isLoading) return <div className="p-8 text-slate-400">Loading...</div>;
  if (!record) return <div className="p-8 text-red-400">Record not found.</div>;

  const roas = record.ad_spend && record.total_revenue
    ? Number(record.total_revenue) / Number(record.ad_spend)
    : null;

  return (
    <RequirePermission permission="store_performance.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-3xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Store Performance
          </button>
          <h1 className="text-2xl font-bold">{storeName} — {record.perf_date}</h1>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Revenue</p>
            <p className="text-lg font-bold text-sky-400">
              {record.total_revenue ? `KES ${Number(record.total_revenue).toLocaleString()}` : "—"}
            </p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Orders</p>
            <p className="text-lg font-bold">{record.total_orders.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Units</p>
            <p className="text-lg font-bold">{record.total_units_sold.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">ROAS</p>
            <p className={`text-lg font-bold ${roas == null ? "text-slate-400" : roas >= 3 ? "text-emerald-400" : roas >= 1 ? "text-yellow-400" : "text-red-400"}`}>
              {roas != null ? `${roas.toFixed(2)}x` : "—"}
            </p>
          </div>
        </div>

        {error && <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>}

        {!editing ? (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Performance Details</h2>
              <RequirePermission permission="store_performance.edit">
                <div className="flex gap-2">
                  <button onClick={() => { setForm({ ...record }); setEditing(true); }}
                    className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 text-sm">Edit</button>
                  <button onClick={() => { if (confirm("Delete this record?")) deleteMut.mutate(); }}
                    className="px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-sm">Delete</button>
                </div>
              </RequirePermission>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-4">
              <Field label="Store" value={storeName} />
              <Field label="Date" value={record.perf_date} />
              <Field label="Gross Margin" value={record.gross_margin ? `KES ${Number(record.gross_margin).toLocaleString()}` : null} />
              <Field label="Ad Spend" value={record.ad_spend ? `KES ${Number(record.ad_spend).toLocaleString()}` : null} />
              <Field label="Net Revenue" value={record.net_revenue ? `KES ${Number(record.net_revenue).toLocaleString()}` : null} />
              <Field label="Returns" value={record.returns_count} />
              <Field label="Impressions" value={record.impressions?.toLocaleString() ?? null} />
              <Field label="Clicks" value={record.clicks?.toLocaleString() ?? null} />
              <Field label="Conversions" value={record.conversions?.toLocaleString() ?? null} />
            </div>
            {record.notes && (
              <div className="mt-4 border-t border-slate-700/50 pt-3">
                <p className="text-xs text-slate-400 mb-1">Notes</p>
                <p className="text-sm text-slate-300">{record.notes}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Total Orders</label>
                <input type="number" min="0" value={String(form.total_orders ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, total_orders: parseInt(e.target.value) || 0 }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Units Sold</label>
                <input type="number" min="0" value={String(form.total_units_sold ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, total_units_sold: parseInt(e.target.value) || 0 }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Total Revenue</label>
                <input type="number" step="0.01" value={String(form.total_revenue ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, total_revenue: e.target.value || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Net Revenue</label>
                <input type="number" step="0.01" value={String(form.net_revenue ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, net_revenue: e.target.value || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Ad Spend</label>
                <input type="number" step="0.01" value={String(form.ad_spend ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, ad_spend: e.target.value || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Returns Count</label>
                <input type="number" min="0" value={String(form.returns_count ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, returns_count: parseInt(e.target.value) || 0 }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes</label>
              <textarea value={String(form.notes ?? "")}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value || null }))}
                rows={2}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none" />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setEditing(false)}
                className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
              <button onClick={() => updateMut.mutate()} disabled={updateMut.isPending}
                className="px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-sm font-medium">
                {updateMut.isPending ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
