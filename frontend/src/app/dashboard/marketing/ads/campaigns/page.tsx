"use client";
// M48.S01.T001–T004 ad campaign builder: provider campaign trees created paused, second-person approvals bound to the
// budget version, fail-closed LIVE/SIMULATED gate, mutation ledger and reconciliation.
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  adCampaignsApi, AdAccountControls, AdAccountInfo, AdCampaignTree, AdMutationRow, AdProvider, AdProviderInfo, AdTreeAction,
} from "@/lib/marketingApi";

const LABEL: Record<AdProvider, string> = { meta: "Meta", google: "Google Ads", linkedin: "LinkedIn", tiktok: "TikTok" };
type Field = { k: string; label: string; list?: boolean; lines?: boolean; def?: string; type?: string };
const FIELDS: Record<AdProvider, Field[]> = {
  meta: [{ k: "page_id", label: "Facebook Page id" }, { k: "link", label: "Link (https)" }, { k: "message", label: "Ad text" },
    { k: "headline", label: "Headline" }, { k: "country", label: "Country (2 letters)", def: "KE" }],
  google: [{ k: "final_url", label: "Final URL (https)" }, { k: "headlines", label: "Headlines (3–15, one per line, ≤30 chars)", list: true, lines: true },
    { k: "descriptions", label: "Descriptions (2–4, one per line, ≤90 chars)", list: true, lines: true },
    { k: "cpc_bid", label: "Max CPC bid", type: "number" }],
  linkedin: [{ k: "share_urn", label: "Post URN (urn:li:share:…)" }, { k: "geo_urn", label: "Location URN (urn:li:geo:…)" },
    { k: "unit_cost", label: "Bid (unit cost)", type: "number" }],
  tiktok: [{ k: "location_ids", label: "Location ids (comma separated)", list: true }, { k: "video_id", label: "Uploaded video_id" },
    { k: "identity_id", label: "Identity id" }, { k: "ad_text", label: "Ad text (≤100)" }, { k: "landing_page_url", label: "Landing page (https)" }],
};
const ACTION_LABEL: Partial<Record<AdTreeAction, string>> = {
  validate: "Validate", request_submit: "Request approval", submit: "Submit (paused)", request_resume: "Request resume approval",
  resume: "Resume", pause: "Pause", request_budget: "Request budget approval", reconcile: "Reconcile",
};
const err = (e: unknown) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : d && typeof d === "object" && "detail" in d ? String((d as { detail: unknown }).detail) : "Request failed.";
};
const newKey = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const input = "border rounded px-2 py-1 text-xs bg-white text-gray-900";

