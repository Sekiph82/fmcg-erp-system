"use client";
// M51.S01.T003/T004/T005/T009 SEO workbench: Search Console, technical crawler + vitals, AEO measurement, visitor verification.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { RequirePermission } from "@/components/PermissionGuard";

const P = "/api/v1/seo-pro";
type Json = Record<string, any>;
const box = "rounded-xl bg-[#131c2e] border border-slate-700/50 p-4 space-y-3";
const inp = "bg-[#0b1120] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white";
const btn = "px-3 py-2 rounded-lg bg-indigo-600 text-sm text-white disabled:opacity-50";

function errText(e: any): string {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : d?.message ?? "Request failed.";
}

function useAction() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const run = async (fn: () => Promise<any>, okText = "Done.") => {
    setBusy(true); setMsg(null);
    try { const r = await fn(); setMsg({ ok: true, text: okText }); return r; }
    catch (e) { setMsg({ ok: false, text: errText(e) }); }
    finally { setBusy(false); }
  };
  const note = msg && <p role={msg.ok ? "status" : "alert"} className={`text-sm ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>;
  return { busy, run, note };
}

function Gsc() {
  const { busy, run, note } = useAction();
  const [state, setState] = useState<Json | null>(null);
  const [site, setSite] = useState("");
  const [sites, setSites] = useState<Json[]>([]);
  const [range, setRange] = useState({ start: "", end: "" });
  const [dims, setDims] = useState("query");
  const [country, setCountry] = useState("");
  const [data, setData] = useState<Json | null>(null);
  const [feed, setFeed] = useState("");
  const [subs, setSubs] = useState<Json[]>([]);
  const [inspectUrl, setInspectUrl] = useState("");
  const [inspect, setInspect] = useState<Json | null>(null);
  const loadSubs = useCallback(() => apiClient.get(`${P}/gsc/submissions`).then((r) => setSubs(r.data)).catch(() => setSubs([])), []);
  useEffect(() => { apiClient.get(`${P}/gsc/state`).then((r) => setState(r.data)).catch(() => setState(null)); loadSubs(); }, [loadSubs]);
  const connected = state?.state === "OK";
  return (
    <div className="space-y-4">
      <div className={box}>
        <h2 className="font-semibold">Google Search Console</h2>
        {!state ? <p className="text-sm text-slate-400">Loading...</p> : connected
          ? <p className="text-sm text-slate-300">Connected as {state.account}. Data source: {state.source === "LIVE" ? "Google (live)" : "LOCAL SIMULATOR (not Google data)"}.{state.can_submit_sitemaps ? "" : " Sitemap submission needs the write connection."}</p>
          : <p role="alert" className="text-sm text-amber-400">NOT_CONFIGURED: {state.reasons.join(" ")}</p>}
        <div className="flex flex-wrap gap-2">
          <button className={btn} disabled={busy} onClick={() => run(async () => { const r = await apiClient.get(`${P}/gsc/connect-url`); window.location.href = r.data.authorize_url; }, "Redirecting to Google...")}>Connect (read-only)</button>
          <button className={btn} disabled={busy} onClick={() => run(async () => { const r = await apiClient.get(`${P}/gsc/connect-url`, { params: { write: true } }); window.location.href = r.data.authorize_url; }, "Redirecting to Google...")}>Connect with sitemap submission</button>
          <button className={btn} disabled={busy || !connected} onClick={() => run(async () => { const r = await apiClient.get(`${P}/gsc/sites`); setSites(r.data); if (r.data[0] && !site) setSite(r.data[0].site_url); })}>Load properties</button>
        </div>
        {note}
      </div>
      <div className={box}>
        <h3 className="font-medium">Search analytics</h3>
        <div className="flex flex-wrap gap-2">
          <select aria-label="Property" className={inp} value={site} onChange={(e) => setSite(e.target.value)}><option value="">Property</option>{sites.map((s) => <option key={s.site_url}>{s.site_url}</option>)}</select>
          <input aria-label="Start date" type="date" className={inp} value={range.start} onChange={(e) => setRange({ ...range, start: e.target.value })} />
          <input aria-label="End date" type="date" className={inp} value={range.end} onChange={(e) => setRange({ ...range, end: e.target.value })} />
          <select aria-label="Dimensions" className={inp} value={dims} onChange={(e) => setDims(e.target.value)}>{["query", "page", "country", "device", "date", "query,page"].map((d) => <option key={d}>{d}</option>)}</select>
          <input aria-label="Country filter (3-letter code)" placeholder="Country e.g. ken" maxLength={3} className={`${inp} w-32`} value={country} onChange={(e) => setCountry(e.target.value)} />
          <button className={btn} disabled={busy || !connected || !site || !range.start || !range.end} onClick={() => run(async () => {
            const r = await apiClient.post(`${P}/gsc/analytics`, { site_url: site, start_date: range.start, end_date: range.end, dimensions: dims.split(","), paginate: true,
              filters: country ? [{ dimension: "country", operator: "equals", expression: country }] : [] });
            setData(r.data);
          }, "Fetched.")}>Fetch / refresh</button>
        </div>
        {data && <>
          <p className="text-xs text-slate-400">{data.row_count} rows · source {data.source} · fetched {data.fetched_at}{data.stale ? ` · STALE (${data.stale_reason})` : ""}{data.incomplete_from ? ` · incomplete from ${data.incomplete_from}` : ""}</p>
          <table className="w-full text-sm"><thead><tr className="text-left text-slate-400"><th>Keys</th><th>Clicks</th><th>Impr.</th><th>CTR</th><th>Position</th></tr></thead>
            <tbody>{data.rows.slice(0, 50).map((r: Json, i: number) => <tr key={i} className="border-t border-slate-800"><td>{r.keys.join(" / ")}</td><td>{r.clicks}</td><td>{r.impressions}</td><td>{(r.ctr * 100).toFixed(1)}%</td><td>{r.position.toFixed(1)}</td></tr>)}</tbody></table>
        </>}
      </div>
      <div className={box}>
        <h3 className="font-medium">Sitemaps (a second person approves before anything is sent to Google)</h3>
        <div className="flex flex-wrap gap-2">
          <input aria-label="Sitemap URL" className={`${inp} flex-1 min-w-[16rem]`} placeholder="https://.../sitemap.xml" value={feed} onChange={(e) => setFeed(e.target.value)} />
          <button className={btn} disabled={busy || !site || !feed} onClick={() => run(async () => { await apiClient.post(`${P}/gsc/submissions`, { site_url: site, feedpath: feed }); await loadSubs(); }, "Submission requested; waiting for approval.")}>Request submission</button>
        </div>
        <ul className="text-sm space-y-1">{subs.map((s) => <li key={s.id} className="flex flex-wrap gap-2 items-center">
          <span>{s.feedpath}</span><span className="text-slate-400">{s.status}{s.result ? ` · ${s.result}` : ""}</span>
          {s.status === "PENDING" && <>
            <button className={btn} disabled={busy} onClick={() => run(async () => { await apiClient.post(`${P}/gsc/submissions/${s.id}/decide`, { approve: true }); await loadSubs(); }, "Decision recorded.")}>Approve and submit</button>
            <button className="px-3 py-2 rounded-lg border border-slate-600 text-sm" disabled={busy} onClick={() => run(async () => { await apiClient.post(`${P}/gsc/submissions/${s.id}/decide`, { approve: false }); await loadSubs(); }, "Rejected.")}>Reject</button></>}
          {s.status === "SUBMITTED" && <button className="underline text-sm" onClick={() => run(async () => { const r = await apiClient.get(`${P}/gsc/sitemaps/status`, { params: { site_url: s.site_url, feedpath: s.feedpath } }); setInspect(r.data); }, "Status read from Search Console.")}>Read status</button>}
        </li>)}</ul>
        <div className="flex flex-wrap gap-2">
          <input aria-label="URL to inspect" className={`${inp} flex-1 min-w-[16rem]`} placeholder="URL to inspect" value={inspectUrl} onChange={(e) => setInspectUrl(e.target.value)} />
          <button className={btn} disabled={busy || !connected || !site || !inspectUrl} onClick={() => run(async () => { const r = await apiClient.post(`${P}/gsc/inspect`, { site_url: site, url: inspectUrl }); setInspect(r.data); }, "Inspected.")}>Inspect URL</button>
        </div>
        {inspect && <pre className="text-xs bg-[#0b1120] rounded p-2 overflow-auto">{JSON.stringify(inspect.summary ?? inspect, null, 2)}</pre>}
        {note}
      </div>
    </div>
  );
}

function Crawler() {
  const { busy, run, note } = useAction();
  const [sites, setSites] = useState<Json[]>([]);
  const [origin, setOrigin] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [crawls, setCrawls] = useState<Json[]>([]);
  const [detail, setDetail] = useState<Json | null>(null);
  const [diff, setDiff] = useState<Json | null>(null);
  const [vit, setVit] = useState<Json[]>([]);
  const [csv, setCsv] = useState("keyword,volume,difficulty,cpc,locale,intent\n");
  const [kwSource, setKwSource] = useState("");
  const load = useCallback(() => {
    apiClient.get(`${P}/sites`).then((r) => setSites(r.data)).catch(() => setSites([]));
    apiClient.get(`${P}/crawls`).then((r) => setCrawls(r.data)).catch(() => setCrawls([]));
  }, []);
  useEffect(load, [load]);
  const own = sites.filter((s) => s.kind === "OWN");
  return (
    <div className="space-y-4">
      <div className={box}>
        <h2 className="font-semibold">Authorised sites</h2>
        <p className="text-sm text-slate-400">Only sites listed here are ever fetched. robots.txt is honoured and off-site links are not followed.</p>
        <ul className="text-sm">{sites.map((s) => <li key={s.id} className="flex gap-2">{s.origin} <span className="text-slate-400">{s.kind}</span>
          <button className="underline text-red-400" onClick={() => run(async () => { await apiClient.delete(`${P}/sites/${s.id}`); load(); }, "Removed.")}>Remove</button></li>)}</ul>
        <div className="flex flex-wrap gap-2 items-center">
          <input aria-label="Site origin" className={`${inp} w-72`} placeholder="https://www.example.com" value={origin} onChange={(e) => setOrigin(e.target.value)} />
          <label className="text-sm flex gap-1 items-center"><input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} /> I own this site or am authorised to audit it</label>
          <button className={btn} disabled={busy || !origin || !confirm} onClick={() => run(async () => { await apiClient.post(`${P}/sites`, { origin, kind: "OWN", confirm_authorized: true }); setOrigin(""); load(); }, "Site authorised.")}>Add site</button>
        </div>
        {note}
      </div>
      <div className={box}>
        <h2 className="font-semibold">Crawls</h2>
        <div className="flex flex-wrap gap-2">{own.map((s) => <button key={s.id} className={btn} disabled={busy} onClick={() => run(async () => { const r = await apiClient.post(`${P}/crawl`, { origin: s.origin }); load(); setDetail((await apiClient.get(`${P}/crawls/${r.data.id}`)).data); }, "Crawl finished.")}>Crawl {s.origin}</button>)}
          {own.length === 0 && <p className="text-sm text-slate-400">Authorise a site first.</p>}</div>
        <ul className="text-sm space-y-1">{crawls.map((c, i) => <li key={c.id} className="flex flex-wrap gap-2">
          <span>{c.origin} · {c.status} · {c.summary ? `${c.summary.pages} pages, ${c.summary.errors} errors, ${c.summary.warnings} warnings` : c.error}</span>
          <button className="underline" onClick={() => apiClient.get(`${P}/crawls/${c.id}`).then((r) => setDetail(r.data))}>Open</button>
          {crawls[i + 1] && crawls[i + 1].origin === c.origin && <button className="underline" onClick={() => apiClient.get(`${P}/crawls/compare`, { params: { a: crawls[i + 1].id, b: c.id } }).then((r) => setDiff(r.data))}>Compare with previous</button>}</li>)}</ul>
        {diff && <p className="text-sm" role="status">Resolved {diff.resolved.length} · New {diff.new.length} · Unchanged {diff.unchanged}</p>}
        {detail && <table className="w-full text-sm"><thead><tr className="text-left text-slate-400"><th>Severity</th><th>Issue</th><th>URL</th><th>Detail</th></tr></thead>
          <tbody>{detail.issues.map((i: Json, k: number) => <tr key={k} className="border-t border-slate-800"><td>{i.severity}</td><td>{i.code}</td><td className="break-all">{i.url}</td><td>{i.detail}</td></tr>)}</tbody></table>}
      </div>
      <div className={box}>
        <h2 className="font-semibold">Core Web Vitals</h2>
        <p className="text-sm text-slate-400">Lab (a local headless browser run) and field (Chrome UX Report, real users) are different measurements and are never mixed.</p>
        <div className="flex flex-wrap gap-2">{own.map((s) => <span key={s.id} className="flex gap-2">
          <button className={btn} disabled={busy} onClick={() => run(async () => { const r = await apiClient.post(`${P}/vitals/lab`, { url: s.origin + "/" }); setVit((v) => [r.data, ...v]); }, "Lab run finished.")}>Lab: {s.origin}</button>
          <button className={btn} disabled={busy} onClick={() => run(async () => { const r = await apiClient.post(`${P}/vitals/field`, { url: s.origin }); setVit((v) => [{ ...r.data, url: s.origin }, ...v]); }, "Field data requested.")}>Field: {s.origin}</button></span>)}</div>
        <ul className="text-sm space-y-1">{vit.map((v, i) => <li key={i}><b>{v.kind}</b> {v.url ?? ""} · {v.state}{v.reason ? ` · ${v.reason}` : ""}{v.metrics ? ` · ${JSON.stringify(v.kind === "FIELD" ? Object.fromEntries(Object.entries(v.metrics).map(([k, m]: [string, any]) => [k, m.p75])) : v.metrics)}` : ""}</li>)}</ul>
      </div>
      <div className={box}>
        <h2 className="font-semibold">Keyword import (CSV)</h2>
        <p className="text-sm text-slate-400">Columns: keyword (required), volume, difficulty (0-100), cpc, locale, intent. No paid keyword API is connected.</p>
        <input aria-label="CSV supplier" className={inp} placeholder="Supplier name" value={kwSource} onChange={(e) => setKwSource(e.target.value)} />
        <textarea aria-label="CSV" className={`${inp} w-full h-28 font-mono`} value={csv} onChange={(e) => setCsv(e.target.value)} />
        <button className={btn} disabled={busy || !kwSource} onClick={() => run(async () => { const r = await apiClient.post(`${P}/keywords/import`, { csv_text: csv, source: kwSource }); return r.data; }, "Imported.")}>Import</button>
      </div>
    </div>
  );
}

function Aeo() {
  const { busy, run, note } = useAction();
  const [sets, setSets] = useState<Json[]>([]);
  const [sel, setSel] = useState<string>("");
  const [st, setSt] = useState<Json | null>(null);
  const [trend, setTrend] = useState<Json[]>([]);
  const [form, setForm] = useState({ name: "", locale: "en", prompts: "", brand: "POVU", domains: "", competitors: "", provider: "simulator", consent: false });
  const load = useCallback(() => apiClient.get(`${P}/aeo/sets`).then((r) => setSets(r.data)).catch(() => setSets([])), []);
  useEffect(() => { load(); }, [load]);
  const open = (id: string) => { setSel(id); apiClient.get(`${P}/aeo/sets/${id}/state`).then((r) => setSt(r.data)); apiClient.get(`${P}/aeo/sets/${id}/trend`).then((r) => setTrend(r.data)); };
  const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);
  return (
    <div className="space-y-4">
      <div className={box}>
        <h2 className="font-semibold">Prompt sets</h2>
        <p className="text-sm text-slate-400">Measures how often one answer engine names and cites the brand across repeated samples. It is not a search ranking. Page readiness (CMS AEO audit) is a separate thing.</p>
        <div className="grid gap-2 md:grid-cols-2">
          <input aria-label="Set name" className={inp} placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <select aria-label="Language" className={inp} value={form.locale} onChange={(e) => setForm({ ...form, locale: e.target.value })}><option value="en">English</option><option value="sw">Kiswahili</option><option value="tr">Türkçe</option></select>
          <textarea aria-label="Prompts" className={`${inp} h-24`} placeholder="One prompt per line" value={form.prompts} onChange={(e) => setForm({ ...form, prompts: e.target.value })} />
          <div className="space-y-2">
            <input aria-label="Brand terms" className={`${inp} w-full`} placeholder="Brand terms (comma separated)" value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
            <input aria-label="Brand domains" className={`${inp} w-full`} placeholder="Brand domains (comma separated)" value={form.domains} onChange={(e) => setForm({ ...form, domains: e.target.value })} />
            <input aria-label="Competitors" className={`${inp} w-full`} placeholder="Competitor names (comma separated)" value={form.competitors} onChange={(e) => setForm({ ...form, competitors: e.target.value })} />
          </div>
          <select aria-label="Provider" className={inp} value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}><option value="simulator">Local simulator (no cost, not real)</option><option value="ai_provider">Configured AI provider (costs money)</option></select>
          <label className="text-sm flex gap-1 items-center"><input type="checkbox" checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} /> I accept the provider terms and call cost for this set</label>
        </div>
        <button className={btn} disabled={busy || !form.name || !form.prompts} onClick={() => run(async () => {
          const csvl = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
          await apiClient.post(`${P}/aeo/sets`, { name: form.name, locale: form.locale, prompts: lines(form.prompts), brand_terms: csvl(form.brand), brand_domains: csvl(form.domains), competitor_terms: csvl(form.competitors), provider: form.provider, consent_confirmed: form.consent });
          load();
        }, "Prompt set saved.")}>Save prompt set</button>
        {note}
      </div>
      <div className={box}>
        <div className="flex flex-wrap gap-2">{sets.map((s) => <button key={s.id} className={`${btn} ${sel === s.id ? "" : "opacity-70"}`} onClick={() => open(s.id)}>{s.name} ({s.locale})</button>)}</div>
        {st && <>
          <p className={`text-sm ${st.state === "OK" ? "text-emerald-400" : "text-amber-400"}`} role="status">{st.state}{st.reasons.length ? `: ${st.reasons.join(" ")}` : ` · source ${st.source} · ${st.calls_this_month}/${st.monthly_cap} calls this month`}</p>
          <button className={btn} disabled={busy || st.state !== "OK"} onClick={() => run(async () => { await apiClient.post(`${P}/aeo/sets/${sel}/run`); open(sel); }, "Run finished.")}>Run now</button>
          <table className="w-full text-sm"><thead><tr className="text-left text-slate-400"><th>When</th><th>Source</th><th>Model</th><th>Samples</th><th>Brand mention (95% CI)</th><th>Brand cited</th></tr></thead>
            <tbody>{trend.map((t) => <tr key={t.run_id} className="border-t border-slate-800"><td>{t.at.slice(0, 16)}</td><td>{t.source}</td><td>{t.model_version}</td><td>{t.samples}{t.low_sample ? " (low)" : ""}</td>
              <td>{(t.brand_mention.rate * 100).toFixed(0)}% ({(t.brand_mention.low * 100).toFixed(0)}-{(t.brand_mention.high * 100).toFixed(0)}%)</td><td>{t.brand_citation.rate === null ? "-" : `${(t.brand_citation.rate * 100).toFixed(0)}%`}</td></tr>)}</tbody></table>
          {trend.length === 0 && <p className="text-sm text-slate-400">No measurement yet; nothing is estimated.</p>}
        </>}
      </div>
    </div>
  );
}

function Verification() {
  const { busy, run, note } = useAction();
  const [email, setEmail] = useState("");
  const [box_, setBox] = useState<Json[]>([]);
  const load = useCallback(() => apiClient.get("/api/v1/visitor-verification/outbox").then((r) => setBox(r.data)).catch(() => setBox([])), []);
  useEffect(() => { load(); }, [load]);
  return (
    <div className={box}>
      <h2 className="font-semibold">Visitor e-mail verification</h2>
      <p className="text-sm text-slate-400">Local outbox only: messages are never sent to a real mail server. Links work once, for 15 minutes, in the visitor's own browser.</p>
      <div className="flex flex-wrap gap-2">
        <input aria-label="Address to revoke" className={`${inp} w-72`} placeholder="visitor@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <button className={btn} disabled={busy || !email} onClick={() => run(async () => { await apiClient.post("/api/v1/visitor-verification/revoke", { email }); setEmail(""); load(); }, "Verification revoked.")}>Revoke address</button>
        <button className={btn} disabled={busy} onClick={() => run(async () => { await apiClient.post("/api/v1/visitor-verification/purge"); load(); }, "Old challenges deleted.")}>Delete old challenges</button>
        <button className="underline text-sm" onClick={load}>Refresh outbox</button>
      </div>
      <ul className="text-sm space-y-2">{box_.map((m, i) => <li key={i} className="border-t border-slate-800 pt-2"><b>{m.subject}</b> to {m.to} ({m.channel})<pre className="whitespace-pre-wrap text-xs text-slate-400">{m.body}</pre></li>)}
        {box_.length === 0 && <li className="text-slate-400">The outbox is empty.</li>}</ul>
      {note}
    </div>
  );
}

const TABS = [["gsc", "Search Console"], ["crawl", "Technical SEO"], ["aeo", "AEO measurement"], ["verify", "Visitor verification"]] as const;

export default function SeoProPage() {
  const [tab, setTab] = useState<(typeof TABS)[number][0]>("gsc");
  return (
    <RequirePermission permission="marketing.view">
      <div className="min-h-screen bg-[#0b1120] p-6 text-white">
        <h1 className="text-2xl font-bold">SEO, AEO and visitor verification</h1>
        <div role="tablist" className="flex flex-wrap gap-2 my-4">{TABS.map(([k, l]) =>
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`px-3 py-2 rounded-lg text-sm ${tab === k ? "bg-indigo-600" : "bg-[#131c2e]"}`}>{l}</button>)}</div>
        {tab === "gsc" && <Gsc />}{tab === "crawl" && <Crawler />}{tab === "aeo" && <Aeo />}{tab === "verify" && <Verification />}
      </div>
    </RequirePermission>
  );
}
