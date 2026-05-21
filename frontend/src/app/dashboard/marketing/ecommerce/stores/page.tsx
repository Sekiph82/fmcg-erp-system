"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { marketingApi, MktStore, StorePlatform, StoreStatus, STORE_STATUS_COLORS } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: StorePlatform[] = [
  "JUMIA", "KILIMALL", "SHOPIFY", "WOOCOMMERCE", "AMAZON",
  "TIKTOK_SHOP", "INSTAGRAM_SHOP", "OTHER",
];
const STATUSES: StoreStatus[] = ["ACTIVE", "INACTIVE", "PENDING"];

export default function EcommerceStoresPage() {
  const router = useRouter();
  const [platform, setPlatform] = useState("");
  const [status, setStatus] = useState("");

  const { data: stores = [], isLoading } = useQuery({
    queryKey: ["stores", platform, status],
    queryFn: () =>
      marketingApi.stores
        .list({ limit: 100, platform: platform || undefined, status: status || undefined })
        .then((r) => r.data),
  });

  return (
    <RequirePermission permission="ecommerce.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">E-commerce Stores</h1>
            <p className="text-slate-400 text-sm mt-1">{stores.length} stores connected</p>
          </div>
          <RequirePermission permission="stores.create">
            <button onClick={() => router.push("/dashboard/marketing/ecommerce/stores/new")}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-sm font-medium">
              + Add Store
            </button>
          </RequirePermission>
        </div>

        <div className="flex gap-3 mb-6 flex-wrap">
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All platforms</option>
            {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <select value={status} onChange={(e) => setStatus(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : stores.length === 0 ? (
          <p className="text-slate-400 text-center py-16">No stores found.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stores.map((s: MktStore) => (
              <div key={s.id} className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-white">{s.store_name}</p>
                  <span className={`font-medium text-xs ${STORE_STATUS_COLORS[s.status as StoreStatus]}`}>{s.status}</span>
                </div>
                <div className="flex gap-2 items-center">
                  <span className="px-2 py-0.5 rounded bg-sky-600/20 text-sky-300 text-xs font-medium">{s.platform}</span>
                  {s.region && <span className="text-xs text-slate-400">{s.region}</span>}
                </div>
                {s.url && (
                  <a href={s.url} target="_blank" rel="noreferrer"
                    className="text-xs text-blue-400 hover:underline truncate">{s.url}</a>
                )}
                {s.owner && <p className="text-xs text-slate-500">Owner: {s.owner}</p>}
                <div className="mt-auto pt-1">
                  <button onClick={() => router.push(`/dashboard/marketing/ecommerce/stores/${s.id}`)}
                    className="text-xs text-sky-400 hover:text-sky-300">View →</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
