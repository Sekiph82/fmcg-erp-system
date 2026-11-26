"use client";
// M50.S01.T001-T004: AI prospecting agent, authorized web research, company enrichment, buyer-intent feed.
// Nothing is sent: outreach is a proposal that a different person approves under CRM -> Add-ins & AI access.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

const API = "/api/v1/prospecting-agent";
type St = { state: string; reasons: string[] };
type State = { search: St; enrichment: St; intent: St; llm: { mode: string; provider: string } };
type Ev = { criterion: string; value: string; citation: string };
type Cite = { url: string; title: string; snippet: string; retrieved_at: string };
type Cand = { id: string; kind: string; company_name: string; email: string | null; score: number; confidence: number; evidence: Ev[]; citations: Cite[]; unknowns: string[];
  territory: { assessment: string; note: string }; competitor: { assessment: string; note: string; mentions: { competitor: string; citation: string }[] }; rationale: string | null;
  crm_association: string; status: string; can_propose_outreach: boolean; outreach_blocked_reason: string | null; approval_request_id: string | null };
type Run = { id: string; llm_mode: string; llm_model: string | null; search_state: string; steps: Record<string, unknown>[]; candidates: Cand[] };
type Hit = { rank: number; title: string; url: string; description: string };
type Doc = { id: string; url: string; status: string; reason: string | null; title: string | null; facts: { field: string; value: string; snippet: string }[] };
type Prop = { id: string; field: string; value: string; current: string | null; confidence: number; status: string; source_ref: string; expires_at: string; expired: boolean; applicable: boolean };
type Alert = { id: string; customer: string; score: number; reasons: string[]; acknowledged_by: string | null };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : tx("Something went wrong."); };
const box = "border rounded p-3 bg-white space-y-2";
const inp = "border rounded px-2 py-1";
const btn = "border rounded px-2 py-1 bg-gray-50 disabled:opacity-50";

function Reasons({ s, label }: { s?: St; label: string }) {
  if (!s) return null;
  return <p className="text-xs text-gray-600">{label}: <b>{s.state === "OK" ? tx("ready") : tx("not configured")}</b>{s.reasons.length > 0 && ` - ${s.reasons.join(" ")}`}</p>;
}

