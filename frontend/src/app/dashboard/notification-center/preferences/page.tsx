"use client";
import { useEffect, useState } from "react";
import {
  notificationsApi, NCPreference, NotificationType, NotificationChannel,
  NOTIFICATION_TYPES, CHANNELS, CHANNEL_LABEL,
} from "@/lib/notifications_center";

export default function PreferencesPage() {
  const [userId, setUserId] = useState("user001");
  const [prefs, setPrefs] = useState<NCPreference[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    notificationsApi.listPreferences(userId).then(setPrefs).finally(() => setLoading(false));
  };
  useEffect(() => { if (userId) load(); }, [userId]);

  const seed = async () => {
    await notificationsApi.seedPreferences(userId);
    load();
  };

  const toggle = async (ntype: NotificationType, channel: NotificationChannel, current: boolean) => {
    const key = `${ntype}:${channel}`;
    setSaving(key);
    await notificationsApi.upsertPreference(userId, {
      notification_type: ntype,
      channel: channel,
      enabled_flag: !current,
    });
    setSaving(null);
    load();
  };

  // Build matrix: type → channel → pref
  const matrix: Record<NotificationType, Record<NotificationChannel, NCPreference | null>> = {} as never;
  for (const t of NOTIFICATION_TYPES) {
    matrix[t] = {} as Record<NotificationChannel, NCPreference | null>;
    for (const c of CHANNELS) matrix[t][c] = null;
  }
  for (const p of prefs) {
    if (matrix[p.notification_type]) {
      matrix[p.notification_type][p.channel] = p;
    }
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Notification Preferences</h1>

      <div className="flex gap-3 items-end">
        <div>
          <label className="text-xs text-gray-500">User ID</label>
          <input className="block border rounded px-2 py-1 text-sm mt-1 w-40" value={userId}
            onChange={(e) => setUserId(e.target.value)} />
        </div>
        <button onClick={load} className="rounded border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Load</button>
        <button onClick={seed} className="rounded border border-blue-200 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50">
          Seed Defaults
        </button>
      </div>

      <p className="text-xs text-gray-500">Click a cell to toggle. Green = enabled, Gray = disabled.</p>

      {loading ? <p className="text-gray-500 text-sm">Loading…</p> : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-600 w-48">Notification Type</th>
                {CHANNELS.map(c => (
                  <th key={c} className="px-4 py-2 text-center text-xs font-semibold text-gray-600">{CHANNEL_LABEL[c]}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {NOTIFICATION_TYPES.map(ntype => (
                <tr key={ntype} className="hover:bg-gray-50">
                  <td className="px-4 py-2 capitalize font-medium text-gray-700">{ntype.replace(/_/g," ")}</td>
                  {CHANNELS.map(ch => {
                    const pref = matrix[ntype][ch];
                    const enabled = pref?.enabled_flag ?? false;
                    const key = `${ntype}:${ch}`;
                    return (
                      <td key={ch} className="px-4 py-2 text-center">
                        <button
                          disabled={saving === key}
                          onClick={() => toggle(ntype, ch, enabled)}
                          className={`w-10 h-6 rounded-full transition-colors relative ${enabled ? "bg-green-500" : "bg-gray-300"} ${saving === key ? "opacity-50" : ""}`}
                        >
                          <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${enabled ? "translate-x-4" : "translate-x-0.5"}`} />
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
