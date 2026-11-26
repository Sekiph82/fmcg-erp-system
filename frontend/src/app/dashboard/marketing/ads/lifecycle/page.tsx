"use client";
// M49.S01.T006 unified advertising lifecycle: every ad account the user may act on, account -> campaign -> ad set / ad group
// -> creative / ad, with status read-back, schedules, approved edits through the M48 ledger and per-node reporting.
// Create / approve / submit / pause / resume run on the M48 endpoints; each button shows why it is disabled.
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";

type Provider = "meta" | "google" | "linkedin" | "tiktok";
const LABEL: Record<Provider, string> = { meta: "Meta", google: "Google Ads", linkedin: "LinkedIn", tiktok: "TikTok" };
interface Report { available: boolean; reason?: string; note?: string | null; rows?: number; impressions?: number; clicks?: number; spend?: number;
  conversions?: number; ctr?: number | null; cpc?: number | null; last_day?: string | null; last_sync_at?: string | null }
interface Edit { id: string; fields: Record<string, string>; status: string; mode: string | null; requested_by: string; decided_by: string | null;
  read_back: { observed?: Record<string, string | null>; diffs?: string[]; note?: string; error?: string } | null; last_error: string | null }
interface Node { id: string; level: string; label: string; name: string; provider_id: string | null; provider_status: string | null; status: string;
  last_error: string | null; last_read_at: string | null; report: Report; edits: Edit[]; editable: string[]; edit_disabled: string | null; unverified: string[] }
interface Approval { id: string; action: string; status: string; requested_by: string; budget_version: number }
interface Campaign { id: string; name: string; objective: string; status: string; mode: "LIVE" | "SIMULATED"; transport: string; daily_budget: number;
  budget_version: number; budget_pushed: number; last_error: string | null; live_blockers: string[]; nodes: Node[]; approvals: Approval[];
  actions: Record<string, string | null>; validation: { ok: boolean; problems: string[] } | null }
interface Controls { activated: boolean; activated_by: string | null; daily_cap: number | null; monthly_cap: number | null; members: string[];
  mode: "LIVE" | "SIMULATED"; transport: string; live_blockers: string[] }
interface Row { account: { id: string; provider: Provider; name: string; currency: string; status: string; last_sync_at: string | null };
  controls: Controls; member: boolean; refusal: string | null; campaigns: Campaign[] }
interface Wizard { provider: Provider; objectives: string[]; fields: { key: string; label: string; kind: string; required: boolean; hint: string }[];
  not_offered: string; budget_note: string | null; editable_note: string | null }

const err = (e: unknown) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : d && typeof d === "object" && "detail" in d ? String((d as { detail: unknown }).detail)
    : e instanceof Error && e.message ? e.message : "Request failed.";
};
const key = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const input = "border rounded px-2 py-1 text-xs bg-white text-gray-900";
const btn = "text-xs border rounded px-2 py-1 bg-white text-gray-900 disabled:opacity-40 disabled:cursor-not-allowed";
const chip = (s: string) => `text-[10px] font-semibold px-2 py-0.5 rounded ${
  ["APPLIED", "ACTIVE", "READY"].includes(s) ? "bg-green-100 text-green-900" : ["FAILED", "REJECTED", "UNKNOWN", "UNCONFIRMED"].includes(s) ? "bg-red-100 text-red-900" : "bg-amber-100 text-amber-900"}`;

