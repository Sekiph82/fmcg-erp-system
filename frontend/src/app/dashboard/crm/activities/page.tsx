"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, CRMActivity, ACTIVITY_TYPE_LABELS, ACTIVITY_RESULT_LABELS } from "@/lib/crm_pipeline";

const RESULT_COLORS: Record<string, string> = {
  PLANNED: "#3B82F6",
  COMPLETED: "#10B981",
  NO_RESPONSE: "#F59E0B",
  RESCHEDULED: "#8B5CF6",
  CANCELLED: "#6B7280",
};

export default function ActivitiesPage() {
  const [activities, setActivities] = useState<CRMActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");

  const load = () => {
    setLoading(true);
    crmApi.getActivities({
      result_status: statusFilter || undefined,
      overdue_only: overdueOnly || undefined,
    }).then(setActivities).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter, overdueOnly]);

  const filtered = typeFilter ? activities.filter(a => a.activity_type === typeFilter) : activities;

  const handleComplete = async (actId: string) => {
    try {
      await crmApi.completeActivity(actId, { result_status: "COMPLETED" });
      load();
    } catch (e) { console.error(e); }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Activity Timeline</h1>
        <span className="text-sm text-gray-500">{filtered.length} activities</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={overdueOnly} onChange={e => setOverdueOnly(e.target.checked)}
            className="rounded" />
          Overdue Only
        </label>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Statuses</option>
          {Object.entries(ACTIVITY_RESULT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="text-sm border rounded-lg px-2 py-1.5">
          <option value="">All Types</option>
          {Object.entries(ACTIVITY_TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {/* Timeline */}
      <div className="relative space-y-3">
        {loading && <div className="text-gray-400 py-6 text-center">Loading…</div>}
        {!loading && filtered.length === 0 && <div className="text-gray-400 py-6 text-center">No activities</div>}
        {filtered.map((act, i) => {
          const isOverdue = act.result_status === "PLANNED" && act.due_datetime && new Date(act.due_datetime) < new Date();
          return (
            <div key={act.id} className={`bg-white rounded-xl border shadow-sm p-4 flex gap-4 ${isOverdue ? "border-red-200 bg-red-50" : ""}`}>
              {/* Icon */}
              <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold text-white"
                style={{ background: RESULT_COLORS[act.result_status] || "#6B7280" }}>
                {ACTIVITY_TYPE_LABELS[act.activity_type]?.slice(0, 2).toUpperCase()}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-medium text-gray-800 text-sm">{act.subject}</div>
                    <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2 flex-wrap">
                      <span>{ACTIVITY_TYPE_LABELS[act.activity_type]}</span>
                      <span>·</span>
                      <span style={{ color: RESULT_COLORS[act.result_status] }}>{ACTIVITY_RESULT_LABELS[act.result_status]}</span>
                      {act.assigned_to && <><span>·</span><span>Rep: {act.assigned_to}</span></>}
                      {act.due_datetime && (
                        <>
                          <span>·</span>
                          <span className={isOverdue ? "text-red-600 font-medium" : ""}>
                            Due: {new Date(act.due_datetime).toLocaleDateString()}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <Link href={`/dashboard/crm/records/${act.crm_record_id}`}
                    className="text-xs text-blue-600 hover:underline flex-shrink-0">
                    View Record
                  </Link>
                </div>
                {act.description && <p className="text-xs text-gray-600 mt-1.5">{act.description}</p>}
                {act.next_step && <p className="text-xs text-indigo-600 mt-1">→ Next: {act.next_step}</p>}
                {act.outcome_code && <p className="text-xs text-gray-500 mt-1">Outcome: {act.outcome_code}</p>}
              </div>

              {/* Actions */}
              {act.result_status === "PLANNED" && (
                <button onClick={() => handleComplete(act.id)}
                  className="flex-shrink-0 text-xs text-green-600 hover:underline self-start mt-1">
                  Complete
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
