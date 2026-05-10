"use client";
import { useCallback, useEffect, useState } from "react";
import { essApi, ESSNotification, NOTIF_TYPE_ICON } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<ESSNotification[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const load = useCallback(() => essApi.listNotifications(DEMO_EMPLOYEE, unreadOnly).then(setNotifications).catch(console.error), [unreadOnly]);
  useEffect(() => { load(); }, [load]);

  const handleMarkRead = async (id: string) => { await essApi.markRead(id, DEMO_EMPLOYEE); load(); };
  const handleMarkAll = async () => { await essApi.markAllRead(DEMO_EMPLOYEE); load(); };
  const unreadCount = notifications.filter((n) => !n.read_flag).length;

  return (
    <div className="p-6 space-y-4 text-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Notifications</h1>
          {unreadCount > 0 && <p className="text-slate-500 text-sm mt-0.5">{unreadCount} unread</p>}
        </div>
        <div className="flex gap-3 items-center">
          <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
            <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} className="accent-indigo-500" />
            Unread only
          </label>
          {unreadCount > 0 && (
            <button onClick={handleMarkAll} className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 text-xs">
              Mark all read
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {notifications.map((n) => (
          <div key={n.notification_id}
            className={`rounded-xl border p-4 flex gap-3 transition-colors ${!n.read_flag ? "border-indigo-500/20 bg-indigo-500/5" : "border-white/[0.07] glow-card"}`}>
            <span className="text-xl shrink-0 mt-0.5">{NOTIF_TYPE_ICON[n.notification_type]}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <p className={`text-sm font-medium ${!n.read_flag ? "text-white" : "text-slate-400"}`}>{n.title}</p>
                <span className="text-xs text-slate-600 shrink-0">{new Date(n.created_at).toLocaleDateString()}</span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{n.body}</p>
              {!n.read_flag && (
                <button onClick={() => handleMarkRead(n.notification_id)} className="text-xs text-indigo-400 hover:text-indigo-300 mt-1">Mark as read</button>
              )}
            </div>
            {!n.read_flag && <div className="w-2 h-2 rounded-full bg-indigo-500 shrink-0 mt-2" />}
          </div>
        ))}
        {notifications.length === 0 && (
          <div className="glow-card p-8 text-center text-slate-600">
            {unreadOnly ? "No unread notifications" : "No notifications"}
          </div>
        )}
      </div>
    </div>
  );
}
