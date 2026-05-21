"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { marketingApi, SegmentType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const SEGMENT_TYPES: SegmentType[] = [
  "RETAIL", "WHOLESALE", "KIOSK", "SUPERMARKET", "DISTRIBUTOR",
  "HORECA", "PHARMACY", "MODERN_TRADE", "GENERAL_TRADE", "ONLINE",
];

export default function NewSegmentPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [form, setForm] = useState({
    segment_name: "",
    segment_type: "RETAIL" as SegmentType,
    region: "",
    description: "",
    is_active: true,
  });
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: () =>
      marketingApi.segments.create({
        segment_name:  form.segment_name,
        segment_type:  form.segment_type,
        region:        form.region || undefined,
        description:   form.description || undefined,
        is_active:     form.is_active,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["segments"] });
      router.push(`/dashboard/marketing/segments/${res.data.id}`);
    },
    onError: (err: unknown) => {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create segment.");
    },
  });

  function set(key: string, val: string | boolean) {
    setForm((f) => ({ ...f, [key]: val }));
    setError("");
  }

  return (
    <RequirePermission permission="segments.create">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-xl">
        <div className="mb-6">
          <a href="/dashboard/marketing/segments" className="text-sm text-slate-400 hover:text-white mb-2 inline-block">
            ← Back to Segments
          </a>
          <h1 className="text-2xl font-bold">New Segment</h1>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">{error}</div>
        )}

        <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-xs text-slate-400 mb-1">Segment Name *</label>
              <input
                value={form.segment_name}
                onChange={(e) => set("segment_name", e.target.value)}
                placeholder="e.g. Nairobi Supermarkets"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Segment Type *</label>
              <select
                value={form.segment_type}
                onChange={(e) => set("segment_type", e.target.value as SegmentType)}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                {SEGMENT_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Region</label>
              <input
                value={form.region}
                onChange={(e) => set("region", e.target.value)}
                placeholder="e.g. Nairobi, Western Kenya"
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              rows={3}
              placeholder="Describe this segment..."
              className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 resize-none"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={(e) => set("is_active", e.target.checked)}
              className="w-4 h-4 rounded border-slate-700"
            />
            <label htmlFor="is_active" className="text-sm text-slate-300">Active</label>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={() => mut.mutate()}
              disabled={mut.isPending || !form.segment_name}
              className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {mut.isPending ? "Creating..." : "Create Segment"}
            </button>
            <a href="/dashboard/marketing/segments"
              className="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
              Cancel
            </a>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
