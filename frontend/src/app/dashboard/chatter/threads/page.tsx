"use client";
import { useCallback, useEffect, useState } from "react";
import { chatterApi, ActivityOut, TimelineResponse, timeAgo, TYPE_BADGE } from "@/lib/chatter";

const REF_OPTIONS = [
  { value: "", label: "All Modules" },
  { value: "sales_order", label: "Sales Orders" },
  { value: "invoice", label: "Invoices" },
  { value: "customer", label: "Customers" },
  { value: "purchase_order", label: "Purchase Orders" },
  { value: "crm_record", label: "CRM / Leads" },
  { value: "ticket", label: "Helpdesk Tickets" },
  { value: "project", label: "Projects" },
  { value: "production", label: "Production" },
  { value: "batch", label: "Batches / Lots" },
  { value: "batch_recall", label: "Batch Recalls" },
  { value: "document", label: "Documents" },
  { value: "contract", label: "Contracts" },
  { value: "other", label: "Other" },
];

const REF_COLORS: Record<string, string> = {
  sales_order: "bg-blue-100 text-blue-700",
  invoice: "bg-indigo-100 text-indigo-700",
  customer: "bg-purple-100 text-purple-700",
  purchase_order: "bg-orange-100 text-orange-700",
  crm_record: "bg-emerald-100 text-emerald-700",
  ticket: "bg-red-100 text-red-700",
  project: "bg-teal-100 text-teal-700",
  production: "bg-yellow-100 text-yellow-700",
  batch: "bg-pink-100 text-pink-700",
  batch_recall: "bg-rose-100 text-rose-700",
  document: "bg-gray-100 text-gray-700",
  contract: "bg-violet-100 text-violet-700",
  other: "bg-gray-50 text-gray-500",
};

export default function CrossModuleThreadsPage() {
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [slaBreached, setSlaBreached] = useState<ActivityOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [refType, setRefType] = useState("");
  const [search, setSearch] = useState("");
  const [slaOnly, setSlaOnly] = useState(false);
  const [page, setPage] = useState(1);

  const load = useCallback(async (filters?: { search?: string }) => {
    setLoading(true);
    try {
      const [tl, sla] = await Promise.all([
        chatterApi.getTimeline({
          reference_types: refType || undefined,
          search: filters?.search || undefined,
          sla_overdue_only: slaOnly || undefined,
          page,
          per_page: 30,
        }),
        chatterApi.getSLABreached(10),
      ]);
      setData(tl);
      setSlaBreached(sla);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [refType, slaOnly, page]);

  useEffect(() => { load(); }, [load]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    load({ search });
  };

  const refLabel = (rt: string) => REF_OPTIONS.find(o => o.value === rt)?.label || rt;
  const refColor = (rt: string) => REF_COLORS[rt] || "bg-gray-100 text-gray-600";

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cross-Module Activity Timeline</h1>
          <p className="text-sm text-gray-500 mt-0.5">Unified thread view across all modules — sales, CRM, production, helpdesk, and more</p>
        </div>
        {data && (
          <div className="text-sm text-gray-500">
            {data.total.toLocaleString()} total activities
            {data.sla_breached_count > 0 && (
              <span className="ml-2 px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium text-xs">
                {data.sla_breached_count} SLA overdue
              </span>
            )}
          </div>
        )}
      </div>

      {/* SLA Breached Alert */}
      {slaBreached.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 bg-red-500 rounded-full" />
            <span className="font-semibold text-red-800 text-sm">SLA Overdue ({slaBreached.length})</span>
          </div>
          <div className="space-y-2">
            {slaBreached.map(a => (
              <div key={a.activity_id} className="flex items-start gap-3 bg-white rounded-lg border border-red-100 p-3">
                <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${refColor(a.reference_type)}`}>
                  {refLabel(a.reference_type)}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-800 truncate">{a.title}</div>
                  <div className="text-xs text-red-600 mt-0.5">
                    SLA due: {a.sla_due_at ? new Date(a.sla_due_at).toLocaleString() : "—"} · {a.created_by}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Module Breakdown */}
      {data && data.module_breakdown.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {data.module_breakdown.map(m => (
            <button key={m.module}
              onClick={() => { setRefType(refType === m.module ? "" : m.module); setPage(1); }}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                refType === m.module ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}>
              {refLabel(m.module)} ({m.count})
            </button>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input type="text" placeholder="Search threads…" value={search}
            onChange={e => setSearch(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm w-56" />
          <button type="submit" className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
            Search
          </button>
        </form>
        <select value={refType} onChange={e => { setRefType(e.target.value); setPage(1); }}
          className="border rounded-lg px-3 py-1.5 text-sm">
          {REF_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input type="checkbox" checked={slaOnly} onChange={e => { setSlaOnly(e.target.checked); setPage(1); }} />
          SLA Overdue Only
        </label>
      </div>

      {/* Timeline */}
      {loading ? (
        <div className="text-gray-400 text-sm py-8 text-center">Loading timeline…</div>
      ) : (
        <>
          <div className="space-y-3">
            {(!data || data.items.length === 0) && (
              <div className="text-center py-10 text-gray-400 text-sm">No activities found</div>
            )}
            {data?.items.map(a => (
              <div key={a.activity_id} className="bg-white rounded-xl border shadow-sm p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 flex flex-col gap-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${refColor(a.reference_type)}`}>
                      {refLabel(a.reference_type)}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${TYPE_BADGE[a.activity_type as keyof typeof TYPE_BADGE] || "bg-gray-100 text-gray-600"}`}>
                      {a.activity_type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium text-gray-800 text-sm leading-tight">{a.title}</div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {a.is_pinned && <span className="text-xs text-amber-600">📌</span>}
                        {a.sla_due_at && (
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            new Date(a.sla_due_at) < new Date() ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                          }`}>
                            SLA: {new Date(a.sla_due_at).toLocaleDateString()}
                          </span>
                        )}
                        <span className="text-xs text-gray-400">{timeAgo(a.created_at)}</span>
                      </div>
                    </div>
                    {a.message && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{a.message}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                      <span>by {a.created_by || "system"}</span>
                      {a.comments.length > 0 && <span>💬 {a.comments.length}</span>}
                      {a.mentions.length > 0 && <span>@ {a.mentions.length}</span>}
                      {a.attachments.length > 0 && <span>📎 {a.attachments.length}</span>}
                      <span className="text-gray-300">ref: {a.reference_id.slice(0, 8)}…</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex justify-center gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-40">
                Prev
              </button>
              <span className="px-3 py-1.5 text-sm text-gray-600">
                Page {page} of {data.pages}
              </span>
              <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page >= data.pages}
                className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-40">
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