export default function AdsLifecycle() {
  const [rows, setRows] = useState<Row[]>([]);
  const [wizard, setWizard] = useState<Wizard[]>([]);
  const [canApprove, setCanApprove] = useState(false);
  const [days, setDays] = useState(30);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [t, w] = await Promise.all([apiClient.get(`/api/v1/ads-lifecycle/tree?days=${days}`), apiClient.get("/api/v1/ads-lifecycle/wizard")]);
      setRows(t.data.accounts); setCanApprove(t.data.can_approve); setWizard(w.data);
    } catch (e) { setMsg(err(e)); }
  }, [days]);
  useEffect(() => { load(); }, [load]);

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setMsg(null);
    try { await fn(); setMsg(ok); } catch (e) { setMsg(err(e)); }
    setBusy(false); load();
  };

  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">Advertising lifecycle</h2>
        <Link href="/dashboard/marketing/ads/campaigns" className="text-xs underline">Campaign builder and account controls</Link>
        <Link href="/dashboard/crm/ads" className="text-xs underline">Ads reporting</Link>
        <label className="text-xs ml-auto">Reporting window
          <select className={`${input} ml-1`} value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Reporting window">
            {[7, 30, 90].map((d) => <option key={d} value={d}>{d} days</option>)}
          </select>
        </label>
      </div>
      <p className="text-xs text-gray-500">Objects are created paused and changed only after a second person approves the exact change. SIMULATED means
        nothing reached a real platform (or only the local simulator did); LIVE needs the egress, ADS_LIVE_MUTATIONS, admin activation and credentials switches.
        Reporting comes from the performance sync and exists at campaign level only.</p>
      {msg && <p role="status" className="text-xs border rounded p-2 bg-gray-50 text-gray-900">{msg}</p>}
      {rows.length === 0 && <p className="text-xs text-gray-500">No ad accounts yet. Add one under Ads reporting.</p>}
      {rows.map((r) => <AccountBlock key={r.account.id} r={r} wiz={wizard.find((w) => w.provider === r.account.provider)}
        canApprove={canApprove} busy={busy} run={run} />)}
    </div>
  );
}

function AccountBlock({ r, wiz, canApprove, busy, run }: { r: Row; wiz?: Wizard; canApprove: boolean; busy: boolean;
  run: (fn: () => Promise<unknown>, ok: string) => void }) {
  const [open, setOpen] = useState(false);
  const c = r.controls;
  return (
    <section className="border rounded bg-white text-gray-900 p-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{LABEL[r.account.provider]} · {r.account.name} ({r.account.currency})</h3>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${c.mode === "LIVE" ? "bg-red-600 text-white" : "bg-amber-100 text-amber-900"}`}>{c.mode}</span>
        <span className="text-xs text-gray-500">Activation: {c.activated ? `on (${c.activated_by})` : "off"} · Caps {c.daily_cap ?? "not set"}/day, {c.monthly_cap ?? "not set"}/month</span>
        {r.member && <button className={btn} disabled={busy} onClick={() => run(() => apiClient.post(`/api/v1/ads/accounts/${r.account.id}/sync?days=7`), "Reporting synced.")}>Sync reporting</button>}
        {r.member && wiz && <button className={btn} onClick={() => setOpen(!open)}>{open ? "Close wizard" : "New campaign"}</button>}
      </div>
      {!r.member && <p role="alert" className="text-xs border border-red-300 bg-red-50 text-red-900 rounded p-2">Refused for you: {r.refusal}</p>}
      {c.live_blockers.length > 0 && <ul className="text-xs text-amber-800 list-disc ml-5">{c.live_blockers.map((b) => <li key={b}>{b}</li>)}</ul>}
      {r.member && open && wiz && <Wizard r={r} wiz={wiz} busy={busy} run={run} done={() => setOpen(false)} />}
      {r.member && r.campaigns.length === 0 && <p className="text-xs text-gray-500">No campaigns on this account.</p>}
      {r.campaigns.map((cm) => <CampaignBlock key={cm.id} cm={cm} canApprove={canApprove} busy={busy} run={run} />)}
    </section>
  );
}

