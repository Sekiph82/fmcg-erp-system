"use client";
import { useEffect, useState } from "react";
import { chatterApi, ChatterStats, ActivityOut, TYPE_ICON, TYPE_BADGE, REF_LABEL, timeAgo } from "@/lib/chatter";
import { tx } from "@/lib/i18n/core";

export default function ChatterDashboard() {
  const [stats, setStats] = useState<ChatterStats | null>(null);
  const [feed, setFeed] = useState<ActivityOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([chatterApi.getStats(), chatterApi.getFeed(20)])
      .then(([s, f]) => { setStats(s); setFeed(f); })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-gray-900">{tx("Chatter & Activity Timeline")}</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: tx("Total Activities"), value: stats?.total_activities ?? "—", color: "text-blue-600" },
          { label: tx("Total Comments"), value: stats?.total_comments ?? "—", color: "text-purple-600" },
          { label: tx("Pending Mentions"), value: stats?.pending_mentions ?? "—", color: "text-orange-600" },
          { label: tx("Active Modules"), value: stats?.by_module.length ?? "—", color: "text-green-600" },
        ].map(s => (
          <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
            <p className="text-xs text-gray-500">{s.label}</p>
            <p className={`text-2xl font-bold mt-1 ${s.color}`}>{loading ? "—" : s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="md:col-span-2 bg-white border rounded-lg shadow-sm">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="font-semibold text-gray-800 text-sm">{tx("Recent Activity Feed")}</h2>
            <a href="/dashboard/chatter/feed" className="text-xs text-blue-600 hover:underline">{tx("View all")}</a>
          </div>
          {loading ? <p className="p-4 text-sm text-gray-500">{tx("Loading…")}</p> : (
            <div className="divide-y max-h-80 overflow-y-auto">
              {feed.map(a => (
                <div key={a.activity_id} className="px-4 py-3 flex items-start gap-3">
                  <span className="text-lg">{TYPE_ICON[a.activity_type]}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs rounded-full px-2 py-0.5 ${TYPE_BADGE[a.activity_type]}`}>
                        {a.activity_type.replace("_", " ")}
                      </span>
                      <span className="text-xs text-gray-400">{REF_LABEL[a.reference_type]}</span>
                      <span className="text-xs text-gray-400 ml-auto">{timeAgo(a.created_at)}</span>
                    </div>
                    <p className="text-sm font-medium text-gray-800 truncate mt-0.5">{a.title}</p>
                    {a.message && <p className="text-xs text-gray-500 truncate">{a.message}</p>}
                    <p className="text-xs text-gray-400 mt-0.5">{tx("by")} {a.created_by ?? tx("System")}</p>
                  </div>
                </div>
              ))}
              {feed.length === 0 && <p className="p-4 text-sm text-gray-400 text-center py-8">{tx("No activity yet.")}</p>}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-white border rounded-lg shadow-sm p-4">
            <h2 className="font-semibold text-gray-800 text-sm mb-3">{tx("Activity by Module")}</h2>
            {loading || !stats ? <p className="text-sm text-gray-500">{tx("Loading…")}</p> : (
              <div className="space-y-2">
                {stats.by_module.slice(0, 8).map(m => {
                  const max = Math.max(...stats.by_module.map(b => b.count), 1);
                  const pct = Math.round((m.count / max) * 100);
                  return (
                    <div key={m.reference_type}>
                      <div className="flex justify-between text-xs text-gray-600 mb-0.5">
                        <span className="capitalize">{m.reference_type.replace("_", " ")}</span>
                        <span>{m.count}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
                {stats.by_module.length === 0 && <p className="text-sm text-gray-400">{tx("No data yet.")}</p>}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
            {[
              { href: "/dashboard/chatter/feed", label: tx("My Feed"), icon: "📋" },
              { href: "/dashboard/chatter/search", label: tx("Search"), icon: "🔍" },
              { href: "/dashboard/chatter/reports", label: tx("Reports"), icon: "📊" },
              { href: "/dashboard/chatter/ai", label: tx("AI Insights"), icon: "🤖" },
            ].map(l => (
              <a key={l.href} href={l.href}
                className="bg-white border rounded-lg p-3 shadow-sm hover:bg-gray-50 text-center">
                <div className="text-xl mb-1">{l.icon}</div>
                <p className="text-xs font-medium text-gray-700">{l.label}</p>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
