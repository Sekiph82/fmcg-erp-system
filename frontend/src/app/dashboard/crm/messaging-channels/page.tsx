"use client";
// M44.S01.T013 messaging channels: Meta / Slack configuration state and custom channels (token shown once).
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface Custom { id: string; key: string; name: string; active: boolean; created_by: string; token?: string }
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Request failed."; };

export default function MessagingChannelsPage() {
  const [st, setSt] = useState<{ meta: string; slack: string } | null>(null);
  const [list, setList] = useState<Custom[] | null>(null);
  const [key, setKey] = useState("");
  const [name, setName] = useState("");
  const [token, setToken] = useState<{ key: string; token: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    apiClient.get("/api/v1/crm-channels/status").then((r) => setSt(r.data)).catch(() => undefined);
    apiClient.get<Custom[]>("/api/v1/crm-channels/custom-channels").then((r) => setList(r.data)).catch(() => setList(null));
  }, []);
  useEffect(() => { load(); }, [load]);

  async function act(fn: () => Promise<{ data: Custom }>) {
    setError(null);
    try { const r = await fn(); if (r.data.token) setToken({ key: r.data.key, token: r.data.token }); await load(); } catch (e) { setError(err(e)); }
  }
  const badge = (s?: string) => <span className={`text-xs px-2 py-0.5 rounded ${s === "CONFIGURED" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}>{s === "CONFIGURED" ? tx("Configured") : tx("Not configured")}</span>;
  const api = typeof window === "undefined" ? "" : (process.env.NEXT_PUBLIC_API_URL || window.location.origin);
  return (
    <div className="space-y-4">
      <section className="bg-white border rounded-xl p-4 space-y-2 text-sm">
        <h2 className="font-semibold">{tx("Connected services")}</h2>
        <p>{tx("Messenger and Instagram DMs")} {badge(st?.meta)} {tx("— messages arrive on the signed Meta webhook for pages registered under Social → Channels and show in the Inbox.")}</p>
        <p>{tx("Slack notices")} {badge(st?.slack)} {tx("— deal won, new ticket and approval waiting are posted once to the Slack incoming webhook.")}</p>
        <p className="text-xs text-gray-500">{tx("Tokens and webhook URLs are server settings; they are added at activation (M47). Until then nothing is sent.")}</p>
      </section>
      <section className="bg-white border rounded-xl p-4 space-y-3 text-sm">
        <h2 className="font-semibold">{tx("Custom channels")}</h2>
        {error && <p role="alert" className="text-red-700">{error}</p>}
        {token && (
          <div className="border border-amber-300 bg-amber-50 rounded p-2 break-all">
            {tx("Token for")} <b>{token.key}</b> {tx("— shown once, copy it now:")} <code>{token.token}</code>
            <button className="ml-2 underline text-xs" onClick={() => setToken(null)}>{tx("Hide")}</button>
          </div>
        )}
        {list === null ? <p className="text-gray-500">{tx("Only CRM administrators manage custom channels.")}</p> : (
          <>
            <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); act(() => apiClient.post("/api/v1/crm-channels/custom-channels", { key, name })).then(() => { setKey(""); setName(""); }); }}>
              <input aria-label={tx("Channel key")} required value={key} onChange={(e) => setKey(e.target.value.toLowerCase())} placeholder={tx("key, e.g. partner-app")} className="border rounded px-2 py-1 flex-1 min-w-[10rem]" />
              <input aria-label={tx("Channel name")} required value={name} onChange={(e) => setName(e.target.value)} placeholder={tx("name")} className="border rounded px-2 py-1 flex-1 min-w-[10rem]" />
              <button className="px-3 py-1 rounded bg-indigo-600 text-white">{tx("Add channel")}</button>
            </form>
            <ul className="divide-y">
              {list.map((c) => (
                <li key={c.id} className="py-2 flex flex-wrap items-center gap-2">
                  <span className="font-medium">{c.name}</span><code className="text-xs">{c.key}</code>
                  {!c.active && <span className="text-xs text-gray-500">{tx("disabled")}</span>}
                  <span className="ml-auto flex gap-2 text-xs">
                    <button className="underline" onClick={() => act(() => apiClient.post(`/api/v1/crm-channels/custom-channels/${c.id}/rotate`))}>{tx("New token")}</button>
                    <button className="underline" onClick={() => act(() => apiClient.post(`/api/v1/crm-channels/custom-channels/${c.id}/${c.active ? "disable" : "enable"}`))}>{c.active ? tx("Disable") : tx("Enable")}</button>
                  </span>
                </li>
              ))}
              {!list.length && <li className="py-2 text-gray-500">{tx("No custom channels yet.")}</li>}
            </ul>
            <details className="text-xs text-gray-600">
              <summary className="cursor-pointer">API</summary>
              <pre className="whitespace-pre-wrap break-all mt-1">{tx("POST {api}/api/v1/public/channels/<key>/messages\nAuthorization: Bearer <token>\n{\"thread_id\": \"t1\", \"message_id\": \"42\", \"sender\": \"Duka Moja\", \"text\": \"Need 20 cartons of POVU AllClean 1 L\"}\n→ threaded in the Inbox; the same message_id is stored once\n\nGET {api}/api/v1/public/channels/<key>/outbox\nAuthorization: Bearer <token>\n→ {\"items\": [{\"id\", \"thread_id\", \"text\", \"created_at\"}]}  our replies, each handed over once", { api })}</pre>
            </details>
          </>
        )}
      </section>
    </div>
  );
}
