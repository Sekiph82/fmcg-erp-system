"use client";
import { useEffect, useState } from "react";
import {
  chatterApi, ChatterStats, ActivityOut, ActivityType,
  TYPE_BADGE, REF_LABEL, timeAgo,
} from "@/lib/chatter";

type Tab = "volume" | "types" | "users";

const ACTIVITY_TYPES: ActivityType[] = [
  "comment", "system_event", "status_change", "assignment",
  "attachment_added", "approval_action", "notification_event",
];

export default function ChatterReportsPage() {
  const [tab, setTab] = useState<Tab>("volume");
  const [stats, setStats] = useState<ChatterStats | null>(null);
  const [activities, setActivities] = useState<ActivityOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      chatterApi.getStats(),
      chatterApi.listActivities({ per_page: 200 }),
    ]).then(([s, a]) => {
      setStats(s);
      setActivities(a.items);
    }).finally(() => setLoading(false));
  }, []);

  // User activity breakdown
  const byUser = activities.reduce((acc, a) => {
    const u = a.created_by ?? "System";
    acc[u] = (acc[u] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  const topUsers = Object.entries(byUser).sort((a, b) => b[1] - a[1]).slice(0, 10);

  // Type breakdown
  const byType = activities.reduce((acc, a) => {
    acc[a.activity_type] = (acc[a.activity_type] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const tabs: { key: Tab; label: string }[] = [
    { key: "volume", label: "Module Volume" },
    { key: "types", label: "Activity Types" },
    { key: "users", label: "User Activity" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Chatter Reports</h1>

      <div className="flex border-b">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === t.key ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <p className="text-sm text-gray-500 text-center py-8">Loading…</p> : (
        <>
          {tab === "volume" && (
            <div className="bg-white border rounded-lg shadow-sm p-5">
              <h2 className="font-semibold text-gray-800 text-sm mb-4">Activity Volume by Module</h2>
              {stats?.by_module.length === 0
                ? <p className="text-sm text-gray-400">No activity data yet.</p>
                : (
                  <div className="space-y-3">
                    {(stats?.by_module ?? []).map(m => {
                      const max = Math.max(...(stats?.by_module.map(b => b.count) ?? [1]), 1);
                      const pct = Math.round((m.count / max) * 100);
                      return (
                        <div key={m.reference_type}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm text-gray-700 capitalize">
                              {REF_LABEL[m.reference_type as keyof typeof REF_LABEL] ?? m.reference_type.replace("_", " ")}
                            </span>
                            <span className="text-sm font-semibold text-gray-800">{m.count} activities</span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-3">
                            <div className="h-3 rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
            </div>
          )}

          {tab === "types" && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="bg-white border rounded-lg shadow-sm p-5">
                <h2 className="font-semibold text-gray-800 text-sm mb-4">Activities by Type</h2>
                {ACTIVITY_TYPES.map(t => {
                  const count = byType[t] ?? 0;
                  const max = Math.max(...Object.values(byType), 1);
                  const pct = Math.round((count / max) * 100);
                  return (
                    <div key={t} className="mb-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-xs rounded-full px-2 py-0.5 ${TYPE_BADGE[t]}`}>
                          {t.replace("_", " ")}
                        </span>
                        <span className="text-sm font-semibold text-gray-800">{count}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className="h-2 rounded-full bg-blue-400" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="bg-white border rounded-lg shadow-sm p-5">
                <h2 className="font-semibold text-gray-800 text-sm mb-4">Summary</h2>
                {[
                  { label: "Total Activities", value: stats?.total_activities ?? 0 },
                  { label: "Total Comments", value: stats?.total_comments ?? 0 },
                  { label: "Pending Mentions", value: stats?.pending_mentions ?? 0 },
                  { label: "Active Modules", value: stats?.by_module.length ?? 0 },
                  { label: "Pinned Activities", value: activities.filter(a => a.is_pinned).length },
                  { label: "With Attachments", value: activities.filter(a => a.attachments.length > 0).length },
                ].map(s => (
                  <div key={s.label} className="flex justify-between py-2 border-b last:border-0">
                    <span className="text-sm text-gray-600">{s.label}</span>
                    <span className="text-sm font-semibold text-gray-800">{s.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "users" && (
            <div className="bg-white border rounded-lg shadow-sm p-5">
              <h2 className="font-semibold text-gray-800 text-sm mb-4">Top Active Users</h2>
              {topUsers.length === 0
                ? <p className="text-sm text-gray-400">No user activity yet.</p>
                : (
                  <div className="space-y-3">
                    {topUsers.map(([user, count], i) => {
                      const max = topUsers[0][1];
                      const pct = Math.round((count / max) * 100);
                      return (
                        <div key={user}>
                          <div className="flex items-center gap-3 mb-1">
                            <span className="text-xs font-medium text-gray-400 w-4">{i + 1}</span>
                            <div className="w-6 h-6 rounded-full bg-blue-500 text-white text-xs flex items-center justify-center font-bold">
                              {user.charAt(0).toUpperCase()}
                            </div>
                            <span className="text-sm font-medium text-gray-800 flex-1">{user}</span>
                            <span className="text-sm font-semibold text-gray-700">{count}</span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-2 ml-9">
                            <div className="h-2 rounded-full bg-purple-400" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )
              }
            </div>
          )}
        </>
      )}
    </div>
  );
}
