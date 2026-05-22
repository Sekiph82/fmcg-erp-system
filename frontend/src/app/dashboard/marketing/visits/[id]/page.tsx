"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { marketingApi } from "@/lib/marketingApi";
import { RequirePermission } from "@/components/PermissionGuard";

export default function VisitDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: visit, isLoading } = useQuery({
    queryKey: ["visit", id],
    queryFn: () => marketingApi.visits.get(id).then((r) => r.data),
    enabled: !!id,
  });

  const deleteMut = useMutation({
    mutationFn: () => marketingApi.visits.delete(id),
    onSuccess: () => router.push("/dashboard/marketing/visits"),
  });

  if (isLoading) return <div className="min-h-screen bg-[#0b1120] p-6 text-slate-400">Loading...</div>;
  if (!visit) return <div className="min-h-screen bg-[#0b1120] p-6 text-red-400">Visit not found.</div>;

  return (
    <RequirePermission permission="customer_visits.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white max-w-2xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <a href="/dashboard/marketing/visits" className="text-sm text-slate-400 hover:text-white mb-1 inline-block">
              ← Field Visits
            </a>
            <h1 className="text-2xl font-bold">Visit Detail</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-sm font-medium text-blue-400">{visit.visit_type.replace(/_/g, " ")}</span>
              <span className="text-sm text-slate-400">{visit.visit_date}</span>
              {visit.followup_required && (
                <span className="text-xs text-orange-400 font-medium bg-orange-400/10 px-2 py-0.5 rounded">Follow-up Required</span>
              )}
            </div>
          </div>
          <button
            onClick={() => { if (confirm("Delete this visit record?")) deleteMut.mutate(); }}
            className="mt-5 px-3 py-1.5 rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/40 text-sm font-medium transition-colors">
            Delete
          </button>
        </div>

        <div className="rounded-xl bg-[#131c2e] border border-slate-700/50 p-5 space-y-5">
          {/* Core details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-slate-500 mb-0.5">Customer ID</p>
              {visit.customer_id ? (
                <p className="font-mono text-xs">{visit.customer_id}</p>
              ) : "—"}
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-0.5">Employee ID</p>
              {visit.employee_id ? (
                <p className="font-mono text-xs">{visit.employee_id}</p>
              ) : "—"}
            </div>
            {visit.crm_profile_id && (
              <div>
                <p className="text-xs text-slate-500 mb-0.5">CRM Profile</p>
                <a href={`/dashboard/marketing/crm/${visit.crm_profile_id}`}
                  className="text-blue-400 hover:underline text-xs">
                  View Profile
                </a>
              </div>
            )}
          </div>

          {/* Purpose */}
          {visit.purpose && (
            <div className="border-t border-slate-700 pt-4">
              <p className="text-xs text-slate-500 mb-1">Purpose</p>
              <p className="text-sm text-slate-300">{visit.purpose}</p>
            </div>
          )}

          {/* Outcome */}
          {visit.outcome && (
            <div className="border-t border-slate-700 pt-4">
              <p className="text-xs text-slate-500 mb-1">Outcome</p>
              <p className="text-sm text-slate-300">{visit.outcome}</p>
            </div>
          )}

          {/* Field observations */}
          {(visit.display_observation || visit.stock_observation || visit.competitor_notes) && (
            <div className="border-t border-slate-700 pt-4 space-y-3">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Field Observations</p>
              {visit.display_observation && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Display Observation</p>
                  <p className="text-sm text-slate-300">{visit.display_observation}</p>
                </div>
              )}
              {visit.stock_observation && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Stock Observation</p>
                  <p className="text-sm text-slate-300">{visit.stock_observation}</p>
                </div>
              )}
              {visit.competitor_notes && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Competitor Notes</p>
                  <p className="text-sm text-slate-300">{visit.competitor_notes}</p>
                </div>
              )}
            </div>
          )}

          {/* Created at */}
          <div className="border-t border-slate-700 pt-4">
            <p className="text-xs text-slate-500">Logged: {visit.created_at ? new Date(visit.created_at).toLocaleString() : "—"}</p>
          </div>
        </div>
      </div>
    </RequirePermission>
  );
}
