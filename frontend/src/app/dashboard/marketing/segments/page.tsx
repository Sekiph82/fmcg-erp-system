"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { marketingApi, CustomerSegment, SegmentType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const SEGMENT_TYPES: SegmentType[] = [
  "RETAIL", "WHOLESALE", "KIOSK", "SUPERMARKET", "DISTRIBUTOR",
  "HORECA", "PHARMACY", "MODERN_TRADE", "GENERAL_TRADE", "ONLINE",
];

export default function SegmentsPage() {
  const qc = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");

  const { data: segments = [], isLoading } = useQuery({
    queryKey: ["segments", typeFilter],
    queryFn: () =>
      marketingApi.segments
        .list({ segment_type: typeFilter || undefined, limit: 200 })
        .then((r) => r.data),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => marketingApi.segments.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["segments"] }),
  });

  return (
    <RequirePermission permission="segments.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Customer Segments</h1>
            <p className="text-slate-400 text-sm mt-1">{segments.length} segments</p>
          </div>
          <Link href="/dashboard/marketing/segments/new"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium transition-colors">
            + New Segment
          </Link>
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6 flex-wrap">
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-[#131c2e] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="">All types</option>
            {SEGMENT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>

        {isLoading ? (
          <p className="text-slate-400">Loading...</p>
        ) : segments.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-slate-400 mb-4">No segments found.</p>
            <Link href="/dashboard/marketing/segments/new"
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium">
              Create your first segment
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {segments.map((s: CustomerSegment) => (
              <div key={s.id} className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-4 hover:border-slate-600 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <Link href={`/dashboard/marketing/segments/${s.id}`}
                      className="font-semibold text-white hover:text-blue-400 truncate block">
                      {s.segment_name}
                    </Link>
                    <p className="text-xs text-blue-400 mt-0.5">{s.segment_type.replace(/_/g, " ")}</p>
                  </div>
                  <div className="flex gap-1.5 ml-2">
                    <Link href={`/dashboard/marketing/segments/${s.id}`}
                      className="px-2 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 text-xs">
                      View
                    </Link>
                    <button
                      onClick={() => { if (confirm(`Delete "${s.segment_name}"?`)) deleteMut.mutate(s.id); }}
                      className="px-2 py-1 rounded bg-red-600/20 text-red-400 hover:bg-red-600/40 text-xs">
                      Del
                    </button>
                  </div>
                </div>
                {s.region && <p className="text-xs text-slate-500 mb-1">{s.region}</p>}
                {s.description && <p className="text-xs text-slate-400 mb-2 line-clamp-2">{s.description}</p>}
                <div className="flex items-center gap-2 mt-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${s.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-700 text-slate-400"}`}>
                    {s.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
