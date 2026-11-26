"use client";
// M49.S01.T011 audience lifecycle on ad platforms: segment -> preview -> approve -> sync -> status -> consent withdrawal.
// Only consented members, SHA-256 hashed, never shown unmasked. Lookalikes only where the platform's API documents one.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import { tx, lx } from "@/lib/i18n/core";

type Provider = "meta" | "google" | "linkedin" | "tiktok";
const LABEL: Record<Provider, string> = lx(() => ({ meta: tx("Meta"), google: tx("Google Ads (Data Manager API)"), linkedin: tx("LinkedIn"), tiktok: tx("TikTok") }));
interface Account { id: string; provider: Provider; name: string; currency: string; member: boolean; refusal: string | null }
interface Sync { id: string; audience_id: string; audience_name: string | null; account_id: string; account_name: string; provider: Provider; kind: string;
  name: string; external_id: string | null; status: string; mode: "LIVE" | "SIMULATED"; provider_status: string | null; provider_size: number | null;
  approval_status: string; requested_by: string | null; approved_by: string | null; created_by: string; last_error: string | null;
  members: Record<string, number>; can_approve: boolean; spec: { ratio?: number }; origin_sync_id: string | null;
  gate: { mode: string; transport: string; reasons: string[] } }
interface Preview { add: number; remove: number; unchanged: number; size_after: number; blocked_no_consent: number; hash: string; sample_add: string[]; note: string | null;
  eligibility: { minimum: number; size_after: number; eligible: boolean; blocking: boolean; note: string } }
interface Cap { provider: Provider; operations: Record<string, boolean>; minimum: number; minimum_blocking: boolean; minimum_note: string; note: string | null }
interface Aud { id: string; name: string; member_count: number }

const err = (e: unknown) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : d && typeof d === "object" && "detail" in d ? String((d as { detail: unknown }).detail)
    : e instanceof Error && e.message ? e.message : tx("Request failed.");
};
const input = "border rounded px-2 py-1 text-xs bg-white text-gray-900";
const btn = "text-xs border rounded px-2 py-1 bg-white text-gray-900 disabled:opacity-40 disabled:cursor-not-allowed";
const chip = (s: string) => `text-[10px] font-semibold px-2 py-0.5 rounded ${
  s === "READY" ? "bg-green-100 text-green-900" : ["FAILED", "UNKNOWN", "DELETED"].includes(s) ? "bg-red-100 text-red-900" : "bg-amber-100 text-amber-900"}`;
const API = "/api/v1/audience-sync";

