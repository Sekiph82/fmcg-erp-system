"use client";
// M50.S01.T006 service-agent QA: metrics, unresolved-question clusters, knowledge-gap proposals, answer reviews, safety cases.
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";

const API = "/api/v1/service-desk/agent";
const errText = (e: unknown) => (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Request failed.";

interface Metrics {
  days: number; turns: number; sessions: number; outcomes: Record<string, number>; modes: Record<string, number>;
  grounded_rate: number | null; containment_rate: number | null; confirmed_resolution_rate: number | null; sessions_with_feedback: number;
  csat: { avg: number | null; n: number }; ces: { avg: number | null; n: number };
  accuracy: { reviewed: number; verdicts: Record<string, number>; correct_rate: number | null; citation_ok_rate: number | null };
  safety_escalations: number;
  by_topic: Record<string, Row>; by_language: Record<string, Row>;
}
interface Row { turns: number; answered: number; abstained: number; grounded_rate: number | null; escalated: number; csat: number | null }
interface Cluster { key: string; count: number; samples: string[]; languages: Record<string, number>; proposal: { id: string; status: string } | null }
interface Gap { id: string; cluster_key: string; status: string; title: string; summary: string | null; content_md: string; samples: string[]; count: number; created_by: string; decided_by: string | null; article_id: string | null }
interface Queued { id: string; question: string; answer: string | null; citations: string[]; lang: string; topic: string; mode: string }
interface Safety { turn_id: string; at: string; lot_number: string | null; complaint_ref: string | null; complaint_status: string | null; product: string | null; regulatory_report_required: boolean | null }

const pct = (v: number | null) => (v === null ? "no data yet" : `${Math.round(v * 100)}%`);
const TABS = ["Metrics", "Unresolved questions", "Gap proposals", "Answer reviews", "Safety"] as const;

function Err({ msg }: { msg: string | null }) { return msg ? <p role="alert" className="text-xs text-red-600 mt-1">{msg}</p> : null; }

export default function ServiceAgentQA() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Metrics");
  const [days, setDays] = useState(30);
  return (
    <div className="p-4 space-y-4 max-w-6xl">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-semibold">Service agent quality</h1>
        <label className="text-sm flex items-center gap-2">Period
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="border rounded px-2 py-1">
            {[7, 30, 90, 365].map((d) => <option key={d} value={d}>{d} days</option>)}
          </select></label>
      </div>
      <div className="flex flex-wrap gap-2" role="tablist">
        {TABS.map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
          className={`px-3 py-1.5 rounded-lg text-sm border ${tab === t ? "bg-indigo-600 text-white" : "bg-white"}`}>{t}</button>)}
      </div>
      {tab === "Metrics" && <MetricsTab days={days} />}
      {tab === "Unresolved questions" && <ClustersTab days={days} />}
      {tab === "Gap proposals" && <GapsTab />}
      {tab === "Answer reviews" && <ReviewsTab />}
      {tab === "Safety" && <SafetyTab days={days} />}
    </div>
  );
}

function BreakDown({ title, rows }: { title: string; rows: Record<string, Row> }) {
  return (
    <div className="overflow-x-auto">
      <table className="text-sm w-full"><caption className="text-left font-medium mb-1">{title}</caption>
        <thead><tr className="text-left text-gray-500"><th className="pr-3">Name</th><th className="pr-3">Turns</th><th className="pr-3">Grounded answers</th><th className="pr-3">Abstained</th><th className="pr-3">Escalated</th><th>CSAT</th></tr></thead>
        <tbody>{Object.entries(rows).map(([k, r]) => (
          <tr key={k} className="border-t"><td className="pr-3">{k}</td><td className="pr-3">{r.turns}</td><td className="pr-3">{r.answered} ({pct(r.grounded_rate)})</td><td className="pr-3">{r.abstained}</td><td className="pr-3">{r.escalated}</td><td>{r.csat ?? "-"}</td></tr>))}</tbody>
      </table>
    </div>
  );
}

