"use client";
// M50.S01.T011 Gmail / Outlook add-in sign-ins of the signed-in user: what each may do, last use, and revoke.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Sess = { id: string; host: string; origin: string; scopes: string[]; created_at: string; last_used_at: string | null };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export default function AddinSessionsPage() {
  const [rows, setRows] = useState<Sess[] | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => { apiClient.get("/api/v1/public/crm-addin/sessions").then((r) => setRows(r.data)).catch((e) => setMsg(err(e))); }, []);
  useEffect(() => { load(); }, [load]);
  const revoke = (id: string) => apiClient.delete(`/api/v1/public/crm-addin/sessions/${id}`).then(() => { setMsg(tx("Signed out of that add-in.")); load(); }).catch((e) => setMsg(err(e)));
  return (
    <div className="p-4 space-y-3 text-sm max-w-3xl">
      <h2 className="text-lg font-semibold">{tx("Add-in sign-ins")}</h2>
      <p className="text-xs text-gray-500">{tx("Gmail and Outlook add-ins that act for you in the CRM. Each has a 15-minute access token that renews itself; revoking stops it at once.")}</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {rows && rows.length === 0 && <p className="text-xs">{tx("No add-in is signed in.")}</p>}
      <ul className="divide-y">{(rows ?? []).map((s) => <li key={s.id} className="py-2 flex justify-between gap-2 items-center">
        <span><b>{s.host === "gmail" ? tx("Gmail add-on") : tx("Outlook add-in")}</b> · {s.scopes.includes("addin.write") ? tx("look-up, log e-mails, notes and tasks") : tx("look-up only")} {tx("· signed in")} {new Date(s.created_at).toLocaleString()} · {s.last_used_at ? `last used ${new Date(s.last_used_at).toLocaleString()}` : tx("not used yet")}</span>
        <button className="border rounded px-2 py-1 text-xs" onClick={() => revoke(s.id)}>{tx("Revoke")}</button></li>)}</ul>
    </div>
  );
}
