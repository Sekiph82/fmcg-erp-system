"use client";
// M44.S01.T002–T005 ad platforms: connection status, accounts, synced performance, guarded drafts. No live publishing.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";

interface Provider { provider: string; configured: boolean; validate_only: boolean }
interface Account { id: string; provider: string; external_id: string; name: string; currency: string; status: string; last_error: string | null; last_sync_at: string | null }
interface Perf { provider: string; account: string; currency: string; campaign_id: string; campaign: string; impressions: number; clicks: number;
  spend: number; conversions: number; ctr: number | null; cpc: number | null; cost_per_conversion: number | null }
interface Draft { id: string; account_id: string; name: string; objective: string; daily_budget: number; status: string;
  created_by: string; approved_by: string | null; validation: { ok?: boolean; provider_checked?: boolean; problems?: string[] } | null }

const LABEL: Record<string, string> = { meta: "Meta", google: "Google Ads", linkedin: "LinkedIn", tiktok: "TikTok" };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : d && typeof d === "object" && "detail" in d ? String((d as { detail: unknown }).detail) : "Request failed."; };
const key = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);

export default function AdsPage() {
  const [prov, setProv] = useState<Provider[]>([]);
  const [accts, setAccts] = useState<Account[]>([]);
  const [perf, setPerf] = useState<Perf[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [na, setNa] = useState({ provider: "meta", external_id: "", name: "", currency: "KES" });
  const [nd, setNd] = useState({ account_id: "", name: "", objective: "OUTCOME_AWARENESS", daily_budget: "10", idem: key() });
  const load = useCallback(() => Promise.all([
    apiClient.get("/api/v1/ads/providers").then((r) => setProv(r.data)),
    apiClient.get("/api/v1/ads/accounts").then((r) => setAccts(r.data)),
    apiClient.get("/api/v1/ads/performance").then((r) => setPerf(r.data)),
    apiClient.get("/api/v1/ads/drafts").then((r) => setDrafts(r.data)),
  ]).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const run = async (fn: () => Promise<unknown>, ok: string) => { setMsg(null); try { await fn(); setMsg(ok); } catch (e) { setMsg(err(e)); } load(); };
  const input = "border rounded px-2 py-1 text-xs";
  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-3"><h2 className="text-lg font-semibold">Ads</h2>
        <Link href="/dashboard/marketing/ads/campaigns" className="text-xs border rounded px-2 py-1">Open campaign builder</Link></div>
      <p className="text-xs text-gray-500">Reporting for Meta, Google Ads, LinkedIn and TikTok. Quick drafts below are checked and approved but never published; build real campaigns (created paused, approved, SIMULATED until live activation) in the campaign builder.</p>
      {msg && <p role="status" className="text-xs border rounded p-2 bg-gray-50">{msg}</p>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">{prov.map((p) => (
        <div key={p.provider} className="border rounded p-2 bg-white text-xs"><b>{LABEL[p.provider]}</b>
          <div className={p.configured ? "text-emerald-700" : "text-gray-500"}>{p.configured ? "Connected" : "Not configured"}</div>
          <div className="text-gray-500">{p.validate_only ? "Platform validate-only checks" : "Local checks only"}</div></div>))}</div>

      <section className="border rounded p-3 bg-white space-y-2">
        <h3 className="font-semibold">Ad accounts</h3>
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); run(() => apiClient.post("/api/v1/ads/accounts", na), "Account added."); }}>
          <select aria-label="Platform" className={input} value={na.provider} onChange={(e) => setNa({ ...na, provider: e.target.value })}>{Object.entries(LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          <input aria-label="Account id" required placeholder="Account id" className={input} value={na.external_id} onChange={(e) => setNa({ ...na, external_id: e.target.value })} />
          <input aria-label="Account name" required placeholder="Name" className={input} value={na.name} onChange={(e) => setNa({ ...na, name: e.target.value })} />
          <input aria-label="Currency" required maxLength={3} className={`${input} w-16`} value={na.currency} onChange={(e) => setNa({ ...na, currency: e.target.value.toUpperCase() })} />
          <button className="border rounded px-3 py-1 text-xs">Add</button>
        </form>
        <div className="overflow-x-auto"><table className="min-w-full text-xs"><thead><tr className="text-left text-gray-500"><th className="py-1">Platform</th><th>Account</th><th>Currency</th><th>Status</th><th>Last sync</th><th /></tr></thead>
          <tbody>{accts.map((a) => (
            <tr key={a.id} className="border-t"><td className="py-1">{LABEL[a.provider]}</td><td>{a.name} <span className="text-gray-400">{a.external_id}</span></td><td>{a.currency}</td>
              <td>{a.status}{a.last_error && <div className="text-red-600">{a.last_error}</div>}</td>
              <td>{a.last_sync_at ? new Date(a.last_sync_at).toLocaleString() : "never"}</td>
              <td className="text-right"><button className="underline" onClick={() => run(() => apiClient.post(`/api/v1/ads/accounts/${a.id}/sync`, null, { params: { days: 7 } }), "Synced the last 7 days.")}>Sync 7 days</button></td></tr>))}</tbody></table>
          {accts.length === 0 && <p className="text-xs text-gray-500 py-1">No ad accounts yet.</p>}</div>
      </section>

      <section className="border rounded p-3 bg-white overflow-x-auto">
        <h3 className="font-semibold mb-1">Performance, last 30 days</h3>
        {perf.length === 0 ? <p className="text-xs text-gray-500">No synced data.</p> :
          <table className="min-w-full text-xs"><thead><tr className="text-left text-gray-500"><th className="py-1">Campaign</th><th>Platform</th><th>Spend</th><th>Impr.</th><th>Clicks</th><th>CTR</th><th>CPC</th><th>Conv.</th><th>Cost/conv.</th></tr></thead>
            <tbody>{perf.map((p) => (
              <tr key={`${p.account}-${p.campaign_id}`} className="border-t"><td className="py-1">{p.campaign}</td><td>{LABEL[p.provider]}</td><td>{p.currency} {p.spend.toLocaleString()}</td>
                <td>{p.impressions.toLocaleString()}</td><td>{p.clicks}</td><td>{p.ctr != null ? `${(p.ctr * 100).toFixed(2)}%` : "—"}</td>
                <td>{p.cpc ?? "—"}</td><td>{p.conversions}</td><td>{p.cost_per_conversion ?? "—"}</td></tr>))}</tbody></table>}
        <p className="text-xs text-gray-500 mt-1">Conversions are as reported by each platform (their attribution rules differ).</p>
      </section>

      <section className="border rounded p-3 bg-white space-y-2">
        <h3 className="font-semibold">Campaign drafts</h3>
        <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault();
          run(() => apiClient.post("/api/v1/ads/drafts", { account_id: nd.account_id, name: nd.name, objective: nd.objective, daily_budget: nd.daily_budget, idempotency_key: nd.idem })
            .then(() => setNd({ ...nd, name: "", idem: key() })), "Draft saved."); }}>
          <select aria-label="Draft account" required className={input} value={nd.account_id} onChange={(e) => setNd({ ...nd, account_id: e.target.value })}>
            <option value="">Account…</option>{accts.map((a) => <option key={a.id} value={a.id}>{LABEL[a.provider]} · {a.name}</option>)}</select>
          <input aria-label="Draft name" required placeholder="Campaign name" className={input} value={nd.name} onChange={(e) => setNd({ ...nd, name: e.target.value })} />
          <input aria-label="Objective" required className={input} value={nd.objective} onChange={(e) => setNd({ ...nd, objective: e.target.value.toUpperCase() })} />
          <input aria-label="Daily budget" required type="number" min="0.01" step="0.01" className={`${input} w-24`} value={nd.daily_budget} onChange={(e) => setNd({ ...nd, daily_budget: e.target.value })} />
          <button className="border rounded px-3 py-1 text-xs">Save draft</button>
        </form>
        <ul className="text-xs space-y-1">{drafts.map((d) => (
          <li key={d.id} className="border-t pt-1 flex flex-wrap gap-2 items-center"><b>{d.name}</b><span>{d.objective} · {d.daily_budget}/day · {d.status.toLowerCase()}</span>
            {d.validation && <span className={d.validation.ok === false ? "text-red-600" : "text-emerald-700"}>{d.validation.ok === false ? `Not valid: ${(d.validation.problems ?? []).join(" ") || "see platform response"}` : d.validation.provider_checked ? "Checked by the platform" : "Passed local checks"}</span>}
            {(d.status === "DRAFT" || d.status === "REJECTED") && <button className="underline" onClick={() => run(() => apiClient.post(`/api/v1/ads/drafts/${d.id}/request`), "Sent for approval.")}>Request approval</button>}
            {d.status === "PENDING" && <><button className="underline" onClick={() => run(() => apiClient.post(`/api/v1/ads/drafts/${d.id}/approve`), "Approved.")}>Approve</button>
              <button className="underline" onClick={() => run(() => apiClient.post(`/api/v1/ads/drafts/${d.id}/reject`), "Rejected.")}>Reject</button></>}
            <button className="underline" onClick={() => run(() => apiClient.post(`/api/v1/ads/drafts/${d.id}/validate`), "Validated.")}>Validate</button>
          </li>))}</ul>
      </section>
    </div>
  );
}
