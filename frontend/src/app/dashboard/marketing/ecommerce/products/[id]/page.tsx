"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi, ProductChannelPerformance } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className="text-sm text-white">{value ?? <span className="text-slate-600">—</span>}</p>
    </div>
  );
}

export default function ProductChannelPerfDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<ProductChannelPerformance>>({});
  const [error, setError] = useState("");

  const { data: record, isLoading } = useQuery({
    queryKey: ["channel-perf", id],
    queryFn: () => marketingApi.channelPerformance.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const { data: stores = [] } = useQuery({
    queryKey: ["stores-all"],
    queryFn: () => marketingApi.stores.list({ limit: 100 }).then((r) => r.data),
  });

  const storeName = stores.find((s) => s.id === record?.store_id)?.store_name ?? record?.store_id?.slice(0, 8);

  const updateMut = useMutation({
    mutationFn: () => marketingApi.channelPerformance.update(id, form as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channel-perf", id] });
      qc.invalidateQueries({ queryKey: ["product-channel-perf"] });
      setEditing(false);
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.channelPerformance.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/ecommerce/products"),
  });

  if (isLoading) return <div className="p-8 text-slate-400">Loading...</div>;
  if (!record) return <div className="p-8 text-red-400">Record not found.</div>;

  return (
    <RequirePermission permission="channel_products.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-3xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← Product Performance
          </button>
          <h1 className="text-2xl font-bold">Product {record.product_id.slice(0, 8)}… — {record.perf_date}</h1>
          <p className="text-slate-400 text-sm mt-1">{storeName}</p>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Revenue</p>
            <p className="text-lg font-bold text-emerald-400">
              {record.revenue ? `KES ${Number(record.revenue).toLocaleString()}` : "—"}
            </p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Units Sold</p>
            <p className="text-lg font-bold">{record.units_sold.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Conv. Rate</p>
            <p className="text-lg font-bold text-sky-400">
              {record.conversion_rate ? `${Number(record.conversion_rate).toFixed(1)}%` : "—"}
            </p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Return Rate</p>
            <p className={`text-lg font-bold ${record.return_rate && Number(record.return_rate) > 10 ? "text-red-400" : "text-slate-300"}`}>
              {record.return_rate ? `${Number(record.return_rate).toFixed(1)}%` : "—"}
            </p>
          </div>
        </div>

        {error && <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>}

        {!editing ? (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Performance Details</h2>
              <RequirePermission permission="channel_products.edit">
                <div className="flex gap-2">
                  <button onClick={() => { setForm({ ...record }); setEditing(true); }}
                    className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 text-sm">Edit</button>
                  <button onClick={() => { if (confirm("Delete this record?")) deleteMut.mutate(); }}
                    className="px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-sm">Delete</button>
                </div>
              </RequirePermission>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-4">
              <Field label="Product ID" value={<span className="font-mono text-xs">{record.product_id}</span>} />
              <Field label="Store" value={storeName} />
              <Field label="Date" value={record.perf_date} />
              <Field label="Impressions" value={record.impressions?.toLocaleString() ?? null} />
              <Field label="Clicks" value={record.clicks?.toLocaleString() ?? null} />
              <Field label="Ranking" value={record.ranking ? `#${record.ranking}` : null} />
              <Field label="Stock Level" value={record.stock_level?.toLocaleString() ?? null} />
            </div>
          </div>
        ) : (
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Units Sold</label>
                <input type="number" min="0" value={String(form.units_sold ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, units_sold: parseInt(e.target.value) || 0 }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Revenue</label>
                <input type="number" step="0.01" value={String(form.revenue ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, revenue: e.target.value || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Impressions</label>
                <input type="number" min="0" value={String(form.impressions ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, impressions: parseInt(e.target.value) || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Clicks</label>
                <input type="number" min="0" value={String(form.clicks ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, clicks: parseInt(e.target.value) || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Conversion Rate (%)</label>
                <input type="number" step="0.01" value={String(form.conversion_rate ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, conversion_rate: e.target.value || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Return Rate (%)</label>
                <input type="number" step="0.01" value={String(form.return_rate ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, return_rate: e.target.value || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Ranking</label>
                <input type="number" min="1" value={String(form.ranking ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, ranking: parseInt(e.target.value) || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Stock Level</label>
                <input type="number" min="0" value={String(form.stock_level ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, stock_level: parseInt(e.target.value) || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setEditing(false)}
                className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
              <button onClick={() => updateMut.mutate()} disabled={updateMut.isPending}
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-sm font-medium">
                {updateMut.isPending ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
