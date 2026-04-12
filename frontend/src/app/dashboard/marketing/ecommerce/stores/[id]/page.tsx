"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marketingApi, MktStore, StorePlatform, StoreStatus, STORE_STATUS_COLORS } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: StorePlatform[] = [
  "JUMIA", "KILIMALL", "SHOPIFY", "WOOCOMMERCE", "AMAZON",
  "TIKTOK_SHOP", "INSTAGRAM_SHOP", "OTHER",
];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      <p className="text-sm text-white">{value ?? <span className="text-slate-600">—</span>}</p>
    </div>
  );
}

export default function StoreDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<MktStore>>({});
  const [error, setError] = useState("");

  const { data: store, isLoading } = useQuery({
    queryKey: ["store", id],
    queryFn: () => marketingApi.stores.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const { data: perfs = [] } = useQuery({
    queryKey: ["store-perf-by-store", id],
    queryFn: () => marketingApi.storePerformance.list({ store_id: id, limit: 10 }).then((r) => r.data),
    enabled: !!id,
  });

  const { data: stocks = [] } = useQuery({
    queryKey: ["channel-stock", id],
    queryFn: () => marketingApi.channelStock.list({ store_id: id }).then((r) => r.data),
    enabled: !!id,
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.stores.update(id, form as Record<string, unknown>),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["store", id] });
      qc.invalidateQueries({ queryKey: ["stores"] });
      setEditing(false);
    },
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.stores.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/ecommerce/stores"),
  });

  const startEdit = () => {
    if (!store) return;
    setForm({ ...store });
    setEditing(true);
  };

  if (isLoading) return <div className="p-8 text-slate-400">Loading...</div>;
  if (!store) return <div className="p-8 text-red-400">Store not found.</div>;

  const recentRevenue = perfs.slice(0, 7).reduce((s, p) => s + Number(p.total_revenue ?? 0), 0);
  const recentOrders = perfs.slice(0, 7).reduce((s, p) => s + p.total_orders, 0);

  return (
    <RequirePermission permission="ecommerce.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-4xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">
            ← E-commerce Stores
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">{store.store_name}</h1>
              <p className="text-slate-400 text-sm mt-1">
                {store.platform.replace(/_/g, " ")}
                {store.region && ` · ${store.region}`}
                {store.owner && ` · ${store.owner}`}
              </p>
            </div>
            <span className={`text-sm font-semibold ${STORE_STATUS_COLORS[store.status as StoreStatus]}`}>
              {store.status}
            </span>
          </div>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Revenue (7d)</p>
            <p className="text-lg font-bold text-sky-400">KES {recentRevenue.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">Orders (7d)</p>
            <p className="text-lg font-bold">{recentOrders.toLocaleString()}</p>
          </div>
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4">
            <p className="text-xs text-slate-400 mb-0.5">SKUs Allocated</p>
            <p className="text-lg font-bold">{stocks.length}</p>
          </div>
        </div>

        {error && <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Store details */}
          {!editing ? (
            <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Store Details</h2>
                <RequirePermission permission="ecommerce.edit">
                  <div className="flex gap-2">
                    <button onClick={startEdit}
                      className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 text-sm">Edit</button>
                    <button onClick={() => { if (confirm("Delete this store?")) deleteMut.mutate(); }}
                      className="px-3 py-1.5 rounded-lg bg-red-900/30 hover:bg-red-900/50 text-red-400 text-sm">Delete</button>
                  </div>
                </RequirePermission>
              </div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                <Field label="Platform" value={store.platform.replace(/_/g, " ")} />
                <Field label="Status" value={store.status} />
                <Field label="Region" value={store.region} />
                <Field label="Owner" value={store.owner} />
                <Field label="Created" value={store.created_at ? new Date(store.created_at).toLocaleDateString() : null} />
              </div>
              {store.url && (
                <div className="mt-4 border-t border-slate-700/50 pt-3">
                  <a href={store.url} target="_blank" rel="noreferrer"
                    className="text-sm text-sky-400 hover:text-sky-300 break-all">{store.url}</a>
                </div>
              )}
              {store.notes && (
                <div className="mt-3 border-t border-slate-700/50 pt-3">
                  <p className="text-xs text-slate-400 mb-1">Notes</p>
                  <p className="text-sm text-slate-300">{store.notes}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Store Name</label>
                <input type="text" value={String(form.store_name ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, store_name: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Platform</label>
                  <select value={String(form.platform ?? store.platform)}
                    onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value as StorePlatform }))}
                    className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                    {PLATFORMS.map((p) => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Status</label>
                  <select value={String(form.status ?? store.status)}
                    onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as StoreStatus }))}
                    className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                    {(["ACTIVE", "INACTIVE", "PENDING"] as StoreStatus[]).map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">URL</label>
                <input type="text" value={String(form.url ?? "")}
                  onChange={(e) => setForm((f) => ({ ...f, url: e.target.value || null }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white" />
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

          {/* Recent performance */}
          <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Recent Performance</h2>
              <button onClick={() => router.push(`/dashboard/marketing/ecommerce/performance/new?store_id=${id}`)}
                className="px-2 py-1 rounded bg-sky-600/20 hover:bg-sky-600/40 text-sky-400 text-xs">
                + Log
              </button>
            </div>
            {perfs.length === 0 ? (
              <p className="text-slate-500 text-sm">No performance records yet.</p>
            ) : (
              <div className="space-y-2">
                {perfs.slice(0, 5).map((p) => (
                  <div key={p.id} className="flex justify-between items-center py-2 border-b border-slate-800 last:border-0">
                    <div>
                      <p className="text-sm text-slate-300">{p.perf_date}</p>
                      <p className="text-xs text-slate-500">{p.total_orders} orders · {p.total_units_sold} units</p>
                    </div>
                    <p className="text-sm font-medium text-sky-400">
                      {p.total_revenue ? `KES ${Number(p.total_revenue).toLocaleString()}` : "—"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Channel stock */}
        {stocks.length > 0 && (
          <div className="mt-6 bg-[#131c2e] border border-slate-700/50 rounded-xl p-6">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Channel Stock</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700/50">
                    {["Product ID", "Allocated", "Reserved", "Available"].map((h) => (
                      <th key={h} className="text-left px-3 py-2 text-xs text-slate-400">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((s) => (
                    <tr key={s.id} className="border-b border-slate-800">
                      <td className="px-3 py-2 font-mono text-xs text-slate-400">{s.product_id.slice(0, 8)}…</td>
                      <td className="px-3 py-2">{Number(s.allocated_stock).toLocaleString()}</td>
                      <td className="px-3 py-2 text-yellow-400">{Number(s.reserved_stock).toLocaleString()}</td>
                      <td className="px-3 py-2 text-emerald-400">{Number(s.available_stock).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
