"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, CRMActivity, ACTIVITY_TYPE_LABELS } from "@/lib/crm_pipeline";

export default function OverdueQueuePage() {
  const [activities, setActivities] = useState<CRMActivity[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    crmApi.getActivities({ overdue_only: true, limit: 200 })
      .then(setActivities).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleComplete = async (actId: string) => {
    try {
      await crmApi.completeActivity(actId, { result_status: "COMPLETED" });
      load();
    } catch (e) { console.error(e); }
  };

  const handleReschedule = async (actId: string) => {
    try {
      await crmApi.completeActivity(actId, { result_status: "RESCHEDULED" });
      load();
    } catch (e) { console.error(e); }
  };

  const daysOverdue = (due: string) => {
    const diff = Date.now() - new Date(due).getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Overdue Follow-Up Queue</h1>
          <p className="text-sm text-gray-500 mt-0.5">Planned activities past their due date</p>
        </div>
        <div className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-semibold">
          {activities.length} overdue
        </div>
      </div>

      {loading && <div className="text-gray-400 py-6 text-center">Loading…</div>}
      {!loading && activities.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
          <div className="text-green-700 font-semibold">No overdue activities!</div>
          <div className="text-sm text-gray-500 mt-1">Your follow-up queue is clear.</div>
        </div>
      )}

      <div className="space-y-2">
        {activities.map(act => {
          const days = act.due_datetime ? daysOverdue(act.due_datetime) : 0;
          const urgency = days > 7 ? "critical" : days > 3 ? "high" : "medium";
          const urgencyColors = {
            critical: { bg: "bg-red-50 border-red-300", text: "text-red-700", badge: "bg-red-100 text-red-700" },
            high: { bg: "bg-orange-50 border-orange-200", text: "text-orange-700", badge: "bg-orange-100 text-orange-700" },
            medium: { bg: "bg-yellow-50 border-yellow-200", text: "text-yellow-700", badge: "bg-yellow-100 text-yellow-700" },
          };
          const colors = urgencyColors[urgency];

          return (
            <div key={act.id} className={`rounded-xl border shadow-sm p-4 flex items-start gap-4 ${colors.bg}`}>
              <div className={`flex-shrink-0 px-2 py-1 rounded-lg text-xs font-bold ${colors.badge}`}>
                {days}d
              </div>
              <div className="flex-1">
                <div className="font-medium text-gray-800 text-sm">{act.subject}</div>
                <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2 flex-wrap">
                  <span>{ACTIVITY_TYPE_LABELS[act.activity_type]}</span>
                  {act.assigned_to && <><span>·</span><span>Rep: {act.assigned_to}</span></>}
                  {act.due_datetime && (
                    <>
                      <span>·</span>
                      <span className={colors.text}>Due: {new Date(act.due_datetime).toLocaleDateString()}</span>
                    </>
                  )}
                </div>
                {act.description && <p className="text-xs text-gray-600 mt-1">{act.description}</p>}
              </div>
              <div className="flex flex-col gap-1 flex-shrink-0">
                <button onClick={() => handleComplete(act.id)}
                  className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700">
                  Complete
                </button>
                <button onClick={() => handleReschedule(act.id)}
                  className="text-xs border border-gray-300 text-gray-600 px-3 py-1 rounded hover:bg-gray-50">
                  Reschedule
                </button>
                <Link href={`/dashboard/crm/records/${act.crm_record_id}`}
                  className="text-xs text-blue-600 hover:underline text-center">
                  View Record
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
