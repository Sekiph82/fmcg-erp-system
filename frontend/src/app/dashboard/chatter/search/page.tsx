"use client";
import { useState } from "react";
import {
  chatterApi, ActivityOut, ActivityType, ReferenceType,
  TYPE_ICON, TYPE_BADGE, REF_LABEL, timeAgo,
} from "@/lib/chatter";

const ACTIVITY_TYPES: ActivityType[] = [
  "comment", "system_event", "status_change", "assignment",
  "attachment_added", "approval_action", "notification_event",
];
const REF_TYPES: ReferenceType[] = [
  "sales_order", "invoice", "customer", "purchase_order",
  "contract", "employee", "product", "other",
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterRef, setFilterRef] = useState("");
  const [filterUser, setFilterUser] = useState("");
  const [results, setResults] = useState<ActivityOut[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);

  const search = async (p = 1) => {
    setLoading(true);
    setSearched(true);
    try {
      const data = await chatterApi.listActivities({
        search: query || undefined,
        activity_type: filterType || undefined,
        reference_type: filterRef || undefined,
        created_by: filterUser || undefined,
        page: p,
        per_page: 20,
      });
      setResults(data.items);
      setTotal(data.total);
      setPages(data.pages);
      setPage(p);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Search Activities</h1>

      <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Search text</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Search titles and messages…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") search(); }}
          />
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Activity Type</label>
            <select className="w-full border rounded px-2 py-1.5 text-sm" value={filterType}
              onChange={e => setFilterType(e.target.value)}>
              <option value="">All Types</option>
              {ACTIVITY_TYPES.map(t => (
                <option key={t} value={t} className="capitalize">{t.replace("_", " ")}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Module</label>
            <select className="w-full border rounded px-2 py-1.5 text-sm" value={filterRef}
              onChange={e => setFilterRef(e.target.value)}>
              <option value="">All Modules</option>
              {REF_TYPES.map(t => (
                <option key={t} value={t}>{REF_LABEL[t]}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Created By</label>
            <input className="w-full border rounded px-2 py-1.5 text-sm" placeholder="Username…"
              value={filterUser} onChange={e => setFilterUser(e.target.value)} />
          </div>
        </div>
        <button onClick={() => search(1)} disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      {searched && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">{total} result{total !== 1 ? "s" : ""} found</p>
          </div>

          {loading ? <p className="text-sm text-gray-500 text-center py-8">Searching…</p> : (
            <div className="space-y-3">
              {results.map(a => (
                <div key={a.activity_id} className="bg-white border rounded-lg p-4 shadow-sm">
                  <div className="flex items-start gap-3">
                    <span className="text-lg shrink-0">{TYPE_ICON[a.activity_type]}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className={`text-xs rounded-full px-2 py-0.5 ${TYPE_BADGE[a.activity_type]}`}>
                          {a.activity_type.replace("_", " ")}
                        </span>
                        <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-2 py-0.5">
                          {REF_LABEL[a.reference_type]}
                        </span>
                        <span className="text-xs text-gray-400 ml-auto">{timeAgo(a.created_at)}</span>
                      </div>
                      <p className="text-sm font-semibold text-gray-800">{a.title}</p>
                      {a.message && (
                        <p className="text-sm text-gray-600 mt-0.5 line-clamp-3">{a.message}</p>
                      )}
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-gray-400">by {a.created_by ?? "System"}</span>
                        <span className="text-xs text-gray-300">ref: {a.reference_id.slice(0, 8)}…</span>
                        {a.comments.filter(c => !c.deleted_flag).length > 0 && (
                          <span className="text-xs text-gray-400">💬 {a.comments.filter(c => !c.deleted_flag).length}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {results.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-12">No results found. Try different search terms.</p>
              )}
            </div>
          )}

          {pages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <button onClick={() => search(Math.max(1, page - 1))} disabled={page === 1 || loading}
                className="rounded border px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40">‹ Prev</button>
              <span className="text-sm text-gray-600">Page {page} of {pages}</span>
              <button onClick={() => search(Math.min(pages, page + 1))} disabled={page === pages || loading}
                className="rounded border px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40">Next ›</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