function Wizard({ r, wiz, busy, run, done }: { r: Row; wiz: Wizard; busy: boolean; done: () => void;
  run: (fn: () => Promise<unknown>, ok: string) => void }) {
  const [name, setName] = useState("");
  const [objective, setObjective] = useState(wiz.objectives[0]);
  const [budget, setBudget] = useState("");
  const [spec, setSpec] = useState<Record<string, string>>({});
  const build = () => {
    const out: Record<string, string | string[]> = {};
    for (const f of wiz.fields) {
      const v = (spec[f.key] ?? "").trim();
      if (!v) continue;
      out[f.key] = f.kind === "list" ? v.split(f.key === "headlines" || f.key === "descriptions" ? "\n" : ",").map((x) => x.trim()).filter(Boolean) : v;
    }
    return out;
  };
  return (
    <form className="border rounded p-2 space-y-2 bg-gray-50" onSubmit={(e) => { e.preventDefault();
      run(async () => { await apiClient.post("/api/v1/ads/campaigns", { account_id: r.account.id, idempotency_key: key(), name, objective, daily_budget: budget, spec: build() }); done(); },
        "Draft created. Validate it, then request approval."); }}>
      <p className="text-xs text-gray-600">Offered types: {wiz.objectives.join(", ")}. Not offered: {wiz.not_offered}</p>
      {wiz.budget_note && <p className="text-xs text-gray-600">{wiz.budget_note}</p>}
      <div className="flex flex-wrap gap-2 items-end">
        <label className="text-xs">Name<input className={`${input} block w-56`} value={name} onChange={(e) => setName(e.target.value)} required maxLength={150} /></label>
        <label className="text-xs">Type<select className={`${input} block`} value={objective} onChange={(e) => setObjective(e.target.value)}>
          {wiz.objectives.map((o) => <option key={o}>{o}</option>)}</select></label>
        <label className="text-xs">Daily budget ({r.account.currency})<input className={`${input} block w-28`} type="number" min="0.01" step="0.01" value={budget}
          onChange={(e) => setBudget(e.target.value)} required /></label>
      </div>
      <div className="grid sm:grid-cols-2 gap-2">
        {wiz.fields.map((f) => (
          <label key={f.key} className="text-xs">{f.label}{f.required ? " *" : ""} <span className="text-gray-400">{f.hint}</span>
            {f.kind === "list" && (f.key === "headlines" || f.key === "descriptions")
              ? <textarea className={`${input} block w-full`} rows={3} value={spec[f.key] ?? ""} onChange={(e) => setSpec({ ...spec, [f.key]: e.target.value })} />
              : <input className={`${input} block w-full`} type={f.kind === "number" ? "number" : "text"} step="any" value={spec[f.key] ?? ""}
                  onChange={(e) => setSpec({ ...spec, [f.key]: e.target.value })} />}
          </label>
        ))}
      </div>
      <button className={btn} disabled={busy || !name || !budget}>Create draft</button>
    </form>
  );
}

const ACTION: [string, string][] = [["validate", "Validate"], ["request_submit", "Request approval"], ["submit", "Submit (paused)"], ["request_budget", "Request budget approval"],
  ["request_resume", "Request resume approval"], ["resume", "Resume"], ["pause", "Pause"], ["reconcile", "Reconcile"]];