function ModeBadge({ mode }: { mode: "LIVE" | "SIMULATED" }) {
  return <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${mode === "LIVE" ? "bg-red-600 text-white" : "bg-amber-100 text-amber-900"}`}>{mode}</span>;
}

export default function AdCampaignBuilder() {
  const { user } = useAuth();
  const isAdmin = Boolean((user as { is_superuser?: boolean } | null)?.is_superuser);
  const [providers, setProviders] = useState<AdProviderInfo[]>([]);
  const [accounts, setAccounts] = useState<AdAccountInfo[]>([]);
  const [aid, setAid] = useState("");
  const [ctrl, setCtrl] = useState<AdAccountControls | null>(null);
  const [trees, setTrees] = useState<AdCampaignTree[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const acct = accounts.find((a) => a.id === aid);
  const prov = providers.find((p) => p.provider === acct?.provider);

  const load = useCallback(async () => {
    try {
      const [p, a] = await Promise.all([adCampaignsApi.providers(), adCampaignsApi.accounts()]);
      setProviders(p.data); setAccounts(a.data);
      const cur = aid || a.data[0]?.id || "";
      if (!aid && cur) setAid(cur);
      if (cur) {
        const [c, t] = await Promise.all([adCampaignsApi.controls(cur), adCampaignsApi.list(cur)]);
        setCtrl(c.data); setTrees(t.data);
      }
    } catch (e) { setMsg(err(e)); }
  }, [aid]);
  useEffect(() => { load(); }, [load]);

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setMsg(null);
    try { await fn(); setMsg(ok); } catch (e) { setMsg(err(e)); }
    setBusy(false); load();
  };

  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">Ad campaign builder</h2>
        <Link href="/dashboard/crm/ads" className="text-xs underline">Ads reporting</Link>
      </div>
      <p className="text-xs text-gray-500">Campaigns are created on the platform paused (Meta/Google PAUSED, LinkedIn DRAFT, TikTok DISABLE) after a
        second person approves the exact version. Going live needs a separate resume approval. Changes run in SIMULATED mode unless provider
        traffic is live, ADS_LIVE_MUTATIONS is on, an admin activated the account and credentials are set.</p>
      {msg && <p role="status" className="text-xs border rounded p-2 bg-gray-50 text-gray-900">{msg}</p>}

      <section className="border rounded p-3 bg-white text-gray-900 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs" htmlFor="acct">Ad account</label>
          <select id="acct" className={input} value={aid} onChange={(e) => setAid(e.target.value)}>
            {accounts.length === 0 && <option value="">No ad accounts — add one under Ads reporting</option>}
            {accounts.map((a) => <option key={a.id} value={a.id}>{LABEL[a.provider]} · {a.name} ({a.currency})</option>)}
          </select>
          {ctrl && <ModeBadge mode={ctrl.mode} />}
          {ctrl && <span className="text-xs text-gray-500">{ctrl.transport === "http" ? "Adapter calls the configured endpoint" : "Nothing is sent (offline simulation)"}</span>}
        </div>
        {ctrl && ctrl.live_blockers.length > 0 && <ul className="text-xs text-amber-800 list-disc ml-5">{ctrl.live_blockers.map((b) => <li key={b}>{b}</li>)}</ul>}
        {ctrl && <p className="text-xs">Caps: {ctrl.daily_cap ?? "not set"} / day, {ctrl.monthly_cap ?? "not set"} / month · Members: {ctrl.members.join(", ") || "none"} · Activation: {ctrl.activated ? `on (by ${ctrl.activated_by})` : "off"}</p>}
        {ctrl && acct && <AdminControls ctrl={ctrl} isAdmin={isAdmin} busy={busy} run={run} aid={acct.id} />}
      </section>

      {acct && prov && <Wizard key={acct.id} acct={acct} prov={prov} busy={busy} run={run} />}

      <section className="space-y-3">
        <h3 className="font-semibold">Campaigns</h3>
        {trees.length === 0 && <p className="text-xs text-gray-500">No campaigns on this account yet.</p>}
        {trees.map((t) => <TreeCard key={t.id} t={t} busy={busy} run={run} />)}
      </section>
    </div>
  );
}

function AdminControls({ ctrl, isAdmin, busy, run, aid }: { ctrl: AdAccountControls; isAdmin: boolean; busy: boolean; aid: string;
  run: (fn: () => Promise<unknown>, ok: string) => void }) {
  const [daily, setDaily] = useState(String(ctrl.daily_cap ?? ""));
  const [monthly, setMonthly] = useState(String(ctrl.monthly_cap ?? ""));
  const [members, setMembers] = useState(ctrl.members.join(", "));
  const why = isAdmin ? null : "Admins only.";
  return (
    <form className="flex flex-wrap gap-2 items-end" onSubmit={(e) => { e.preventDefault();
      run(() => adCampaignsApi.setControls(aid, { daily_cap: daily, monthly_cap: monthly, members: members.split(",").map((m) => m.trim()).filter(Boolean) }), "Controls saved."); }}>
      <label className="text-xs">Daily cap<input aria-label="Daily cap" type="number" min="0.01" step="0.01" className={`${input} w-24 block`} value={daily} onChange={(e) => setDaily(e.target.value)} disabled={!isAdmin} /></label>
      <label className="text-xs">Monthly cap<input aria-label="Monthly cap" type="number" min="0.01" step="0.01" className={`${input} w-28 block`} value={monthly} onChange={(e) => setMonthly(e.target.value)} disabled={!isAdmin} /></label>
      <label className="text-xs">Members (usernames)<input aria-label="Members" className={`${input} w-64 block`} value={members} onChange={(e) => setMembers(e.target.value)} disabled={!isAdmin} /></label>
      <button className="border rounded px-3 py-1 text-xs disabled:opacity-50" disabled={!isAdmin || busy} title={why ?? ""}>Save controls</button>
      <button type="button" className="border rounded px-3 py-1 text-xs disabled:opacity-50" disabled={!isAdmin || busy} title={why ?? ""}
        onClick={() => run(() => adCampaignsApi.activate(aid, !ctrl.activated), ctrl.activated ? "Account deactivated." : "Account activated (live still needs the global switches).")}>
        {ctrl.activated ? "Deactivate live changes" : "Activate live changes"}</button>
      {why && <span className="text-xs text-gray-500">{why}</span>}
    </form>
  );
}

function Wizard({ acct, prov, busy, run }: { acct: AdAccountInfo; prov: AdProviderInfo; busy: boolean;
  run: (fn: () => Promise<unknown>, ok: string) => void }) {
  const fields = FIELDS[acct.provider];
  const blank = useMemo(() => Object.fromEntries(fields.map((f) => [f.k, f.def ?? ""])), [fields]);
  const [name, setName] = useState("");
  const [objective, setObjective] = useState(prov.objectives[0]);
  const [budget, setBudget] = useState(String(Math.max(20, !prov.min_budget_currency || prov.min_budget_currency === acct.currency ? prov.min_daily_budget ?? 0 : 0)));
  const [start, setStart] = useState("");
  const [spec, setSpec] = useState<Record<string, string>>(blank);
  const [key, setKey] = useState(newKey());
  const minApplies = prov.min_daily_budget !== null && (!prov.min_budget_currency || prov.min_budget_currency === acct.currency);
  const toSpec = () => {
    const out: Record<string, unknown> = {};
    for (const f of fields) {
      const v = spec[f.k] ?? "";
      out[f.k] = f.list ? v.split(f.lines ? "\n" : ",").map((s) => s.trim()).filter(Boolean) : v.trim();
    }
    if (start) out.start_date = start;
    return out;
  };
  return (
    <section className="border rounded p-3 bg-white text-gray-900 space-y-2">
      <h3 className="font-semibold">New {LABEL[acct.provider]} campaign</h3>
      <p className="text-xs text-gray-500">Creates: {prov.levels.map((l) => l.label).join(" → ")}. Only objectives this builder can complete from documented fields are offered.
        {!prov.write_tier_ok && " LinkedIn Development tier: provider writes are refused until Standard tier."}</p>
      {minApplies && <p className="text-xs text-gray-700">Minimum daily budget: {prov.min_daily_budget} {acct.currency}
        {prov.min_budget_currency ? "" : ` (${LABEL[acct.provider]} documents ${prov.min_daily_budget} USD; applied as ${prov.min_daily_budget} ${acct.currency} because the local-currency minimum is not verified)`}.
        Global guardrail: {prov.guardrail} {acct.currency}/day.</p>}
      {minApplies && (prov.min_daily_budget ?? 0) > prov.guardrail && <p role="alert" className="text-xs text-red-700">The provider minimum is above the
        global guardrail ADS_MAX_DAILY_BUDGET ({prov.guardrail}): no {LABEL[acct.provider]} campaign can be valid until the owner raises the guardrail.</p>}
      <form className="grid grid-cols-1 md:grid-cols-3 gap-2" onSubmit={(e) => { e.preventDefault();
        run(() => adCampaignsApi.create({ account_id: acct.id, idempotency_key: key, name, objective, daily_budget: budget, spec: toSpec() })
          .then(() => { setName(""); setSpec(blank); setKey(newKey()); }), "Campaign draft created (paused, not sent).");
      }}>
        <label className="text-xs">Campaign name<input required maxLength={150} className={`${input} w-full block`} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="text-xs">Objective<select className={`${input} w-full block`} value={objective} onChange={(e) => setObjective(e.target.value)}>
          {prov.objectives.map((o) => <option key={o} value={o}>{o}</option>)}</select></label>
        <label className="text-xs">Daily budget ({acct.currency})<input required type="number" min="0.01" step="0.01" className={`${input} w-full block`} value={budget} onChange={(e) => setBudget(e.target.value)} /></label>
        <label className="text-xs">Start date<input type="date" className={`${input} w-full block`} value={start} onChange={(e) => setStart(e.target.value)} /></label>
        {fields.map((f) => (
          <label key={f.k} className="text-xs">{f.label}
            {f.lines ? <textarea rows={3} className={`${input} w-full block`} value={spec[f.k] ?? ""} onChange={(e) => setSpec({ ...spec, [f.k]: e.target.value })} />
              : <input type={f.type ?? "text"} step={f.type === "number" ? "0.01" : undefined} className={`${input} w-full block`} value={spec[f.k] ?? ""} onChange={(e) => setSpec({ ...spec, [f.k]: e.target.value })} />}
          </label>))}
        <div className="md:col-span-3"><button className="border rounded px-3 py-1 text-xs bg-indigo-600 text-white disabled:opacity-50" disabled={busy || !name}>Create paused draft</button></div>
      </form>
    </section>
  );
}

function TreeCard({ t, busy, run }: { t: AdCampaignTree; busy: boolean; run: (fn: () => Promise<unknown>, ok: string) => void }) {
  const [budget, setBudget] = useState(String(t.daily_budget));
  const [ledger, setLedger] = useState<AdMutationRow[] | null>(null);
  const btn = (act: AdTreeAction, fn: () => Promise<unknown>, ok: string) => {
    const why = t.actions[act];
    return (
      <span key={act} className="inline-flex flex-col">
        <button className="border rounded px-2 py-1 text-xs disabled:opacity-40" disabled={busy || why !== null} title={why ?? ""} onClick={() => run(fn, ok)}>{ACTION_LABEL[act]}</button>
        {why && <span className="text-[10px] text-gray-500 max-w-[11rem]">{why}</span>}
      </span>);
  };
  return (
    <article className="border rounded p-3 bg-white text-gray-900 space-y-2">
      <header className="flex flex-wrap items-center gap-2">
        <b>{t.name}</b><ModeBadge mode={t.mode} />
        <span className="text-xs border rounded px-1">{t.status}</span>
        <span className="text-xs text-gray-500">{LABEL[t.provider]} · {t.objective} · {t.daily_budget} {t.currency}/day · budget v{t.budget_version} (sent v{t.budget_pushed})</span>
      </header>
      {t.last_error && <p className="text-xs text-red-700">{t.last_error}</p>}
      {t.pending_unknown > 0 && <p className="text-xs text-red-700">{t.pending_unknown} provider call(s) with unknown outcome — reconcile before anything else.</p>}
      {t.validation && <p className={`text-xs ${t.validation.ok ? "text-emerald-700" : "text-red-700"}`}>
        {t.validation.ok ? (t.validation.provider_checked ? "Checked by the platform's validate-only call." : "Passed local checks (no platform validate-only for this provider).")
          : `Not valid: ${t.validation.problems.join(" ")}`}</p>}

      <ul className="text-xs space-y-1" aria-label="Campaign tree">
        {t.nodes.map((n, i) => (
          <li key={n.id} style={{ paddingLeft: `${i * 16}px` }} className="flex flex-wrap gap-2">
            <span className="text-gray-400">{i === 0 ? "■" : "└"}</span><b>{n.label}</b><span>{n.provider_name}</span>
            <span className="text-gray-500">{n.provider_id ? `id ${n.provider_id}` : "not created"}</span>
            {n.provider_status && <span className="border rounded px-1">{n.provider_status}</span>}
            {n.last_error && <span className="text-red-700">{n.last_error}</span>}
          </li>))}
      </ul>

      <div className="flex flex-wrap gap-2 items-start">
        {btn("validate", () => adCampaignsApi.run(t.id, "validate"), "Validated.")}
        {btn("request_submit", () => adCampaignsApi.requestApproval(t.id, "SUBMIT"), "Approval requested.")}
        {btn("submit", () => adCampaignsApi.run(t.id, "submit"), "Submitted.")}
        {btn("request_resume", () => adCampaignsApi.requestApproval(t.id, "RESUME"), "Resume approval requested.")}
        {btn("resume", () => adCampaignsApi.run(t.id, "resume"), "Resume sent.")}
        {btn("pause", () => adCampaignsApi.run(t.id, "pause"), "Paused.")}
        {btn("request_budget", () => adCampaignsApi.requestApproval(t.id, "BUDGET"), "Budget approval requested.")}
        {btn("reconcile", () => adCampaignsApi.run(t.id, "reconcile"), "Reconciled by read-back.")}
      </div>

      <form className="flex flex-wrap gap-2 items-center" onSubmit={(e) => { e.preventDefault();
        run(() => adCampaignsApi.budget(t.id, budget), "New budget version saved; it needs approval."); }}>
        <label className="text-xs">Daily budget<input aria-label={`Daily budget for ${t.name}`} type="number" min="0.01" step="0.01" className={`${input} w-24 ml-1`} value={budget} onChange={(e) => setBudget(e.target.value)} /></label>
        <button className="border rounded px-2 py-1 text-xs disabled:opacity-40" disabled={busy || t.actions.edit_budget !== null} title={t.actions.edit_budget ?? ""}>Edit budget (new version)</button>
        {t.actions.edit_budget && <span className="text-[10px] text-gray-500">{t.actions.edit_budget}</span>}
      </form>

      {t.approvals.length > 0 && <table className="text-xs min-w-full"><thead><tr className="text-left text-gray-500"><th>Approval</th><th>Version</th><th>Budget</th><th>Hash</th><th>Status</th><th>By</th><th /></tr></thead>
        <tbody>{t.approvals.map((a) => (
          <tr key={a.id} className="border-t"><td>{a.action}</td><td>v{a.budget_version}</td><td>{a.daily_budget}</td><td className="font-mono">{a.hash}</td>
            <td>{a.status}</td><td>{a.requested_by}{a.decided_by ? ` → ${a.decided_by}` : ""}</td>
            <td className="text-right">{a.status === "PENDING" && <>
              <button className="underline mr-2 disabled:opacity-40" disabled={busy || t.actions.approve !== null} title={t.actions.approve ?? ""} onClick={() => run(() => adCampaignsApi.decide(a.id, true), "Approved.")}>Approve</button>
              <button className="underline disabled:opacity-40" disabled={busy || t.actions.approve !== null} title={t.actions.approve ?? ""} onClick={() => run(() => adCampaignsApi.decide(a.id, false), "Rejected.")}>Reject</button>
              {t.actions.approve && <div className="text-[10px] text-gray-500">{t.actions.approve}</div>}</>}</td></tr>))}</tbody></table>}

      <button className="text-xs underline" onClick={async () => setLedger(ledger ? null : (await adCampaignsApi.mutations(t.id)).data)}>{ledger ? "Hide" : "Show"} provider call ledger</button>
      {ledger && <table className="text-xs min-w-full"><thead><tr className="text-left text-gray-500"><th>Operation</th><th>Mode</th><th>State</th><th>Provider id</th><th>Attempts</th><th>Error</th></tr></thead>
        <tbody>{ledger.map((m) => <tr key={m.id} className="border-t"><td>{m.operation}</td><td>{m.mode}</td><td>{m.state}</td><td>{m.provider_id ?? "—"}</td><td>{m.attempts}</td><td className="text-red-700">{m.error ?? ""}</td></tr>)}</tbody></table>}
    </article>
  );
}
