"use client";
import { useEffect, useState } from "react";
import { essApi, ESSNotification, NOTIF_TYPE_ICON } from "@/lib/ess";

const DEMO_EMPLOYEE = "00000000-0000-0000-0000-000000000001";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<ESSNotification[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const load = () => essApi.listNotifications(DEMO_EMPLOYEE, unreadOnly).then(setNotifications).catch(console.error);
  useEffect(() => { load(); }, [unreadOnly]);

  const handleMarkRead = async (id: string) => {
    await essApi.markRead(id, DEMO_EMPLOYEE);
    load();
  };

  const handleMarkAll = async () => {
    await essApi.markAllRead(DEMO_EMPLOYEE);
    load();
  };

  const unreadCount = notifications.filter((n) => !n.read_flag).length;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Notifications</h1>
          {unreadCount > 0 && <p className="text-xs text-gray-500">{unreadCount} unread</p>}
        </div>
        <div className="flex gap-2">
          <label className="flex items-center gap-1.5 text-sm cursor-pointer">
            <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
            Unread only
          </label>
          {unreadCount > 0 && (
            <button onClick={handleMarkAll} className="bg-gray-100 text-gray-600 px-3 py-1.5 rounded text-sm hover:bg-gray-200">
              Mark all read
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {notifications.map((n) => (
          <div key={n.notification_id}
            className={`bg-white border rounded-xl p-4 flex gap-3 ${!n.read_flag ? "border-blue-200 bg-blue-50/30" : ""}`}>
            <span className="text-xl shrink-0 mt-0.5">{NOTIF_TYPE_ICON[n.notification_type]}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <p className={`text-sm font-medium ${!n.read_flag ? "text-gray-900" : "text-gray-600"}`}>{n.title}</p>
                <span className="text-xs text-gray-400 shrink-0">{new Date(n.created_at).toLocaleDateString()}</span>
              </div>
              <p className="text-sm text-gray-500 mt-0.5">{n.body}</p>
              {!n.read_flag && (
                <button onClick={() => handleMarkRead(n.notification_id)}
                  className="text-xs text-blue-600 hover:underline mt-1">Mark as read</button>
              )}
            </div>
            {!n.read_flag && <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0 mt-2" />}
          </div>
        ))}
        {notifications.length === 0 && (
          <div className="bg-white border rounded-xl p-8 text-center text-gray-400 text-sm">
            {unreadOnly ? "No unread notifications" : "No notifications"}
          </div>
        )}
      </div>
    </div>
  );
}
