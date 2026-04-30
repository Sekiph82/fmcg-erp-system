"use client";
import { useEffect, useState } from "react";
import {
  notificationsApi, NCNotification, NotificationType, NotificationPriority,
  TYPE_COLOR, TYPE_ICON, PRIORITY_COLOR, STATUS_COLOR,
  NOTIFICATION_TYPES, PRIORITIES,
} from "@/lib/notifications_center";

export default function NotificationListPage() {
  const [notifications, setNotifications] = useState<NCNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    user_id: "", notification_type: "", priority: "", read_flag: "" as "" | "true" | "false", module: "",
  });
  const [selected, setSelected] = useState<NCNotification | null>(null);
  const [showCompose, setShowCompose] = useState(false);
  const [compose, setCompose] = useState({
    user_id: "", title: "", message: "",
    notification_type: "info" as NotificationType,
    priority: "normal" as NotificationPriority,
    channel: "in_app",
    module: "", reference_type: "", reference_id: "",
  });

  const load = () => {
    const params: Record<string, string | boolean | undefined> = {};
    if (filters.user_id) params.user_id = filters.user_id;
    if (filters.notification_type) params.notification_type = filters.notification_type;
    if (filters.priority) params.priority = filters.priority;
    if (filters.read_flag !== "") params.read_flag = filters.read_flag === "true";
    if (filters.module) params.module = filters.module;
    notificationsApi.list(params).then(setNotifications).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [filters]);

  const markRead = async (id: string) => {
    await notificationsApi.markRead(id);
    load();
  };

  const markAllRead = async () => {
    if (!filters.user_id) { alert("Enter a user ID to mark all read"); return; }
    await notificationsApi.markAllRead(filters.user_id);
    load();
  };

  const del = async (id: string) => {
    await notificationsApi.delete(id);
    setSelected(null);
    load();
  };

  const send = async () => {
    await notificationsApi.create({
      ...compose,
      module: compose.module || undefined,
      reference_type: compose.reference_type || undefined,
      reference_id: compose.reference_id || undefined,
    });
    setShowCompose(false);
    load();
  };

  const unread = notifications.filter(n => !n.read_flag).length;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Notifications</h1>
          {unread > 0 && <p className="text-sm text-orange-600 mt-0.5">{unread} unread</p>}
        </div>
        <div className="flex gap-2">
          <button onClick={markAllRead} className="rounded border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
            Mark All Read
          </button>
          <button onClick={() => setShowCompose(true)}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + Send Notification
          </button>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <input className="border rounded px-2 py-1 text-sm w-32" placeholder="User ID…"
          value={filters.user_id} onChange={(e) => setFilters({ ...filters, user_id: e.target.value })} />
        <select className="border rounded px-2 py-1 text-sm" value={filters.notification_type}
          onChange={(e) => setFilters({ ...filters, notification_type: e.target.value })}>
          <option value="">All Types</option>
          {NOTIFICATION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
        </select>
        <select className="border rounded px-2 py-1 text-sm" value={filters.priority}
          onChange={(e) => setFilters({ ...filters, priority: e.target.value })}>
          <option value="">All Priorities</option>
          {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select className="border rounded px-2 py-1 text-sm" value={filters.read_flag}
          onChange={(e) => setFilters({ ...filters, read_flag: e.target.value as "" | "true" | "false" })}>
          <option value="">All</option>
          <option value="false">Unread</option>
          <option value="true">Read</option>
        </select>
        <input className="border rounded px-2 py-1 text-sm w-28" placeholder="Module…"
          value={filters.module} onChange={(e) => setFilters({ ...filters, module: e.target.value })} />
      </div>

      {showCompose && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">Send Notification</h2>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-gray-500">User ID *</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={compose.user_id}
                onChange={(e) => setCompose({ ...compose, user_id: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">Type</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={compose.notification_type}
                onChange={(e) => setCompose({ ...compose, notification_type: e.target.value as NotificationType })}>
                {NOTIFICATION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Priority</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={compose.priority}
                onChange={(e) => setCompose({ ...compose, priority: e.target.value as NotificationPriority })}>
                {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Module</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={compose.module}
                onChange={(e) => setCompose({ ...compose, module: e.target.value })} /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Title *</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={compose.title}
                onChange={(e) => setCompose({ ...compose, title: e.target.value })} /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Message *</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={3} value={compose.message}
                onChange={(e) => setCompose({ ...compose, message: e.target.value })} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={send} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Send</button>
            <button onClick={() => setShowCompose(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.notification_id}
              onClick={() => setSelected(n)}
              className={`bg-white border rounded-lg p-3 shadow-sm cursor-pointer hover:bg-gray-50 flex gap-3 ${!n.read_flag ? "border-l-4 border-l-blue-500" : ""}`}
            >
              <span className="text-xl shrink-0">{TYPE_ICON[n.notification_type]}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLOR[n.notification_type]}`}>
                    {n.notification_type.replace(/_/g," ")}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLOR[n.priority]}`}>
                    {n.priority}
                  </span>
                  {n.module && <span className="text-xs text-gray-400">{n.module}</span>}
                  {!n.read_flag && <span className="ml-auto text-xs font-semibold text-blue-600">UNREAD</span>}
                </div>
                <p className="font-semibold text-gray-800 text-sm mt-0.5 truncate">{n.title}</p>
                <p className="text-xs text-gray-500 truncate">{n.message}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {n.user_id} · {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
          {notifications.length === 0 && <p className="text-gray-400 text-sm text-center py-8">No notifications found.</p>}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-3">
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{TYPE_ICON[selected.notification_type]}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLOR[selected.notification_type]}`}>
                  {selected.notification_type.replace(/_/g," ")}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLOR[selected.priority]}`}>
                  {selected.priority}
                </span>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
            </div>
            <h2 className="font-bold text-gray-900">{selected.title}</h2>
            <p className="text-sm text-gray-700">{selected.message}</p>
            <div className="text-xs text-gray-400 space-y-0.5">
              <p>User: {selected.user_id}</p>
              {selected.module && <p>Module: {selected.module}</p>}
              {selected.reference_type && <p>Ref: {selected.reference_type} #{selected.reference_id}</p>}
              <p>Status: <span className={STATUS_COLOR[selected.status]}>{selected.status}</span></p>
              <p>Created: {new Date(selected.created_at).toLocaleString()}</p>
              {selected.read_at && <p>Read: {new Date(selected.read_at).toLocaleString()}</p>}
            </div>
            <div className="flex gap-2 pt-2">
              {!selected.read_flag && (
                <button onClick={() => { markRead(selected.notification_id); setSelected(null); }}
                  className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">
                  Mark Read
                </button>
              )}
              <button onClick={() => del(selected.notification_id)}
                className="rounded border border-red-200 px-4 py-1.5 text-sm text-red-600 hover:bg-red-50">
                Delete
              </button>
              <button onClick={() => setSelected(null)}
                className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
