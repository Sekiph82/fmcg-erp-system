"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  notificationsApi, NCDashboard,
  TYPE_COLOR, PRIORITY_COLOR, CHANNEL_LABEL,
} from "@/lib/notifications_center";

export default function NotificationCenterDashboard() {
  const [dash, setDash] = useState<NCDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    notificationsApi.getDashboard().then(setDash).finally(() => setLoading(false));
  }, []);

  const seedTemplates = async () => {
    setSeeding(true);
    const r = await notificationsApi.seedTemplates();
    setSeeding(false);
    alert(`Seeded ${r.created} default templates.`);
  };

  const kpis = dash ? [
    { label: "Total Notifications", value: dash.total_notifications },
    { label: "Unread", value: dash.unread_count, color: "text-orange-600" },
    { label: "Sent Today", value: dash.sent_today, color: "text-green-600" },
    { label: "Failed", value: dash.failed_count, color: "text-red-600" },
    { label: "Pending Schedules", value: dash.pending_schedules, color: "text-blue-600" },
  ] : [];

  const links = [
    { href: "/dashboard/notification-center/list", label: "All Notifications" },
    { href: "/dashboard/notification-center/preferences", label: "Preferences" },
    { href: "/dashboard/notification-center/templates", label: "Templates" },
    { href: "/dashboard/notification-center/schedules", label: "Schedules" },
    { href: "/dashboard/notification-center/reports", label: "Reports" },
    { href: "/dashboard/notification-center/ai", label: "AI Insights" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Notification Center</h1>
        <button onClick={seedTemplates} disabled={seeding}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
          {seeding ? "Seeding…" : "Seed Default Templates"}
        </button>
      </div>

      {loading ? <p className="text-gray-500">Loading…</p> : (
        <>
          <div className="grid grid-cols-3 gap-4 lg:grid-cols-5">
            {kpis.map((k) => (
              <div key={k.label} className="bg-white rounded-lg border p-4 shadow-sm">
                <p className="text-xs text-gray-500">{k.label}</p>
                <p className={`text-2xl font-bold mt-1 ${k.color ?? "text-gray-900"}`}>{k.value}</p>
              </div>
            ))}
          </div>

          {dash && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="bg-white border rounded-lg p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">By Type</h2>
                <div className="space-y-1.5">
                  {Object.entries(dash.by_type).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLOR[type as keyof typeof TYPE_COLOR] ?? "bg-gray-100 text-gray-600"}`}>
                        {type.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm font-semibold text-gray-700">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-white border rounded-lg p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">By Priority</h2>
                <div className="space-y-1.5">
                  {Object.entries(dash.by_priority).map(([p, count]) => (
                    <div key={p} className="flex items-center justify-between">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLOR[p as keyof typeof PRIORITY_COLOR] ?? ""}`}>
                        {p}
                      </span>
                      <span className="text-sm font-semibold text-gray-700">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-white border rounded-lg p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-700 mb-3">By Channel</h2>
                <div className="space-y-1.5">
                  {Object.entries(dash.by_channel).map(([ch, count]) => (
                    <div key={ch} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">{CHANNEL_LABEL[ch as keyof typeof CHANNEL_LABEL] ?? ch}</span>
                      <span className="text-sm font-semibold text-gray-700">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {dash && dash.top_modules.length > 0 && (
            <div className="bg-white border rounded-lg p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Top Modules</h2>
              <div className="flex gap-4 flex-wrap">
                {dash.top_modules.map((m) => (
                  <div key={m.module} className="bg-gray-50 rounded-lg px-4 py-2 text-center">
                    <p className="text-lg font-bold text-gray-800">{m.count}</p>
                    <p className="text-xs text-gray-500 capitalize">{m.module}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Quick Navigation</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {links.map((l) => (
            <Link key={l.href} href={l.href}
              className="block rounded border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700 hover:bg-blue-100 text-center">
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
