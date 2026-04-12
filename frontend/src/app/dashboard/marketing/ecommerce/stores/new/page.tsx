"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { marketingApi, StorePlatform, StoreStatus } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const PLATFORMS: StorePlatform[] = [
  "JUMIA", "KILIMALL", "SHOPIFY", "WOOCOMMERCE", "AMAZON",
  "TIKTOK_SHOP", "INSTAGRAM_SHOP", "OTHER",
];

export default function NewStorePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    store_name: "",
    platform: "SHOPIFY" as StorePlatform,
    region: "",
    url: "",
    owner: "",
    status: "ACTIVE" as StoreStatus,
    notes: "",
  });
  const [error, setError] = useState("");

  const createMut = useMutation({
    mutationFn: () =>
      marketingApi.stores.create({
        store_name: form.store_name,
        platform: form.platform,
        region: form.region || null,
        url: form.url || null,
        owner: form.owner || null,
        status: form.status,
        notes: form.notes || null,
      }),
    onSuccess: (r) => router.push(`/dashboard/marketing/ecommerce/stores/${r.data.id}`),
    onError: (e: unknown) => setError(String((e as { message?: string }).message ?? e)),
  });

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <RequirePermission permission="ecommerce.edit">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl mx-auto">
        <div className="mb-6">
          <button onClick={() => router.back()} className="text-slate-400 hover:text-white text-sm mb-2">← Back</button>
          <h1 className="text-2xl font-bold">Add Store / Channel</h1>
        </div>

        {error && <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-300 text-sm">{error}</div>}

        <div className="bg-[#131c2e] border border-slate-700/50 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Store Name *</label>
            <input type="text" value={form.store_name} onChange={(e) => set("store_name", e.target.value)}
              placeholder="e.g. Jumia Kenya Store"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Platform *</label>
              <select value={form.platform} onChange={(e) => set("platform", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {PLATFORMS.map((p) => <option key={p} value={p}>{p.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Status</label>
              <select value={form.status} onChange={(e) => set("status", e.target.value)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                {(["ACTIVE", "INACTIVE", "PENDING"] as StoreStatus[]).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Region</label>
              <input type="text" value={form.region} onChange={(e) => set("region", e.target.value)}
                placeholder="Kenya, East Africa…"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Owner / Manager</label>
              <input type="text" value={form.owner} onChange={(e) => set("owner", e.target.value)}
                placeholder="Name or team"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Store URL</label>
            <input type="text" value={form.url} onChange={(e) => set("url", e.target.value)}
              placeholder="https://store.example.com"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600" />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Notes</label>
            <textarea value={form.notes} onChange={(e) => set("notes", e.target.value)}
              rows={2} placeholder="Context, login info location, SLA notes…"
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none" />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => router.back()}
              className="px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-800 text-sm">Cancel</button>
            <button onClick={() => createMut.mutate()}
              disabled={!form.store_name || createMut.isPending}
              className="px-5 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-sm font-medium">
              {createMut.isPending ? "Saving..." : "Add Store"}
            </button>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
