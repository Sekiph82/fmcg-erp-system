"use client";

// M49.S01.T002: change notifications for the signed-in user's connected calendars (Google channels, Microsoft Graph
// subscriptions). "Polling" is the honest fallback: the 5-minute sync keeps running whatever the state here.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface Sub {
  id: string; status: string; mode: string; environment: string; expires_at: string; renew_due: boolean;
  last_notification_at: string | null; last_sync_at: string | null; last_error: string | null;
}
interface Row { connection_id: string; provider: string; account_email: string | null; mode: string; subscription: Sub | null }

const LABEL: Record<string, string> = { google: "Google Calendar", microsoft: "Outlook calendar" };
const when = (v: string | null) => (v ? new Date(v).toLocaleString() : "never");
function errorText(e: unknown) {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : "The request failed.";
}

export function CalendarSubscriptionsPanel() {
  const [rows, setRows] = useState<Row[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    try { setRows((await apiClient.get<Row[]>("/api/v1/calendar-subscriptions")).data); } catch { setRows([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const act = async (key: string, fn: () => Promise<string>) => {
    setBusy(key); setMsg(null);
    try { setMsg({ ok: true, text: await fn() }); } catch (e) { setMsg({ ok: false, text: errorText(e) }); }
    finally { setBusy(null); await load(); }
  };

  if (!rows.length) return null;     // nothing to manage until a calendar is connected
  return (
    <div className="border rounded-lg bg-white p-3 space-y-2" data-testid="calendar-subscriptions-panel">
      <div className="text-sm font-semibold text-gray-800">Calendar change notifications</div>
      <p className="text-xs text-gray-500">With notifications on, a change in Google / Outlook reaches the ERP within moments. Without them (or if one lapses) the ERP checks every 5 minutes.</p>
      {msg && <p role={msg.ok ? "status" : "alert"} className={`text-xs rounded px-2 py-1 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}
      <div className="grid sm:grid-cols-2 gap-2">
        {rows.map((r) => {
          const s = r.subscription;
          const live = r.mode === "webhook" && s;
          return (
            <div key={r.connection_id} className="border rounded p-2 text-xs space-y-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{LABEL[r.provider] ?? r.provider}</span>
                <span className={`px-1.5 py-0.5 rounded ${live ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-800"}`}>{live ? "Live notifications" : "Polling every 5 min"}</span>
              </div>
              {r.account_email && <div className="text-gray-600 break-all">{r.account_email}</div>}
              {s && (
                <div className="text-gray-600 space-y-0.5">
                  <div>State: {s.status}{s.status === "ACTIVE" && !live ? " (expired)" : ""} · {s.environment === "SIMULATED" ? "simulated provider (not live)" : "live provider"}</div>
                  <div>Expires: {when(s.expires_at)}{s.renew_due ? " (renewal due)" : ""}</div>
                  <div>Last notification: {when(s.last_notification_at)} · last sync: {when(s.last_sync_at)}</div>
                  {s.last_error && <div className="text-red-600">{s.last_error}</div>}
                </div>)}
              <div className="flex gap-3 flex-wrap">
                {!live && (
                  <button className="text-indigo-600 hover:underline disabled:opacity-50" disabled={busy !== null}
                    onClick={() => act(`en-${r.connection_id}`, async () => { await apiClient.post("/api/v1/calendar-subscriptions", null, { params: { connection_id: r.connection_id } }); return "Notifications enabled and the first sync ran."; })}>
                    {busy === `en-${r.connection_id}` ? "Enabling..." : "Enable notifications"}</button>)}
                {s && s.status !== "STOPPED" && (
                  <>
                    <button className="text-indigo-600 hover:underline disabled:opacity-50" disabled={busy !== null}
                      onClick={() => act(`rn-${s.id}`, async () => { await apiClient.post(`/api/v1/calendar-subscriptions/${s.id}/renew`); return "Renewed."; })}>Renew now</button>
                    <button className="text-indigo-600 hover:underline disabled:opacity-50" disabled={busy !== null}
                      onClick={() => act(`sy-${s.id}`, async () => { const x = await apiClient.post<Record<string, number>>(`/api/v1/calendar-subscriptions/${s.id}/sync`); return `Synced: ${x.data.busy ?? 0} busy block(s), ${x.data.moved ?? 0} moved, ${x.data.cancelled ?? 0} cancelled.`; })}>Sync now</button>
                    <button className="text-red-600 hover:underline disabled:opacity-50" disabled={busy !== null}
                      onClick={() => { if (confirm("Stop notifications for this calendar? Changes will still be picked up every 5 minutes.")) act(`dc-${s.id}`, async () => { await apiClient.post(`/api/v1/calendar-subscriptions/${s.id}/disconnect`); return "Notifications stopped."; }); }}>Disconnect</button>
                  </>)}
              </div>
            </div>);
        })}
      </div>
    </div>
  );
}