export default function AudienceSync() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [syncs, setSyncs] = useState<Sync[]>([]);
  const [auds, setAuds] = useState<Aud[]>([]);
  const [caps, setCaps] = useState<{ export_enabled: boolean; providers: Cap[] } | null>(null);
  const [conv, setConv] = useState<{ rows: { provider: string; status: string; count: number }[] } | null>(null);
  const [aid, setAid] = useState("");
  const [acct, setAcct] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [withdrawn, setWithdrawn] = useState<{ removed: { provider: string; result: string }[]; note: string | null } | null>(null);

  const load = useCallback(async () => {
    try {
      const [l, a, c, v] = await Promise.all([apiClient.get(API), apiClient.get("/api/v1/audiences"), apiClient.get(`${API}/capabilities`), apiClient.get(`${API}/conversions/overview`)]);
      setAccounts(l.data.accounts); setSyncs(l.data.syncs); setAuds(a.data); setCaps(c.data); setConv(v.data);
    } catch (e) { setMsg(err(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setMsg(null);
    try { await fn(); setMsg(ok); } catch (e) { setMsg(err(e)); }
    setBusy(false); load();
  };
  const chosen = accounts.find((a) => a.id === acct);

  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">{tx("Audience sync with ad platforms")}</h2>
        <Link href="/dashboard/crm/audiences" className="text-xs underline">{tx("Segments")}</Link>
        <Link href="/dashboard/marketing/ads/lifecycle" className="text-xs underline">{tx("Advertising lifecycle")}</Link>
      </div>
      <p className="text-xs text-gray-500">{tx("Segment → preview → approval by a second person → sync (simulated unless every live switch is on) → status poll → consent withdrawal removes the person everywhere and suppresses them. Only people with marketing consent are sent, as SHA-256 hashes.")}</p>
      {caps && !caps.export_enabled && <p role="alert" className="text-xs border border-amber-300 bg-amber-50 text-amber-900 rounded p-2">
        {tx("Audience sharing is switched off (AUDIENCE_EXPORT_ENABLED): nothing can be sent to a platform. Removals and consent withdrawals still work.")}</p>}
      {msg && <p role="status" className="text-xs border rounded p-2 bg-gray-50 text-gray-900">{msg}</p>}

      <section className="border rounded p-3 bg-white text-gray-900 space-y-2">
        <h3 className="font-semibold">{tx("1. Choose segment and ad account")}</h3>
        <form className="flex flex-wrap gap-2 items-end" onSubmit={(e) => { e.preventDefault(); run(() => apiClient.post(API, { audience_id: aid, account_id: acct }), tx("Sync draft created. Preview it next.")); }}>
          <label className="text-xs">{tx("Segment")}<select className={`${input} block`} value={aid} onChange={(e) => setAid(e.target.value)} required>
            <option value="">{tx("Select…")}</option>{auds.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.member_count})</option>)}</select></label>
          <label className="text-xs">{tx("Ad account")}<select className={`${input} block`} value={acct} onChange={(e) => setAcct(e.target.value)} required>
            <option value="">{tx("Select…")}</option>{accounts.map((a) => <option key={a.id} value={a.id}>{LABEL[a.provider]} · {a.name}{a.member ? "" : tx(" (not allowed)")}</option>)}</select></label>
          <button className={btn} disabled={busy || !aid || !acct || !chosen?.member} title={chosen && !chosen.member ? chosen.refusal ?? "" : ""}>{tx("Create sync")}</button>
        </form>
        {accounts.filter((a) => !a.member).map((a) => <p key={a.id} className="text-xs text-red-800">{tx("Refused for you —")} {LABEL[a.provider]} · {a.name}: {a.refusal}</p>)}
        {accounts.length === 0 && <p className="text-xs text-gray-500">{tx("No ad accounts yet. Add one under Ads reporting.")}</p>}
      </section>

      <section className="space-y-3">
        <h3 className="font-semibold">{tx("2. Syncs")}</h3>
        {syncs.length === 0 && <p className="text-xs text-gray-500">{tx("No audience has been set up on an ad account yet.")}</p>}
        {syncs.map((s) => <SyncCard key={s.id} s={s} cap={caps?.providers.find((c) => c.provider === s.provider)} busy={busy} run={run} />)}
      </section>

      <section className="border rounded p-3 bg-white text-gray-900 space-y-2">
        <h3 className="font-semibold">{tx("3. Consent withdrawal")}</h3>
        <p className="text-xs text-gray-500">{tx("Unsubscribes the address, adds it to the suppression list (never sent again) and removes it from every platform list that holds it.")}</p>
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault();
          run(async () => { const r = await apiClient.post(`${API}/consent-withdrawal`, { email }); setWithdrawn(r.data); setEmail(""); }, tx("Consent withdrawn.")); }}>
          <input aria-label={tx("E-mail address")} type="email" className={`${input} w-64`} placeholder="customer@povu-demo.test" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <button className={btn} disabled={busy || !email}>{tx("Withdraw consent and remove")}</button>
        </form>
        {withdrawn && <ul className="text-xs list-disc ml-5">{withdrawn.removed.length === 0 && <li>{tx("Not on any platform list; suppressed.")}</li>}
          {withdrawn.removed.map((r, i) => <li key={i}>{LABEL[r.provider as Provider]}: {r.result}</li>)}{withdrawn.note && <li>{withdrawn.note}</li>}</ul>}
      </section>

      <section className="border rounded p-3 bg-white text-gray-900 space-y-2">
        <h3 className="font-semibold">{tx("4. Conversion upload and what each platform supports")}</h3>
        <div className="flex flex-wrap gap-2 items-center">
          {(["meta", "google"] as Provider[]).map((p) => <button key={p} className={btn} disabled={busy || !caps?.export_enabled}
            title={caps?.export_enabled ? "" : tx("AUDIENCE_EXPORT_ENABLED is off.")}
            onClick={() => run(async () => { const r = await apiClient.post(`/api/v1/audiences/conversion-uploads/${p}`); if (r.data.status === "NOT_CONFIGURED") throw new Error(r.data.message); },
              tx("{LABEL} conversions uploaded (consented, hashed, once per source).", { LABEL: LABEL[p] }))}>{tx("Upload")} {LABEL[p]} {tx("conversions")}</button>)}
          {(["linkedin", "tiktok"] as Provider[]).map((p) => <button key={p} className={btn} disabled title={caps?.providers.find((c) => c.provider === p)?.note ?? ""}>{tx("Upload")} {LABEL[p]} {tx("conversions")}</button>)}
        </div>
        {conv && conv.rows.length > 0 && <p className="text-xs">{tx("Uploaded so far:")} {conv.rows.map((r) => `${r.provider} ${r.status.toLowerCase()} ${r.count}`).join(" · ")}</p>}
        <table className="w-full text-xs"><thead><tr className="text-left text-gray-500"><th>{tx("Platform")}</th><th>{tx("Create")}</th><th>{tx("Add / remove")}</th><th>{tx("Delete")}</th><th>{tx("Status")}</th><th>{tx("Lookalike")}</th><th>{tx("Minimum size")}</th><th>{tx("Note")}</th></tr></thead>
          <tbody>{caps?.providers.map((c) => (
            <tr key={c.provider} className="border-t align-top"><td>{LABEL[c.provider]}</td>
              <td>{c.operations.create ? tx("yes") : tx("no")}</td><td>{c.operations.add && c.operations.remove ? tx("yes") : tx("no")}</td><td>{c.operations.delete ? tx("yes") : tx("no")}</td>
              <td>{c.operations.status ? tx("yes") : tx("no")}</td><td>{c.operations.lookalike ? tx("yes") : tx("not available")}</td>
              <td>{c.minimum}{c.minimum_blocking ? tx(" (blocks)") : tx(" (advice)")}<div className="text-gray-400">{c.minimum_note}</div></td><td>{c.note}</td></tr>))}</tbody></table>
      </section>
    </div>
  );
}