export default function ProspectingPage() {
  const [msg, setMsg] = useState<string | null>(null);
  const [state, setState] = useState<State | null>(null);
  const [icps, setIcps] = useState<{ id: string; name: string; criteria: Record<string, unknown>; use_search: boolean }[]>([]);
  const [icp, setIcp] = useState({ name: "", city: "", channel: "", segment: "", keywords: "", competitors: "", use_search: false });
  const [sel, setSel] = useState("");
  const [disc, setDisc] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [draft, setDraft] = useState<{ id: string; subject: string; body: string; sources: string[] } | null>(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<{ hits: Hit[]; more: boolean; page: number; qid: string } | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [verdict, setVerdict] = useState<{ field: string; verdict: string; values: { value: string; sources: string[] }[] }[]>([]);
  const [cq, setCq] = useState("");
  const [custs, setCusts] = useState<{ id: string; name: string }[]>([]);
  const [cust, setCust] = useState<string>("");
  const [props, setProps] = useState<Prop[]>([]);
  const [feed, setFeed] = useState({ feed: "", consent: "", json: '[{"company_name":"","domain":"","topic":"","strength":0.8,"observed_at":""}]' });
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [wd, setWd] = useState("");

  const load = useCallback(() => {
    apiClient.get(`${API}/state`).then((r) => setState(r.data)).catch((e) => setMsg(err(e)));
    apiClient.get(`${API}/icps`).then((r) => setIcps(r.data)).catch(() => setIcps([]));
    apiClient.get(`${API}/research/docs`).then((r) => setDocs(r.data)).catch(() => setDocs([]));
    apiClient.get(`${API}/intent/alerts`).then((r) => setAlerts(r.data)).catch(() => setAlerts([]));
  }, []);
  useEffect(() => { load(); }, [load]);
  const go = (p: Promise<unknown>, ok?: string) => p.then(() => { if (ok) setMsg(ok); }).catch((e) => setMsg(err(e)));

  const saveIcp = () => go(apiClient.post(`${API}/icps`, {
    name: icp.name, city: icp.city || undefined, channel: icp.channel || undefined, segment: icp.segment || undefined,
    keywords: icp.keywords ? icp.keywords.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
    competitors: icp.competitors.split(",").map((s) => s.trim()).filter(Boolean), use_search: icp.use_search,
  }).then(() => load()), tx("Target profile saved."));
  const runAgent = () => go(apiClient.post(`${API}/runs`, { icp_id: sel, discovery_queries: disc ? [disc] : [] }).then((r) => setRun(r.data)));
  const showDraft = (c: Cand) => go(apiClient.post(`${API}/candidates/${c.id}/draft`).then((r) => setDraft({ id: c.id, ...r.data })));
  const propose = (c: Cand) => go(apiClient.post(`${API}/candidates/${c.id}/outreach`, {}).then((r) => {
    setMsg(tx("Proposed: a colleague approves it under CRM -> Add-ins & AI access. Nothing was sent."));
    setRun((x) => x && { ...x, candidates: x.candidates.map((k) => k.id === c.id ? { ...k, status: "OUTREACH_PROPOSED", approval_request_id: r.data.approval_request_id } : k) });
  }));
  const dismiss = (c: Cand) => go(apiClient.post(`${API}/candidates/${c.id}/dismiss`).then(() => setRun((x) => x && { ...x, candidates: x.candidates.map((k) => k.id === c.id ? { ...k, status: "DISMISSED" } : k) })));

  const search = (page = 0) => go(apiClient.post(`${API}/research/search`, { q, page }).then((r) => setHits({ hits: r.data.results, more: r.data.more_available, page, qid: r.data.query_id })));
  const fetchDoc = (h: Hit) => go(apiClient.post(`${API}/research/fetch`, { url: h.url, query_id: hits?.qid }).then(() => load()), tx("Page fetched under the safe-fetch policy."));
  const reconcile = () => go(apiClient.post(`${API}/research/reconcile`, { doc_ids: docs.filter((d) => d.status === "FETCHED").slice(0, 20).map((d) => d.id) }).then((r) => setVerdict(r.data.fields)));

  const findCust = () => apiClient.get("/api/v1/customer-intel/customers", { params: { q: cq, limit: 10 } }).then((r) => setCusts(r.data)).catch((e) => setMsg(err(e)));
  const loadProps = (id: string) => { setCust(id); return apiClient.get(`${API}/enrichment/customers/${id}`).then((r) => setProps(r.data)).catch((e) => setMsg(err(e))); };
  const preview = () => go(apiClient.post(`${API}/enrichment/customers/${cust}/preview`).then((r) => { setProps(r.data.proposals); setMsg(tx("{new} new proposal(s). Nothing is applied until you apply it.", { new: r.data.new })); }));
  const decide = (p: Prop, what: "apply" | "reject" | "revoke", overwrite = false) =>
    apiClient.post(`${API}/enrichment/${p.id}/${what}`, what === "apply" ? { overwrite } : undefined).then(() => { setMsg(tx("{what} done.", { what })); return loadProps(cust); })
      .catch((e) => { const m = err(e); if (m.includes("confirm the overwrite") && window.confirm(tx("{m} Overwrite?", { m }))) decide(p, what, true); else setMsg(m); });
  const purge = () => go(apiClient.delete(`${API}/enrichment/customers/${cust}`).then(() => loadProps(cust)), tx("Stored proposals deleted; customer data is unchanged."));

  const importFeed = () => {
    let events: unknown;
    try { events = JSON.parse(feed.json); } catch { setMsg(tx("Events must be valid JSON.")); return; }
    go(apiClient.post(`${API}/intent/import`, { feed: feed.feed, consent_basis: feed.consent, events }).then((r) => { setMsg(tx("Stored {stored}; duplicates {duplicates}, stale {stale}, weak {weak}, unresolved {unresolved}, person fields dropped {person_fields_dropped}, alerts {alerts}.", { stored: r.data.stored, duplicates: r.data.duplicates, stale: r.data.stale, weak: r.data.weak, unresolved: r.data.unresolved, person_fields_dropped: r.data.person_fields_dropped, alerts: r.data.alerts })); load(); }));
  };
  const withdraw = () => go(apiClient.post(`${API}/intent/withdraw`, { feed: wd }).then((r) => { setMsg(tx("Withdrawn {withdrawn} event(s); {alerts_removed} alert(s) removed.", { withdrawn: r.data.withdrawn, alerts_removed: r.data.alerts_removed })); load(); }));
  const ack = (a: Alert) => go(apiClient.post(`${API}/intent/alerts/${a.id}/ack`).then(() => load()));

  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">{tx("AI prospecting & external data")}</h2>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {state && (
        <section className={box}>
          <p className="text-xs text-gray-600">{tx("Ranking mode:")} <b>{state.llm.mode === "LLM" ? tx("AI model ({provider})", { provider: state.llm.provider }) : tx("deterministic (no AI key configured)")}</b>{tx(". Outreach is never sent automatically.")}</p>
          <Reasons s={state.search} label={tx("Web research")} /><Reasons s={state.enrichment} label={tx("Enrichment")} /><Reasons s={state.intent} label={tx("Buyer-intent feed")} />
        </section>
      )}

      <section className={box}>
        <h3 className="font-semibold">{tx("1. Target profile and agent run")}</h3>
        <div className="flex flex-wrap gap-2">
          <input className={inp} placeholder={tx("Name")} value={icp.name} onChange={(e) => setIcp({ ...icp, name: e.target.value })} />
          <input className={inp} placeholder={tx("City")} value={icp.city} onChange={(e) => setIcp({ ...icp, city: e.target.value })} />
          <input className={inp} placeholder={tx("Channel (RETAIL...)")} value={icp.channel} onChange={(e) => setIcp({ ...icp, channel: e.target.value })} />
          <input className={inp} placeholder={tx("Segment")} value={icp.segment} onChange={(e) => setIcp({ ...icp, segment: e.target.value })} />
          <input className={inp} placeholder={tx("Keywords, comma separated")} value={icp.keywords} onChange={(e) => setIcp({ ...icp, keywords: e.target.value })} />
          <input className={inp} placeholder={tx("Competitors, comma separated")} value={icp.competitors} onChange={(e) => setIcp({ ...icp, competitors: e.target.value })} />
          <label className="flex items-center gap-1"><input type="checkbox" checked={icp.use_search} onChange={(e) => setIcp({ ...icp, use_search: e.target.checked })} />{tx("Use web research")}</label>
          <button className={btn} disabled={!icp.name || !(icp.city || icp.channel || icp.segment || icp.keywords)} title={!icp.name ? tx("Give the profile a name") : tx("Give at least one criterion")} onClick={saveIcp}>{tx("Save profile")}</button>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <select className={inp} value={sel} onChange={(e) => setSel(e.target.value)}><option value="">{tx("Choose a profile")}</option>{icps.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</select>
          <input className={inp} placeholder={tx("Optional discovery search")} value={disc} onChange={(e) => setDisc(e.target.value)} />
          <button className={btn} disabled={!sel} title={!sel ? tx("Choose a profile first") : ""} onClick={runAgent}>{tx("Run agent")}</button>
        </div>
        {run && (
          <div className="space-y-2">
            <p className="text-xs text-gray-600">{tx("Ranking:")} {run.llm_mode}{run.llm_model ? ` (${run.llm_model})` : ""}{tx("; web research:")} {run.search_state}{tx(". Steps:")} {run.steps.map((s) => String(s.step)).join(" > ")}</p>
            {!run.candidates.length && <p className="text-xs text-amber-700">{tx("No candidates matched this profile in the CRM")}{run.search_state === "OK" ? tx(" or the web research") : tx(" (web research is off)")}{tx(". Widen the profile (city, channel, segment, keywords) or add prospects first.")}</p>}
            {run.candidates.map((c) => (
              <div key={c.id} className="border rounded p-2 space-y-1">
                <div className="flex justify-between"><b>{c.company_name}</b><span>{tx("score")} {c.score.toFixed(2)} {tx("/ confidence")} {c.confidence.toFixed(2)} ({c.kind}{c.crm_association === "EXISTING_LEAD" ? tx(", linked to CRM lead") : ""})</span></div>
                <p>{c.rationale}</p>
                <ul className="list-disc ml-5 text-xs">{c.evidence.map((e, i) => <li key={i}>{tx("[E")}{i + 1}] {e.criterion}: {e.value} <i>({e.citation})</i></li>)}</ul>
                {c.citations.map((x) => <p key={x.url} className="text-xs">{tx("Web:")} <a className="underline" href={x.url} target="_blank" rel="noreferrer noopener">{x.title}</a> {tx("retrieved")} {x.retrieved_at.slice(0, 10)}</p>)}
                {c.unknowns.length > 0 && <p className="text-xs text-amber-700">{tx("Unknown:")} {c.unknowns.join(", ")}</p>}
                <p className="text-xs">{tx("Territory:")} {c.territory.assessment} - {c.territory.note}{tx(". Competitors:")} {c.competitor.assessment}{c.competitor.mentions.map((m) => ` ${m.competitor}`).join(",")}.</p>
                <div className="flex gap-2 items-center">
                  <button className={btn} onClick={() => showDraft(c)} disabled={!c.email} title={c.email ? "" : tx("No e-mail address known")}>{tx("Preview draft")}</button>
                  <button className={btn} onClick={() => propose(c)} disabled={!c.can_propose_outreach} title={c.outreach_blocked_reason ?? (c.status !== "RANKED" ? tx("Already {status}", { status: c.status }) : "")}>{tx("Propose outreach for approval")}</button>
                  <button className={btn} onClick={() => dismiss(c)} disabled={c.status !== "RANKED"}>{tx("Dismiss")}</button>
                  <span className="text-xs">{c.status === "OUTREACH_PROPOSED" ? tx("Waiting for a different person to approve") : c.status}</span>
                </div>
              </div>
            ))}
            {draft && <div className="border rounded p-2 bg-gray-50"><b>{draft.subject}</b><pre className="whitespace-pre-wrap text-xs">{draft.body}</pre><p className="text-xs">{tx("Sources:")} {draft.sources.join("; ")}</p></div>}
          </div>
        )}
      </section>

      <section className={box}>
        <h3 className="font-semibold">{tx("2. Web research (licensed search, safe fetch)")}</h3>
        <div className="flex gap-2"><input className={inp} placeholder={tx("Search query")} value={q} onChange={(e) => setQ(e.target.value)} />
          <button className={btn} disabled={!q || state?.search.state !== "OK"} title={state?.search.state !== "OK" ? state?.search.reasons.join(" ") : ""} onClick={() => search(0)}>{tx("Search")}</button></div>
        {hits && (<div className="space-y-1">
          {hits.hits.map((h) => <div key={h.url} className="flex gap-2 items-start text-xs"><div className="flex-1"><b>{h.rank}. {h.title}</b><br />{h.url}<br />{h.description}</div><button className={btn} onClick={() => fetchDoc(h)}>{tx("Fetch page")}</button></div>)}
          <div className="flex gap-2"><button className={btn} disabled={hits.page === 0} onClick={() => search(hits.page - 1)}>{tx("Previous page")}</button>
            <button className={btn} disabled={!hits.more} title={hits.more ? "" : tx("The provider reports no more results")} onClick={() => search(hits.page + 1)}>{tx("Next page")}</button></div></div>)}
        <ul className="text-xs space-y-1">{docs.map((d) => <li key={d.id}>{d.status}: {d.title ?? d.url}{d.reason ? ` - ${d.reason}` : ""}{d.facts.length > 0 && ` (${d.facts.map((f) => `${f.field}=${f.value}`).join(", ")})`}</li>)}</ul>
        <button className={btn} disabled={!docs.some((d) => d.status === "FETCHED")} onClick={reconcile}>{tx("Compare facts across pages")}</button>
        {verdict.map((f) => <p key={f.field} className="text-xs"><b>{f.field}</b>: {f.verdict}{f.values.map((v) => tx(" | {value} ({length} page(s))", { value: v.value, length: v.sources.length })).join("")}</p>)}
      </section>

      <section className={box}>
        <h3 className="font-semibold">{tx("3. Customer enrichment")}</h3>
        <div className="flex gap-2"><input className={inp} placeholder={tx("Find customer")} value={cq} onChange={(e) => setCq(e.target.value)} /><button className={btn} onClick={findCust}>{tx("Find")}</button>
          {custs.map((c) => <button key={c.id} className={btn} onClick={() => loadProps(c.id)}>{c.name}</button>)}</div>
        <button className={btn} disabled={!cust || state?.enrichment.state !== "OK"} title={!cust ? tx("Choose a customer") : state?.enrichment.reasons.join(" ")} onClick={preview}>{tx("Preview enrichment")}</button>
        {props.length > 0 && <button className={btn} onClick={purge}>{tx("Delete stored proposals")}</button>}
        {props.map((p) => (
          <div key={p.id} className="flex flex-wrap gap-2 items-center text-xs border-t pt-1">
            <b>{p.field}</b> {p.value} {p.current && p.current !== p.value && <i>{tx("(now:")} {p.current})</i>} {tx("conf")} {p.confidence} - {p.source_ref} - {p.status}{p.expired ? tx(" (expired)") : ""}
            <button className={btn} disabled={p.status !== "PROPOSED" || !p.applicable || p.expired} title={!p.applicable ? tx("Shown for information only") : ""} onClick={() => decide(p, "apply")}>{tx("Apply")}</button>
            <button className={btn} disabled={p.status !== "PROPOSED"} onClick={() => decide(p, "reject")}>{tx("Reject")}</button>
            <button className={btn} disabled={p.status === "REVOKED"} onClick={() => decide(p, "revoke")}>{tx("Revoke")}</button>
          </div>))}
      </section>

      <section className={box}>
        <h3 className="font-semibold">{tx("4. Buyer-intent feed (company level, third party)")}</h3>
        <p className="text-xs text-gray-600">{tx("Person-level fields in a feed are dropped. This score is separate from the first-party intent score.")}</p>
        <div className="flex gap-2"><input className={inp} placeholder={tx("Feed name")} value={feed.feed} onChange={(e) => setFeed({ ...feed, feed: e.target.value })} />
          <input className={inp} placeholder={tx("Consent / licence basis")} value={feed.consent} onChange={(e) => setFeed({ ...feed, consent: e.target.value })} /></div>
        <textarea className={`${inp} w-full font-mono text-xs`} rows={4} value={feed.json} onChange={(e) => setFeed({ ...feed, json: e.target.value })} />
        <button className={btn} disabled={!feed.feed || feed.consent.length < 3 || state?.intent.state !== "OK"} title={state?.intent.state !== "OK" ? state?.intent.reasons.join(" ") : ""} onClick={importFeed}>{tx("Import events")}</button>
        <div className="flex gap-2"><input className={inp} placeholder={tx("Feed to withdraw consent for")} value={wd} onChange={(e) => setWd(e.target.value)} /><button className={btn} disabled={!wd} onClick={withdraw}>{tx("Withdraw consent")}</button></div>
        {alerts.map((a) => <p key={a.id} className="text-xs"><b>{a.customer}</b> {tx("score")} {a.score}: {a.reasons.join("; ")} {a.acknowledged_by ? tx("(acknowledged by {acknowledged_by})", { acknowledged_by: a.acknowledged_by }) : <button className={btn} onClick={() => ack(a)}>{tx("Acknowledge")}</button>}</p>)}
      </section>
    </div>
  );
}