function MetricsTab({ days }: { days: number }) {
  const q = useQuery({ queryKey: ["sa-metrics", days], queryFn: () => apiClient.get<Metrics>(`${API}/metrics?days=${days}`).then((r) => r.data), retry: false });
  const [text, setText] = useState("");
  const retest = useMutation({ mutationFn: () => apiClient.post<{ grounded: boolean; citations: { slug: string; title: string; version: number; kind: string }[] }>(`${API}/retest`, { question: text }).then((r) => r.data) });
  if (q.isLoading) return <p className="text-sm text-gray-500">Loading...</p>;
  if (q.isError) return <p role="alert" className="text-sm text-red-600">{errText(q.error)}</p>;
  const m = q.data!;
  const card = (label: string, value: string, hint?: string) => (
    <div className="border rounded-lg p-3"><p className="text-xs text-gray-500">{label}</p><p className="text-lg font-semibold">{value}</p>{hint && <p className="text-xs text-gray-400">{hint}</p>}</div>);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {card("Chats / turns", `${m.sessions} / ${m.turns}`)}
        {card("Grounded answer rate", pct(m.grounded_rate), "answered vs. abstained")}
        {card("Contained by the agent", pct(m.containment_rate), "never handed over or escalated")}
        {card("Confirmed resolved", pct(m.confirmed_resolution_rate), `${m.sessions_with_feedback} chats with a rating`)}
        {card("CSAT (1-5)", m.csat.avg === null ? "no data yet" : String(m.csat.avg), `${m.csat.n} ratings`)}
        {card("CES (1-7, 7 = easy)", m.ces.avg === null ? "no data yet" : String(m.ces.avg), `${m.ces.n} ratings`)}
        {card("Reviewed answers correct", pct(m.accuracy.correct_rate), `${m.accuracy.reviewed} reviewed; citations ok ${pct(m.accuracy.citation_ok_rate)}`)}
        {card("Safety escalations", String(m.safety_escalations))}
      </div>
      <p className="text-xs text-gray-500">Outcomes: {Object.entries(m.outcomes).map(([k, v]) => `${k} ${v}`).join(", ") || "none"}. Answer modes: {Object.entries(m.modes).map(([k, v]) => `${k} ${v}`).join(", ") || "none"}. Safety chats are never counted as resolved.</p>
      <BreakDown title="By topic" rows={m.by_topic} />
      <BreakDown title="By language" rows={m.by_language} />
      <div className="border rounded-lg p-3 space-y-2">
        <p className="text-sm font-medium">Re-test a question against the approved articles (no model call, nothing stored)</p>
        <div className="flex gap-2"><input aria-label="Question to re-test" value={text} maxLength={500} onChange={(e) => setText(e.target.value)} className="flex-1 border rounded px-2 py-1 text-sm" />
          <button disabled={text.trim().length < 2 || retest.isPending} onClick={() => retest.mutate()} title={text.trim().length < 2 ? "Type a question first" : ""} className="px-3 py-1 rounded bg-indigo-600 text-white text-sm disabled:opacity-50">Re-test</button></div>
        {retest.data && (retest.data.grounded
          ? <ul className="text-sm list-disc pl-5">{retest.data.citations.map((c) => <li key={c.slug}>{c.title} <span className="text-gray-400">(v{c.version}, {c.kind}, /kb/{c.slug})</span></li>)}</ul>
          : <p className="text-sm text-amber-700">Not grounded: the agent would abstain and hand over to a person.</p>)}
        <Err msg={retest.isError ? errText(retest.error) : null} />
      </div>
    </div>
  );
}

