"use client";
import { useEffect, useState } from "react";
import {
  chatterApi, ActivityOut, ActivityType, ReferenceType,
  TYPE_ICON, TYPE_BADGE, TYPE_COLOR, REF_LABEL, timeAgo,
} from "@/lib/chatter";

const ACTIVITY_TYPES: ActivityType[] = [
  "comment", "system_event", "status_change", "assignment",
  "attachment_added", "approval_action", "notification_event",
];
const REF_TYPES: ReferenceType[] = [
  "sales_order", "invoice", "customer", "purchase_order",
  "contract", "employee", "product", "other",
];

export default function FeedPage() {
  const [activities, setActivities] = useState<ActivityOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState("");
  const [filterRef, setFilterRef] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);

  const load = () => {
    setLoading(true);
    chatterApi.listActivities({
      activity_type: filterType || undefined,
      reference_type: filterRef || undefined,
      page,
      per_page: 25,
    }).then(data => {
      setActivities(data.items);
      setTotal(data.total);
      setPages(data.pages);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { setPage(1); }, [filterType, filterRef]);
  useEffect(() => { load(); }, [filterType, filterRef, page]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Activity Feed</h1>

      <div className="flex gap-3 flex-wrap items-center">
        <select className="border rounded px-2 py-1.5 text-sm" value={filterType}
          onChange={e => setFilterType(e.target.value)}>
          <option value="">All Types</option>
          {ACTIVITY_TYPES.map(t => (
            <option key={t} value={t} className="capitalize">{t.replace("_", " ")}</option>
          ))}
        </select>
        <select className="border rounded px-2 py-1.5 text-sm" value={filterRef}
          onChange={e => setFilterRef(e.target.value)}>
          <option value="">All Modules</option>
          {REF_TYPES.map(t => (
            <option key={t} value={t}>{REF_LABEL[t]}</option>
          ))}
        </select>
        <span className="text-xs text-gray-500 ml-auto">{total} activities</span>
      </div>

      {loading ? <p className="text-sm text-gray-500 text-center py-8">Loading…</p> : (
        <div className="space-y-3">
          {activities.map(a => (
            <div key={a.activity_id}
              className={`bg-white border rounded-lg p-4 shadow-sm ${a.is_pinned ? "border-yellow-300" : ""}`}>
              <div className="flex items-start gap-3">
                <div className={`text-base rounded-full px-2 py-1 leading-none shrink-0 ${TYPE_COLOR[a.activity_type]}`}>
                  {TYPE_ICON[a.activity_type]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${TYPE_BADGE[a.activity_type]}`}>
                      {a.activity_type.replace("_", " ")}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-2 py-0.5">
                      {REF_LABEL[a.reference_type]}
                    </span>
                    {a.is_pinned && <span className="text-xs text-yellow-600">📌</span>}
                    <span className="text-xs text-gray-400 ml-auto">{timeAgo(a.created_at)}</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-800">{a.title}</p>
                  {a.message && (
                    <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">{a.message}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-xs text-gray-400">by {a.created_by ?? "System"}</span>
                    {a.comments.filter(c => !c.deleted_flag).length > 0 && (
                      <span className="text-xs text-gray-400">
                        💬 {a.comments.filter(c => !c.deleted_flag).length} comment{a.comments.filter(c => !c.deleted_flag).length !== 1 ? "s" : ""}
                      </span>
                    )}
                    {a.attachments.length > 0 && (
                      <span className="text-xs text-gray-400">📎 {a.attachments.length}</span>
                    )}
                    {a.mentions.length > 0 && (
                      <span className="text-xs text-blue-500">
                        @{a.mentions.map(m => m.mentioned_user).join(" @")}
                      </span>
                    )}
                    <span className="text-xs text-gray-300 ml-auto">ref: {a.reference_id.slice(0, 8)}…</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {activities.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-12">No activities found.</p>
          )}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="rounded border px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40">‹ Prev</button>
          <span className="text-sm text-gray-600">Page {page} of {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages}
            className="rounded border px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40">Next ›</button>
        </div>
      )}
    </div>
  );
}