function CampaignBlock({ cm, canApprove, busy, run }: { cm: Campaign; canApprove: boolean; busy: boolean; run: (fn: () => Promise<unknown>, ok: string) => void }) {
  const base = `/api/v1/ads/campaigns/${cm.id}`;
  const pending = cm.approvals.find((a) => a.status === "PENDING");
  const call = (a: string) => {
    if (a === "request_submit") return apiClient.post(`${base}/approvals`, { action: "SUBMIT" });
    if (a === "request_budget") return apiClient.post(`${base}/approvals`, { action: "BUDGET" });
    if (a === "request_resume") return apiClient.post(`${base}/approvals`, { action: "RESUME" });
    return apiClient.post(`${base}/${a}`);
  };
  const [budget, setBudget] = useState("");
  return (
    <div className="border rounded p-2 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{cm.name}</span><span className={chip(cm.status)}>{cm.status}</span>
        <span className={`text-[10px] px-2 py-0.5 rounded ${cm.mode === "LIVE" ? "bg-red-600 text-white" : "bg-amber-100 text-amber-900"}`}>{cm.mode}</span>
        <span className="text-xs text-gray-500">{cm.objective} · {cm.daily_budget}/day (version {cm.budget_version}, sent {cm.budget_pushed}) · {cm.transport === "http" ? "adapter calls the configured endpoint" : "nothing is sent (offline)"}</span>
      </div>
      {cm.last_error && <p className="text-xs text-red-700">Last error: {cm.last_error}</p>}
      {cm.validation && <p className="text-xs">{cm.validation.ok ? "Validation passed." : `Validation: ${cm.validation.problems.join(" ")}`}</p>}
      <div className="flex flex-wrap gap-1 items-center">
        {ACTION.map(([a, label]) => <button key={a} className={btn} disabled={busy || cm.actions[a] !== null} title={cm.actions[a] ?? ""}
          onClick={() => run(() => call(a), `${label}: done.`)}>{label}</button>)}
        <button className={btn} disabled={busy || !pending || !canApprove || cm.actions.approve !== null} title={cm.actions.approve ?? ""}
          onClick={() => pending && run(() => apiClient.post(`/api/v1/ads/approvals/${pending.id}/decide`, { ok: true }), "Approved.")}>Approve {pending?.action.toLowerCase() ?? ""}</button>
        <button className={btn} disabled={busy || !pending || !canApprove || cm.actions.approve !== null} title={cm.actions.approve ?? ""}
          onClick={() => pending && run(() => apiClient.post(`/api/v1/ads/approvals/${pending.id}/decide`, { ok: false }), "Rejected.")}>Reject</button>
        <input aria-label="New daily budget" className={`${input} w-24`} type="number" min="0.01" step="0.01" placeholder="New budget" value={budget} onChange={(e) => setBudget(e.target.value)} />
        <button className={btn} disabled={busy || !budget || cm.actions.edit_budget !== null} title={cm.actions.edit_budget ?? ""}
          onClick={() => run(() => apiClient.post(`${base}/budget`, { daily_budget: budget }), "New budget version saved; it needs approval.")}>Save budget version</button>
      </div>
      <table className="w-full text-xs">
        <thead><tr className="text-left text-gray-500"><th>Object</th><th>Provider status</th><th>Schedule</th><th>Reporting</th><th /></tr></thead>
        <tbody>{cm.nodes.map((n) => <NodeRow key={n.id} n={n} canApprove={canApprove} busy={busy} run={run} />)}</tbody>
      </table>
    </div>
  );
}

function schedule(n: Node): string {
  const e = [...n.edits].reverse().find((x) => ["APPLIED", "SIMULATED", "UNCONFIRMED"].includes(x.status) && (x.fields.start_date || x.fields.end_date));
  if (!e) return "—";
  const o = e.read_back?.observed;
  const s = o?.start_date ?? e.fields.start_date, en = o?.end_date ?? e.fields.end_date;
  return `${s ?? "…"} → ${en ?? "no end"}${o ? " (read back)" : e.status === "SIMULATED" ? " (simulated, not read back)" : ""}`;
}