function ClustersTab({ days }: { days: number }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["sa-clusters", days], queryFn: () => apiClient.get<Cluster[]>(`${API}/clusters?days=${days}`).then((r) => r.data), retry: false });
  const [open, setOpen] = useState<string | null>(null);
  const [f, setF] = useState({ title: "", summary: "", content_md: "" });
  const [err, setErr] = useState<string | null>(null);
  const propose = useMutation({
    mutationFn: (key: string) => apiClient.post(`${API}/gaps`, { cluster_key: key, days, title: f.title, summary: f.summary || null, content_md: f.content_md }),
    onSuccess: () => { setOpen(null); setF({ title: "", summary: "", content_md: "" }); setErr(null); qc.invalidateQueries({ queryKey: ["sa-clusters"] }); qc.invalidateQueries({ queryKey: ["sa-gaps"] }); },
    onError: (e) => setErr(errText(e)),
  });
  if (q.isError) return <p role="alert" className="text-sm text-red-600">{errText(q.error)}</p>;
  const ready = f.title.trim().length >= 3 && f.content_md.trim().length > 0;
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">Questions the agent could not ground in approved articles (and answers customers rated 1-2), grouped by topic words.</p>
      {(q.data ?? []).length === 0 && <p className="text-sm text-gray-500">No unresolved questions in this period.</p>}
      {(q.data ?? []).map((c) => (
        <div key={c.key} className="border rounded-lg p-3 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-medium">{c.key} <span className="text-gray-400 text-sm">{c.count} questions, {Object.entries(c.languages).map(([l, n]) => `${l} ${n}`).join(", ")}</span></p>
            {c.proposal ? <span className="text-xs px-2 py-0.5 rounded bg-gray-100">Proposal {c.proposal.status.toLowerCase()}</span>
              : <button onClick={() => { setOpen(open === c.key ? null : c.key); setErr(null); }} className="px-3 py-1 rounded bg-indigo-600 text-white text-sm">Propose article</button>}
          </div>
          <ul className="text-sm text-gray-600 list-disc pl-5">{c.samples.map((s, i) => <li key={i} className="break-words">{s}</li>)}</ul>
          {open === c.key && (
            <div className="space-y-2 border-t pt-2">
              <input aria-label="Article title" placeholder="Article title" value={f.title} maxLength={300} onChange={(e) => setF({ ...f, title: e.target.value })} className="w-full border rounded px-2 py-1 text-sm" />
              <input aria-label="Short summary" placeholder="Short summary (shown to customers)" value={f.summary} maxLength={1000} onChange={(e) => setF({ ...f, summary: e.target.value })} className="w-full border rounded px-2 py-1 text-sm" />
              <textarea aria-label="Article content" placeholder="Article content (markdown). Must be accurate: customers will see it and the agent will cite it." rows={5} value={f.content_md} onChange={(e) => setF({ ...f, content_md: e.target.value })} className="w-full border rounded px-2 py-1 text-sm" />
              <button disabled={!ready || propose.isPending} title={ready ? "" : "Add a title (3+ characters) and the article content"} onClick={() => propose.mutate(c.key)} className="px-3 py-1 rounded bg-indigo-600 text-white text-sm disabled:opacity-50">Submit for approval</button>
              <Err msg={err} />
            </div>)}
        </div>))}
    </div>
  );
}

function GapsTab() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["sa-gaps"], queryFn: () => apiClient.get<Gap[]>(`${API}/gaps`).then((r) => r.data), retry: false });
  const [err, setErr] = useState<Record<string, string>>({});
  const [note, setNote] = useState<Record<string, string>>({});
  const decide = useMutation({
    mutationFn: (v: { id: string; approve: boolean }) => apiClient.post(`${API}/gaps/${v.id}/decision`, { approve: v.approve, note: note[v.id] || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sa-gaps"] }); qc.invalidateQueries({ queryKey: ["sa-clusters"] }); },
    onError: (e, v) => setErr((x) => ({ ...x, [v.id]: errText(e) })),
  });
  if (q.isError) return <p role="alert" className="text-sm text-red-600">{errText(q.error)}</p>;
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">Approving publishes the article to the public help centre, where the agent can cite it. A second person must approve; service administrators only.</p>
      {(q.data ?? []).length === 0 && <p className="text-sm text-gray-500">No proposals yet.</p>}
      {(q.data ?? []).map((g) => (
        <div key={g.id} className="border rounded-lg p-3 space-y-2">
          <div className="flex flex-wrap justify-between gap-2"><p className="font-medium break-words">{g.title}</p>
            <span className="text-xs px-2 py-0.5 rounded bg-gray-100">{g.status.toLowerCase()} - by {g.created_by}{g.decided_by ? `, decided by ${g.decided_by}` : ""}</span></div>
          <p className="text-xs text-gray-500">{g.count} customer questions in cluster {g.cluster_key}</p>
          <pre className="text-xs bg-gray-50 rounded p-2 whitespace-pre-wrap break-words">{g.content_md}</pre>
          {g.status === "PROPOSED" && (
            <div className="flex flex-wrap items-center gap-2">
              <input aria-label="Decision note" placeholder="Note (optional)" maxLength={500} value={note[g.id] ?? ""} onChange={(e) => setNote({ ...note, [g.id]: e.target.value })} className="border rounded px-2 py-1 text-sm flex-1 min-w-40" />
              <button disabled={decide.isPending} onClick={() => decide.mutate({ id: g.id, approve: true })} className="px-3 py-1 rounded bg-emerald-600 text-white text-sm disabled:opacity-50">Approve and publish</button>
              <button disabled={decide.isPending} onClick={() => decide.mutate({ id: g.id, approve: false })} className="px-3 py-1 rounded border text-sm disabled:opacity-50">Reject</button>
            </div>)}
          {g.article_id && <p className="text-xs text-emerald-700">Published as a help article.</p>}
          <Err msg={err[g.id] ?? null} />
        </div>))}
    </div>
  );
}

