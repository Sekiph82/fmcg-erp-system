"use client";
// M45.S01.T023: audited "log in as another user" for support, session log, and company notification defaults.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { usersApi } from "@/lib/users";
import { tx } from "@/lib/i18n/core";

type Sess = { id: string; actor: string; target: string; reason: string; started_at: string; expires_at: string; ended_at: string | null; ended_reason: string | null };
type Pol = { notification_type: string; channel: string; default_enabled: boolean; mandatory: boolean };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : tx("Something went wrong."); };

export default function SupportAccessPage() {
  const [q, setQ] = useState("");
  const [users, setUsers] = useState<{ id: string; username: string; full_name: string; is_superuser: boolean }[]>([]);
  const [target, setTarget] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [minutes, setMinutes] = useState(30);
  const [sessions, setSessions] = useState<Sess[]>([]);
  const [pols, setPols] = useState<{ types: string[]; channels: string[]; policies: Pol[] } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/impersonation/sessions").then((r) => setSessions(r.data)).catch(() => setSessions([]));
    apiClient.get("/api/v1/impersonation/notification-policies").then((r) => setPols(r.data)).catch(() => setPols(null));
  }, []);
  useEffect(() => { load(); }, [load]);
  const find = () => usersApi.list({ search: q, limit: 10, is_active: true }).then((r) => setUsers(r.items as unknown as typeof users)).catch((e) => setMsg(err(e)));
  // a full reload is required: the signed-in identity changes, so every cached user/permission must be dropped
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  const start = () => apiClient.post("/api/v1/impersonation/start", { user_id: target, reason, minutes }).then(() => window.location.assign("/dashboard")).catch((e) => setMsg(err(e)));
  const setPol = (p: Pol, patch: Partial<Pol>) => apiClient.put("/api/v1/impersonation/notification-policies", { ...p, ...patch }).then((r) => setPols(r.data)).catch((e) => setMsg(err(e)));

  return (
    <div className="p-4 space-y-4 text-sm max-w-4xl">
      <h2 className="text-lg font-semibold">{tx("Support access & notification defaults")}</h2>
      {msg && <p role="status" className="text-xs text-red-600">{msg}</p>}
      <section className="border rounded p-3 bg-white space-y-2">
        <h3 className="font-semibold">{tx("Log in as another user")}</h3>
        <p className="text-xs text-gray-500">{tx("For support only. Needs a reason, ends after at most 60 minutes, cannot be used on superusers, never touches the user's password, 2FA or tokens. The user is notified and every action is logged under both names.")}</p>
        <div className="flex gap-2"><input aria-label={tx("Find user")} className="border rounded px-2 py-1" placeholder={tx("Name or username")} value={q} onChange={(e) => setQ(e.target.value)} /><button className="border rounded px-3" onClick={find}>{tx("Find")}</button></div>
        <div className="flex flex-wrap gap-2 text-xs">{users.map((u) => <button key={u.id} disabled={u.is_superuser} className={`border rounded px-2 ${target === u.id ? "bg-indigo-50" : ""} disabled:opacity-40`} onClick={() => setTarget(u.id)}>{u.full_name} ({u.username}){u.is_superuser ? tx(" · superuser") : ""}</button>)}</div>
        <textarea aria-label={tx("Reason")} className="border rounded px-2 py-1 w-full text-xs" rows={2} placeholder={tx("Reason, e.g. ticket TKT-123: cannot see her orders")} value={reason} onChange={(e) => setReason(e.target.value)} />
        <div className="flex gap-2 items-center text-xs"><label>{tx("Minutes")} <input aria-label={tx("Minutes")} type="number" min={1} max={60} className="border rounded px-1 w-16" value={minutes} onChange={(e) => setMinutes(+e.target.value)} /></label>
          <button className="bg-red-700 text-white rounded px-3 py-1" disabled={!target || reason.trim().length < 10} onClick={start}>{tx("Start support session")}</button></div>
      </section>
      <section className="border rounded p-3 bg-white space-y-1"><h3 className="font-semibold">{tx("Support sessions")}</h3>
        <ul className="text-xs divide-y">{sessions.map((s) => <li key={s.id} className="py-1">{new Date(s.started_at).toLocaleString()} · <b>{s.actor}</b> {tx("as")} <b>{s.target}</b> · {s.reason} · {s.ended_at ? `${(s.ended_reason ?? "").toLowerCase()} ${new Date(s.ended_at).toLocaleTimeString()}` : tx("until {date}", { date: new Date(s.expires_at).toLocaleTimeString() })}</li>)}</ul></section>
      {pols && <section className="border rounded p-3 bg-white space-y-1 overflow-x-auto"><h3 className="font-semibold">{tx("Company notification defaults")}</h3>
        <p className="text-xs text-gray-500">{tx("Users can change non-mandatory notifications for themselves; mandatory ones are always delivered.")}</p>
        <table className="text-xs"><thead><tr><th className="text-left p-1">{tx("Type")}</th>{pols.channels.map((c) => <th key={c} className="p-1">{c}</th>)}</tr></thead>
          <tbody>{pols.types.map((t) => <tr key={t} className="border-t"><td className="p-1">{t.replace("_", " ")}</td>{pols.channels.map((c) => { const p = pols.policies.find((x) => x.notification_type === t && x.channel === c)!; return <td key={c} className="p-1 whitespace-nowrap">
            <label className="mr-2"><input type="checkbox" aria-label={tx("{t} {c} on by default", { t, c })} checked={p.default_enabled} disabled={p.mandatory} onChange={(e) => setPol(p, { default_enabled: e.target.checked })} /> {tx("on")}</label>
            <label><input type="checkbox" aria-label={tx("{t} {c} mandatory", { t, c })} checked={p.mandatory} onChange={(e) => setPol(p, { mandatory: e.target.checked })} /> {tx("must")}</label></td>; })}</tr>)}</tbody></table></section>}
    </div>
  );
}