function SyncCard({ s, cap, busy, run }: { s: Sync; cap?: Cap; busy: boolean; run: (fn: () => Promise<unknown>, ok: string) => void }) {
  const [pv, setPv] = useState<Preview | null>(null);
  const [ratio, setRatio] = useState("0.01");
  const [local, setLocal] = useState<{ label: string; note?: string; candidates: { name: string; score: number; reasons: string[] }[] } | null>(null);
  const u = `${API}/${s.id}`;
  const lookalike = s.kind === "LOOKALIKE";
  const gone = s.status === "DELETED";
  const counts = Object.entries(s.members).map(([k, v]) => `${k.replace("_", " ").toLowerCase()} ${v}`).join(" · ") || "no members sent";
  return (
    <div className="border rounded p-3 bg-white text-gray-900 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{s.name}</span><span className={chip(s.status)}>{s.status}</span>
        <span className={`text-[10px] px-2 py-0.5 rounded ${s.mode === "LIVE" ? "bg-red-600 text-white" : "bg-amber-100 text-amber-900"}`}>{s.mode}</span>
        <span className="text-xs text-gray-500">{LABEL[s.provider]} · {s.account_name} · {lookalike ? tx("lookalike ratio {ratio}", { ratio: s.spec.ratio }) : counts}</span>
      </div>
      <p className="text-xs text-gray-500">{tx("Segment:")} {s.audience_name} {tx("· platform id")} {s.external_id ?? tx("not created yet")} {tx("· platform status:")} {s.provider_status ?? "—"}
        {s.provider_size != null ? tx(" · size ≥ {provider_size}", { provider_size: s.provider_size }) : ""} {tx("· approval:")} {s.approval_status.toLowerCase()}{s.approved_by ? tx(" by {approved_by}", { approved_by: s.approved_by }) : ""}</p>
      {s.gate.reasons.length > 0 && <ul className="text-xs text-amber-800 list-disc ml-5">{s.gate.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
      {s.last_error && <p className="text-xs text-red-700">{tx("Last error:")} {s.last_error}</p>}
      {pv && <div className="text-xs border rounded p-2 bg-gray-50">
        <p>{tx("Would add")} {pv.add}{tx(", remove")} {pv.remove}{tx(", keep")} {pv.unchanged} {tx("→ list size")} {pv.size_after}{tx(". Approval covers diff")} {pv.hash}.</p>
        {pv.sample_add.length > 0 && <p>{tx("Examples (masked):")} {pv.sample_add.join(", ")}</p>}
        <p className={pv.eligibility.blocking ? "text-red-700" : ""}>{tx("Eligibility: minimum")} {pv.eligibility.minimum} — {pv.eligibility.eligible ? tx("met") : pv.eligibility.blocking ? tx("NOT met, blocks the sync") : tx("not met (advice only)")}. {pv.eligibility.note}</p>
      </div>}
      <div className="flex flex-wrap gap-1 items-center">
        {!lookalike && <button className={btn} disabled={busy || gone} onClick={async () => { try { setPv((await apiClient.get(`${u}/preview`)).data); } catch (e) { setPv(null); alert(err(e)); } }}>{tx("Preview")}</button>}
        <button className={btn} disabled={busy || gone || s.approval_status === "PENDING"} onClick={() => run(() => apiClient.post(`${u}/approvals`), tx("Approval requested."))}>{tx("Request approval")}</button>
        <button className={btn} disabled={busy || s.approval_status !== "PENDING" || !s.can_approve} title={s.approval_status !== "PENDING" ? tx("Nothing waiting for approval.") : s.can_approve ? "" : tx("Needs marketing.approve and must not be the requester or author.")}
          onClick={() => run(() => apiClient.post(`${u}/decide`, { ok: true }), "Approved.")}>{tx("Approve")}</button>
        <button className={btn} disabled={busy || s.approval_status !== "PENDING" || !s.can_approve} onClick={() => run(() => apiClient.post(`${u}/decide`, { ok: false }), "Rejected.")}>{tx("Reject")}</button>
        <button className={btn} disabled={busy || s.approval_status !== "APPROVED"} title={s.approval_status === "APPROVED" ? "" : tx("Needs an approved request.")}
          onClick={() => run(() => apiClient.post(`${u}/sync`), tx("Synced; read the platform status next."))}>{tx("Sync")}</button>
        <button className={btn} disabled={busy || !s.external_id || gone} onClick={() => run(() => apiClient.post(`${u}/poll`), tx("Status read from the platform."))}>{tx("Poll status")}</button>
        <button className={btn} disabled={busy || !["UNKNOWN", "FAILED"].includes(s.status)} title={tx("Re-sends pending member changes (idempotent) and reads the status.")}
          onClick={() => run(() => apiClient.post(`${u}/reconcile`), "Reconciled.")}>{tx("Reconcile")}</button>
        <button className={btn} disabled={busy || gone} onClick={() => { if (confirm(tx("Delete this audience on the platform? Members are removed from it."))) run(() => apiClient.delete(u), tx("Audience deleted.")); }}>{tx("Delete")}</button>
        {!lookalike && <>
          <input aria-label={tx("Lookalike ratio")} className={`${input} w-16`} type="number" min="0.01" max="0.2" step="0.01" value={ratio} onChange={(e) => setRatio(e.target.value)} />
          <button className={btn} disabled={busy || gone || !cap?.operations.lookalike} title={cap?.operations.lookalike ? tx("Needs the list on the platform and at least the seed minimum.") : tx("Not available: {note}", { note: cap?.note ?? "no documented API" })}
            onClick={() => run(() => apiClient.post(`${API}/lookalike`, { origin_sync_id: s.id, ratio: Number(ratio) }), tx("Lookalike draft created; approve and sync it."))}>{tx("Platform lookalike")}</button>
          <button className={btn} disabled={busy} onClick={async () => { try { setLocal((await apiClient.get(`/api/v1/audiences/${s.audience_id}/similar`)).data); } catch (e) { alert(err(e)); } }}>{tx("Local similarity score")}</button></>}
      </div>
      {local && <div className="text-xs border rounded p-2 bg-gray-50"><p className="font-medium">{local.label}</p>{local.note && <p>{local.note}</p>}
        <ul className="list-disc ml-5">{local.candidates.slice(0, 5).map((c) => <li key={c.name}>{c.name}: {c.score} — {c.reasons.join("; ")}</li>)}</ul></div>}
    </div>
  );
}
