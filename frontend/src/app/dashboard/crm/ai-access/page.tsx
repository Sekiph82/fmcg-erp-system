"use client";
// M45.S01.T012/T022: personal access tokens (Outlook/Gmail add-in, MCP clients) and AI-proposed changes awaiting approval.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Token = { id: string; name: string; prefix: string; scopes: string[]; expires_at: string; revoked: boolean; last_used_at: string | null };
type Req = { id: string; source: string; action: string; summary: string; status: string; created_at: string; decided_by: string | null; result: Record<string, unknown> | null };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export default function AIAccessPage() {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [scopes, setScopes] = useState<Record<string, string>>({});
  const [name, setName] = useState("Outlook add-in");
  const [pick, setPick] = useState<string[]>(["crm.addin"]);
  const [days, setDays] = useState(90);
  const [shown, setShown] = useState<string | null>(null);
  const [reqs, setReqs] = useState<Req[]>([]);
  const [status, setStatus] = useState("PENDING");
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/access-tokens").then((r) => { setTokens(r.data.tokens); setScopes(r.data.scopes); }).catch((e) => setMsg(err(e)));
    apiClient.get("/api/v1/access-tokens/requests", { params: { status } }).then((r) => setReqs(r.data)).catch(() => setReqs([]));
  }, [status]);
  useEffect(() => { load(); }, [load]);
  const create = () => apiClient.post("/api/v1/access-tokens", { name, scopes: pick, days }).then((r) => { setShown(r.data.token); load(); }).catch((e) => setMsg(err(e)));
  const revoke = (id: string) => apiClient.delete(`/api/v1/access-tokens/${id}`).then(load).catch((e) => setMsg(err(e)));
  const decide = (id: string, a: string) => apiClient.post(`/api/v1/access-tokens/requests/${id}/${a}`).then(load).catch((e) => setMsg(err(e)));
  const origin = typeof window !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL || window.location.origin) : "";

  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">{tx("Add-ins & AI access")}</h2>
      {msg && <p role="status" className="text-xs text-red-600">{msg}</p>}
      <section className="border rounded p-3 bg-white space-y-2">
        <h3 className="font-semibold">{tx("My access tokens")}</h3>
        <p className="text-xs text-gray-500">{tx("A token acts with your own permissions. Use it in the Outlook/Gmail add-in or an AI client (MCP server at")} <code>{origin}/api/v1/public/mcp</code>).</p>
        <div className="flex flex-wrap gap-2 items-end">
          <label className="text-xs">{tx("Name")}<input className="border rounded px-2 py-1 block" value={name} onChange={(e) => setName(e.target.value)} /></label>
          <label className="text-xs">{tx("Valid for (days)")}<input type="number" min={1} max={365} className="border rounded px-2 py-1 block w-24" value={days} onChange={(e) => setDays(+e.target.value)} /></label>
          <button className="bg-indigo-600 text-white rounded px-3 py-1" disabled={!pick.length} onClick={create}>{tx("Create token")}</button>
        </div>
        <fieldset className="text-xs space-y-1"><legend className="font-medium">{tx("Scopes")}</legend>
          {Object.entries(scopes).map(([k, d]) => <label key={k} className="flex gap-2 items-start"><input type="checkbox" checked={pick.includes(k)}
            onChange={(e) => setPick(e.target.checked ? [...pick, k] : pick.filter((x) => x !== k))} /><span><b>{k}</b>: {d}</span></label>)}</fieldset>
        {shown && <div className="border rounded p-2 bg-amber-50 text-xs break-all"><b>{tx("Copy it now; it is not shown again:")}</b> <code>{shown}</code> <button className="underline" onClick={() => setShown(null)}>{tx("Done")}</button></div>}
        <ul className="text-xs divide-y">{tokens.map((t) => <li key={t.id} className="py-1 flex flex-wrap justify-between gap-2">
          <span>{t.name} · {t.prefix}… · {t.scopes.join(", ")} · {t.revoked ? tx("revoked") : `expires ${new Date(t.expires_at).toLocaleDateString()}`}{t.last_used_at ? ` · used ${new Date(t.last_used_at).toLocaleString()}` : ""}</span>
          {!t.revoked && <button className="text-red-600 underline" onClick={() => revoke(t.id)}>{tx("Revoke")}</button>}</li>)}</ul>
      </section>
      <section className="border rounded p-3 bg-white space-y-2">
        <div className="flex justify-between items-center"><h3 className="font-semibold">{tx("AI requests")}</h3>
          <select aria-label={tx("Request status")} className="border rounded px-2 py-1 text-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
            {["PENDING", "DONE", "REJECTED", "FAILED"].map((s) => <option key={s}>{s}</option>)}</select></div>
        <p className="text-xs text-gray-500">{tx("Changes proposed by AI clients and agents. Nothing happens until someone other than the requester approves.")}</p>
        {reqs.length === 0 ? <p className="text-xs text-gray-400">{tx("Nothing here.")}</p> : <ul className="text-xs divide-y">{reqs.map((r) => <li key={r.id} className="py-1 flex flex-wrap justify-between gap-2">
          <span><b>{r.source}</b> · {r.summary} · {new Date(r.created_at).toLocaleString()}{r.decided_by ? ` · ${r.status.toLowerCase()} by ${r.decided_by}` : ""}</span>
          {r.status === "PENDING" && <span className="flex gap-2"><button className="underline" onClick={() => decide(r.id, "approve")}>{tx("Approve")}</button><button className="underline text-red-600" onClick={() => decide(r.id, "reject")}>{tx("Reject")}</button></span>}</li>)}</ul>}
      </section>
    </div>
  );
}
