"use client";
import { useEffect, useState } from "react";
import { notificationsApi, NCNotification, TYPE_COLOR, CHANNEL_LABEL } from "@/lib/notifications_center";

type ReportTab = "delivery" | "unread" | "failed";

export default function NotificationReportsPage() {
  const [tab, setTab] = useState<ReportTab>("delivery");
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  const run = async (t: ReportTab) => {
    setLoading(true);
    setData(null);
    try {
      if (t === "delivery") setData(await notificationsApi.reportDelivery());
      else if (t === "unread") setData(await notificationsApi.reportUnread());
      else setData(await notificationsApi.reportFailed());
    } finally { setLoading(false); }
  };

  useEffect(() => { run(tab); }, [tab]);

  const tabs: { key: ReportTab; label: string }[] = [
    { key: "delivery", label: "Delivery Report" },
    { key: "unread", label: "Unread Report" },
    { key: "failed", label: "Failed Notifications" },
  ];

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Notification Reports</h1>

      <div className="flex gap-2 flex-wrap">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm rounded font-medium ${tab === t.key ? "bg-blue-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="bg-white border rounded-lg p-4 shadow-sm">
        {loading && <p className="text-gray-500 text-sm">Loading…</p>}

        {!!data && tab === "delivery" && (() => {
          const rows = data as { channel: string; status: string; count: number }[];
          const channels = Array.from(new Set(rows.map(r => r.channel)));
          const statuses = Array.from(new Set(rows.map(r => r.status)));
          const map: Record<string, Record<string, number>> = {};
          for (const r of rows) {
            if (!map[r.channel]) map[r.channel] = {};
            map[r.channel][r.status] = r.count;
          }
          return (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b"><tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600">Channel</th>
                {statuses.map(s => <th key={s} className="px-4 py-2 text-center text-xs font-semibold text-gray-600 capitalize">{s}</th>)}
              </tr></thead>
              <tbody className="divide-y">
                {channels.map(ch => (
                  <tr key={ch} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{CHANNEL_LABEL[ch as keyof typeof CHANNEL_LABEL] ?? ch}</td>
                    {statuses.map(s => (
                      <td key={s} className={`px-4 py-2 text-center font-semibold ${s === "failed" ? "text-red-600" : s === "read" ? "text-green-600" : "text-gray-700"}`}>
                        {map[ch]?.[s] ?? 0}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          );
        })()}

        {!!data && tab === "unread" && (() => {
          const rows = data as { user_id: string; unread_count: number }[];
          return (
            <div>
              <p className="text-sm text-gray-500 mb-3">{rows.length} users with unread notifications</p>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b"><tr>
                  {["User ID","Unread Count","Progress"].map(h => (
                    <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                  ))}
                </tr></thead>
                <tbody className="divide-y">
                  {rows.map(r => {
                    const max = Math.max(...rows.map(x => x.unread_count));
                    return (
                      <tr key={r.user_id} className="hover:bg-gray-50">
                        <td className="px-4 py-2 font-medium text-gray-800">{r.user_id}</td>
                        <td className={`px-4 py-2 font-bold ${r.unread_count > 20 ? "text-red-600" : r.unread_count > 5 ? "text-orange-600" : "text-gray-700"}`}>
                          {r.unread_count}
                        </td>
                        <td className="px-4 py-2">
                          <div className="bg-gray-100 rounded-full h-2 w-32">
                            <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${(r.unread_count / max) * 100}%` }} />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {rows.length === 0 && <p className="text-gray-400 text-sm text-center py-4">No unread notifications.</p>}
            </div>
          );
        })()}

        {!!data && tab === "failed" && (() => {
          const rows = data as NCNotification[];
          return (
            <div>
              <p className="text-sm text-gray-500 mb-3">{rows.length} failed notifications</p>
              <div className="space-y-2">
                {rows.map(n => (
                  <div key={n.notification_id} className="border border-red-200 bg-red-50 rounded p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLOR[n.notification_type]}`}>
                        {n.notification_type.replace(/_/g," ")}
                      </span>
                      <span className="text-xs text-gray-500">{n.user_id}</span>
                      <span className="text-xs text-gray-400 ml-auto">{new Date(n.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-sm font-semibold text-gray-800">{n.title}</p>
                    {n.error_message && <p className="text-xs text-red-600 mt-1">{n.error_message}</p>}
                    <p className="text-xs text-gray-500">Retries: {n.retry_count}</p>
                  </div>
                ))}
                {rows.length === 0 && <p className="text-gray-400 text-sm text-center py-4">No failed notifications.</p>}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