function NodeRow({ n, canApprove, busy, run }: { n: Node; canApprove: boolean; busy: boolean; run: (fn: () => Promise<unknown>, ok: string) => void }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState<Record<string, string>>({});
  const rp = n.report;
  const body = Object.fromEntries(Object.entries(f).filter(([k, v]) => v && n.editable.includes(k)));
  return (
    <>
      <tr className="border-t align-top">
        <td className="py-1"><div className="font-medium">{n.label}</div><div>{n.name}</div><div className="text-gray-400">{n.provider_id ?? "not on the provider yet"}</div></td>
        <td>{n.provider_status ?? n.status}{n.last_read_at && <div className="text-gray-400">read {new Date(n.last_read_at).toLocaleString()}</div>}{n.last_error && <div className="text-red-700">{n.last_error}</div>}</td>
        <td>{schedule(n)}</td>
        <td>{rp.available ? (rp.rows ? `${rp.impressions} imp · ${rp.clicks} clicks · spend ${rp.spend} · CTR ${rp.ctr ?? "n/a"} · CPC ${rp.cpc ?? "n/a"} (to ${rp.last_day})` : rp.note) : <span className="text-gray-400">{rp.reason}</span>}</td>
        <td className="whitespace-nowrap">
          <button className={btn} disabled={busy || !n.provider_id} title={n.provider_id ? "" : "Not on the provider yet."}
            onClick={() => run(async () => { const r = await apiClient.post(`/api/v1/ads-lifecycle/nodes/${n.id}/readback`); if (r.data.simulated) throw new Error(r.data.note); }, "Read back from the provider.")}>Read back</button>{" "}
          <button className={btn} disabled={busy || n.edit_disabled !== null} title={n.edit_disabled ?? ""} onClick={() => setOpen(!open)}>Edit</button>
        </td>
      </tr>
      {open && n.editable.length > 0 && (
        <tr><td colSpan={5} className="pb-2">
          <form className="flex flex-wrap gap-2 items-end bg-gray-50 p-2 rounded" onSubmit={(e) => { e.preventDefault();
            run(async () => { await apiClient.post(`/api/v1/ads-lifecycle/nodes/${n.id}/edits`, body); setOpen(false); setF({}); }, "Edit requested; a second person must approve it."); }}>
            {n.editable.includes("name") && <label className="text-xs">Name<input className={`${input} block w-56`} value={f.name ?? ""} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>}
            {n.editable.includes("start_date") && <label className="text-xs">Start date<input type="date" className={`${input} block`} value={f.start_date ?? ""} onChange={(e) => setF({ ...f, start_date: e.target.value })} /></label>}
            {n.editable.includes("end_date") && <label className="text-xs">End date<input type="date" className={`${input} block`} value={f.end_date ?? ""} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></label>}
            {n.unverified.length > 0 && <span className="text-xs text-amber-800">The platform&apos;s update fields for {n.unverified.join(", ")} are unverified; it may refuse.</span>}
            <button className={btn} disabled={busy || Object.keys(body).length === 0}>Request edit</button>
          </form>
        </td></tr>
      )}
      {n.edits.slice(-3).map((e) => (
        <tr key={e.id}><td colSpan={5} className="pb-1 pl-4 text-xs">
          <span className={chip(e.status)}>{e.status}</span> {Object.entries(e.fields).map(([k, v]) => `${k}: ${v}`).join(" · ")} · by {e.requested_by}{e.decided_by ? `, decided by ${e.decided_by}` : ""}
          {e.read_back?.diffs && e.read_back.diffs.length > 0 && <span className="text-red-700"> · read-back differs: {e.read_back.diffs.join("; ")}</span>}
          {e.last_error && <span className="text-red-700"> · {e.last_error}</span>}{" "}
          {e.status === "PENDING_APPROVAL" && <>
            <button className={btn} disabled={busy || !canApprove} title={canApprove ? "" : "Needs marketing.approve."} onClick={() => run(() => apiClient.post(`/api/v1/ads-lifecycle/edits/${e.id}/decide`, { ok: true }), "Edit approved.")}>Approve</button>{" "}
            <button className={btn} disabled={busy || !canApprove} onClick={() => run(() => apiClient.post(`/api/v1/ads-lifecycle/edits/${e.id}/decide`, { ok: false }), "Edit rejected.")}>Reject</button></>}
          {["APPROVED", "FAILED"].includes(e.status) && <button className={btn} disabled={busy} onClick={() => run(() => apiClient.post(`/api/v1/ads-lifecycle/edits/${e.id}/apply`), "Edit sent; status read back.")}>Apply</button>}
          {["UNKNOWN", "UNCONFIRMED", "FAILED"].includes(e.status) && <button className={btn} disabled={busy} onClick={() => run(() => apiClient.post(`/api/v1/ads-lifecycle/edits/${e.id}/reconcile`), "Reconciled by read-back.")}>Reconcile</button>}
        </td></tr>
      ))}
    </>
  );
}