function ReviewsTab() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["sa-queue"], queryFn: () => apiClient.get<Queued[]>(`${API}/reviews/queue`).then((r) => r.data), retry: false });
  const [note, setNote] = useState<Record<string, string>>({});
  const [err, setErr] = useState<Record<string, string>>({});
  const review = useMutation({
    mutationFn: (v: { id: string; verdict: string }) => apiClient.post(`${API}/turns/${v.id}/review`, { verdict: v.verdict, note: note[v.id] || null }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sa-queue"] }),
    onError: (e, v) => setErr((x) => ({ ...x, [v.id]: errText(e) })),
  });
  if (q.isError) return <p role="alert" className="text-sm text-red-600">{errText(q.error)}</p>;
  const verdicts: [string, string][] = [["CORRECT", "Correct"], ["WRONG_CITATION", "Wrong citation"], ["INACCURATE", "Inaccurate"], ["UNSUPPORTED", "Not supported by source"]];
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">Check each answer against the cited article. Any verdict other than &ldquo;Correct&rdquo; needs a note.</p>
      {(q.data ?? []).length === 0 && <p className="text-sm text-gray-500">Nothing waiting for review.</p>}
      {(q.data ?? []).map((t) => {
        const hasNote = (note[t.id] ?? "").trim().length > 0;
        return (
          <div key={t.id} className="border rounded-lg p-3 space-y-2">
            <p className="text-xs text-gray-400">{t.lang} - {t.topic} - {t.mode === "LLM" ? "model answer" : "extractive answer"}</p>
            <p className="text-sm"><b>Customer:</b> {t.question}</p>
            <pre className="text-xs bg-gray-50 rounded p-2 whitespace-pre-wrap break-words">{t.answer}</pre>
            <p className="text-xs">Cited: {t.citations.map((c) => <a key={c} href={c} target="_blank" rel="noreferrer" className="text-indigo-600 underline mr-2">{c}</a>)}</p>
            <input aria-label="Review note" placeholder="Note (required unless correct)" maxLength={1000} value={note[t.id] ?? ""} onChange={(e) => setNote({ ...note, [t.id]: e.target.value })} className="w-full border rounded px-2 py-1 text-sm" />
            <div className="flex flex-wrap gap-2">{verdicts.map(([v, label]) => {
              const blocked = v !== "CORRECT" && !hasNote;
              return <button key={v} disabled={blocked || review.isPending} title={blocked ? "Add a note first" : ""} onClick={() => review.mutate({ id: t.id, verdict: v })}
                className={`px-3 py-1 rounded text-sm disabled:opacity-50 ${v === "CORRECT" ? "bg-emerald-600 text-white" : "border"}`}>{label}</button>;
            })}</div>
            <Err msg={err[t.id] ?? null} />
          </div>);
      })}
    </div>
  );
}

function SafetyTab({ days }: { days: number }) {
  const q = useQuery({ queryKey: ["sa-safety", days], queryFn: () => apiClient.get<Safety[]>(`${API}/safety?days=${days}`).then((r) => r.data), retry: false });
  if (q.isError) return <p role="alert" className="text-sm text-red-600">{errText(q.error)}</p>;
  return (
    <div className="space-y-2">
      <p className="text-sm text-gray-600">Customer chats that reported a possible product-safety problem. Each created an escalated safety complaint (and, for signed-in customers, a critical ticket on the lot). Quality owns the follow-up in Consumer Complaints.</p>
      {(q.data ?? []).length === 0 && <p className="text-sm text-gray-500">No safety reports in this period.</p>}
      <div className="overflow-x-auto"><table className="text-sm w-full">
        <thead><tr className="text-left text-gray-500"><th className="pr-3">When</th><th className="pr-3">Complaint</th><th className="pr-3">Status</th><th className="pr-3">Product</th><th className="pr-3">Lot</th><th>Regulatory report</th></tr></thead>
        <tbody>{(q.data ?? []).map((s) => (
          <tr key={s.turn_id} className="border-t"><td className="pr-3">{new Date(s.at).toLocaleString()}</td><td className="pr-3">{s.complaint_ref ?? "-"}</td><td className="pr-3">{s.complaint_status ?? "-"}</td>
            <td className="pr-3">{s.product ?? "-"}</td><td className="pr-3">{s.lot_number ?? "not stated"}</td><td>{s.regulatory_report_required ? "required" : "-"}</td></tr>))}</tbody>
      </table></div>
    </div>
  );
}
