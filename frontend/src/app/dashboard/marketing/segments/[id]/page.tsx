"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { marketingApi, SegmentType } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

const SEGMENT_TYPES: SegmentType[] = [
  "RETAIL", "WHOLESALE", "KIOSK", "SUPERMARKET", "DISTRIBUTOR",
  "HORECA", "PHARMACY", "MODERN_TRADE", "GENERAL_TRADE", "ONLINE",
];

export default function SegmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Record<string, unknown>>({});
  const [saveError, setSaveError] = useState("");

  const { data: segment, isLoading } = useQuery({
    queryKey: ["segment", id],
    queryFn: () => marketingApi.segments.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const updateMut = useMutation({
    mutationFn: () => marketingApi.segments.update(id, editForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["segment", id] });
      qc.invalidateQueries({ queryKey: ["segments"] });
      setEditing(false);
    },
    onError: (err: unknown) => {
      setSaveError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Save failed.");
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.segments.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/segments"),
  });

  function startEdit() {
    if (!segment) return;
    setEditForm({
      segment_name:  segment.segment_name,
      segment_type:  segment.segment_type,
      region:        segment.region ?? "",
      description:   segment.description ?? "",
      is_active:     segment.is_active,
    });
    setEditing(true);
  }

  if (isLoading) return <div className="min-h-screen bg-[#0b1120] p-6 text-slate-400">Loading...</div>;
  if (!segment) return <div className="min-h-screen bg-[#0b1120] p-6 text-red-400">Segment not found.</div>;

  return (
    <RequirePermission permission="segments.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <a href="/dashboard/marketing/segments" className="text-sm text-slate-400 hover:text-white mb-1 inline-block">
              ← Segments
            </a>
            <h1 className="text-2xl font-bold">{segment.segment_name}</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-xs text-blue-400">{segment.segment_type.replace(/_/g, " ")}</span>
              {segment.region && <span className="text-xs text-slate-400">{segment.region}</span>}
              <span className={`text-xs font-medium ${segment.is_active ? "text-emerald-400" : "text-slate-400"}`}>
                {segment.is_active ? "Active" : "Inactive"}
              </span>
            </div>
          </div>
          {!editing && (
            <div className="flex gap-2 mt-5">
              <button onClick={startEdit}
                className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
                Edit
              </button>
              <button onClick={() => { if (confirm("Delete this segment?")) deleteMut.mutate(); }}
                className="px-3 py-1.5 rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/40 text-sm font-medium transition-colors">
                Delete
              </button>
            </div>
          )}
        </div>

        {/* View mode */}
        {!editing && (
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5 space-y-4">
            {segment.description ? (
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Description</p>
                <p className="text-sm text-slate-300">{segment.description}</p>
              </div>
            ) : (
              <p className="text-sm text-slate-500 italic">No description provided.</p>
            )}
            <div className="grid grid-cols-2 gap-4 text-sm pt-2 border-t border-slate-700">
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Created</p>
                <p>{segment.created_at ? new Date(segment.created_at).toLocaleDateString() : "—"}</p>
              </div>
            </div>
          </div>
        )}

        {/* Edit mode */}
        {editing && (
          <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-6 space-y-4">
            {saveError && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400 text-sm">{saveError}</div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-xs text-slate-400 mb-1">Segment Name</label>
                <input
                  value={editForm.segment_name as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, segment_name: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Type</label>
                <select
                  value={editForm.segment_type as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, segment_type: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                >
                  {SEGMENT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Region</label>
                <input
                  value={editForm.region as string ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, region: e.target.value }))}
                  className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Description</label>
              <textarea
                value={editForm.description as string ?? ""}
                onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
                rows={3}
                className="w-full bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white resize-none"
              />
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="edit_is_active"
                checked={editForm.is_active as boolean ?? true}
                onChange={(e) => setEditForm((f) => ({ ...f, is_active: e.target.checked }))}
                className="w-4 h-4 rounded border-slate-700"
              />
              <label htmlFor="edit_is_active" className="text-sm text-slate-300">Active</label>
            </div>

            <div className="flex gap-3 pt-2">
              <button onClick={() => updateMut.mutate()} disabled={updateMut.isPending}
                className="px-5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium disabled:opacity-50 transition-colors">
                {updateMut.isPending ? "Saving..." : "Save Changes"}
              </button>
              <button onClick={() => setEditing(false)}
                className="px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm font-medium transition-colors">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </RequirePermission>
  );
}
