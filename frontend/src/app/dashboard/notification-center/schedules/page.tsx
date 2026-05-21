"use client";
import { useEffect, useState } from "react";
import {
  notificationsApi, NCSchedule, NotificationType, NotificationChannel,
  NOTIFICATION_TYPES, CHANNELS, CHANNEL_LABEL, TYPE_COLOR,
} from "@/lib/notifications_center";

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<NCSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [form, setForm] = useState({
    user_id: "", title: "", message: "",
    notification_type: "reminder" as NotificationType,
    channel: "in_app" as NotificationChannel,
    scheduled_for: "", recurring: false, recurrence_days: "",
    reference_type: "", reference_id: "",
  });

  const load = () => notificationsApi.listSchedules().then(setSchedules).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    await notificationsApi.createSchedule({
      ...form,
      recurring: form.recurring,
      recurrence_days: form.recurrence_days ? Number(form.recurrence_days) : undefined,
      reference_type: form.reference_type || undefined,
      reference_id: form.reference_id || undefined,
    });
    setShowForm(false);
    load();
  };

  const processDue = async () => {
    setProcessing(true);
    const r = await notificationsApi.processDueSchedules();
    setProcessing(false);
    alert(`Processed ${r.processed} due schedules.`);
    load();
  };

  const deactivate = async (id: string) => {
    await notificationsApi.deactivateSchedule(id);
    load();
  };

  const isOverdue = (s: NCSchedule) => new Date(s.scheduled_for) < new Date();

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-gray-900">Notification Schedules</h1>
        <div className="flex gap-2">
          <button onClick={processDue} disabled={processing}
            className="rounded border border-green-200 px-3 py-1.5 text-sm text-green-700 hover:bg-green-50 disabled:opacity-50">
            {processing ? "Processing…" : "Process Due Now"}
          </button>
          <button onClick={() => setShowForm(true)}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            + Schedule Reminder
          </button>
        </div>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 shadow-sm space-y-3">
          <h2 className="font-semibold text-gray-800">New Scheduled Notification</h2>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-gray-500">User ID *</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.user_id}
                onChange={(e) => setForm({ ...form, user_id: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">Scheduled For *</label>
              <input type="datetime-local" className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.scheduled_for}
                onChange={(e) => setForm({ ...form, scheduled_for: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">Type</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.notification_type}
                onChange={(e) => setForm({ ...form, notification_type: e.target.value as NotificationType })}>
                {NOTIFICATION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Channel</label>
              <select className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.channel}
                onChange={(e) => setForm({ ...form, channel: e.target.value as NotificationChannel })}>
                {CHANNELS.map(c => <option key={c} value={c}>{CHANNEL_LABEL[c]}</option>)}
              </select></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Title *</label>
              <input className="w-full border rounded px-2 py-1 text-sm mt-1" value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Message *</label>
              <textarea className="w-full border rounded px-2 py-1 text-sm mt-1" rows={2} value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })} /></div>
            <div className="flex items-center gap-2 col-span-2">
              <input type="checkbox" checked={form.recurring}
                onChange={(e) => setForm({ ...form, recurring: e.target.checked })} />
              <label className="text-sm text-gray-700">Recurring</label>
              {form.recurring && (
                <div className="flex items-center gap-2 ml-4">
                  <label className="text-xs text-gray-500">Every</label>
                  <input type="number" min={1} className="border rounded px-2 py-0.5 text-sm w-16"
                    value={form.recurrence_days}
                    onChange={(e) => setForm({ ...form, recurrence_days: e.target.value })} />
                  <span className="text-xs text-gray-500">days</span>
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={submit} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">Schedule</button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["User","Title","Type","Channel","Scheduled For","Recurring","Last Sent","Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {schedules.map(s => (
                <tr key={s.schedule_id} className={`hover:bg-gray-50 ${isOverdue(s) ? "bg-yellow-50" : ""}`}>
                  <td className="px-4 py-2 font-medium text-gray-800">{s.user_id}</td>
                  <td className="px-4 py-2 text-gray-700">{s.title}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLOR[s.notification_type]}`}>
                      {s.notification_type.replace(/_/g," ")}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-600">{CHANNEL_LABEL[s.channel]}</td>
                  <td className={`px-4 py-2 ${isOverdue(s) ? "text-orange-600 font-semibold" : "text-gray-600"}`}>
                    {new Date(s.scheduled_for).toLocaleString()}
                    {isOverdue(s) && <span className="ml-1 text-xs">(due)</span>}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {s.recurring ? <span className="text-green-600">Every {s.recurrence_days}d</span> : "—"}
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    {s.last_sent_at ? new Date(s.last_sent_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => deactivate(s.schedule_id)}
                      className="text-xs text-red-500 hover:underline">Deactivate</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {schedules.length === 0 && <p className="text-center text-gray-400 py-8 text-sm">No active schedules.</p>}
        </div>
      )}
    </div>
  );
}
