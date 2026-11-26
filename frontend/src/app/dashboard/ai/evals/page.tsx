"use client";
// M50.S01.T012 AI evaluation review: run a versioned benchmark corpus through an adapter, inspect expected vs actual per case,
// see which scorers failed, compare two runs for regressions, and record a second person's review. Everything here is
// SYNTHETIC test data; real-world calibration is a separate, currently empty, field.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Corpus = { corpus_id: string; version: string; data_kind: string; description: string; cases: number; sha256: string; tasks: string[] };
type Adapter = { model_id: string; provider: string; tasks: string[] | null; available: boolean; unavailable_reason: string | null };
type Run = {
  id: string; corpus_id: string; corpus_version: string; corpus_sha256: string; adapter: string; model_id: string; provider: string; config_hash: string;
  data_kind: string; label: string | null; real_calibration: unknown; status: string; note: string | null; total: number; passed: number;
  summary: { scorers?: Record<string, { passed: number; total: number }>; digest?: string; skipped?: number } | null;
  review_status: string; reviewed_by: string | null; review_note: string | null; created_by: string; created_at: string;
};
type Case = { case_id: string; passed: boolean; scores: Record<string, { passed: boolean; score: number; detail: string }>; expected: unknown; actual: { text?: string; citations?: unknown[]; actions?: unknown[]; latency_ms?: number; latency_source?: string }; latency_ms: number; tokens: number; cost: string; error: string | null };
type Detail = Run & { results: Case[] };

const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const B = "/api/v1/ai-agents/evals";

export default function EvalsPage() {
  const [label, setLabel] = useState("");
  const [corpora, setCorpora] = useState<Corpus[]>([]);
  const [adapters, setAdapters] = useState<Record<string, Adapter>>({});
  const [runs, setRuns] = useState<Run[]>([]);
  const [corpus, setCorpus] = useState("customer_service");
  const [adapter, setAdapter] = useState("simulator");
  const [cur, setCur] = useState<Detail | null>(null);
  const [failedOnly, setFailedOnly] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [verify, setVerify] = useState<string[] | null>(null);
  const [note, setNote] = useState("");
  const [cmp, setCmp] = useState<{ same_digest: boolean; same_config: boolean; regressions: string[]; fixed: string[] } | null>(null);
  const [other, setOther] = useState("");
  const load = useCallback(() => {
    apiClient.get(`${B}/corpora`).then((r) => { setCorpora(r.data.corpora); setAdapters(r.data.adapters); setLabel(r.data.label); }).catch((e) => setMsg(err(e)));
    apiClient.get(`${B}/runs`).then((r) => setRuns(r.data.runs)).catch((e) => setMsg(err(e)));
  }, []);
  useEffect(() => { load(); }, [load]);
  const open = (id: string, failed = failedOnly) => { setCmp(null); return apiClient.get(`${B}/runs/${id}`, { params: { failed_only: failed } }).then((r) => setCur(r.data)).catch((e) => setMsg(err(e))); };
  const start = () => apiClient.post(`${B}/runs`, { corpus_id: corpus, adapter }).then((r) => { setMsg(r.data.status === "UNAVAILABLE" ? tx("Not scored: {note}", { note: r.data.note }) : tx("Run finished: {passed}/{total} cases passed.", { passed: r.data.passed, total: r.data.total })); load(); open(r.data.id); }).catch((e) => setMsg(err(e)));
  const doVerify = () => apiClient.get(`${B}/corpora/${corpus}/verify`).then((r) => setVerify(r.data.problems)).catch((e) => setMsg(err(e)));
  const review = (verdict: "ACCEPTED" | "REJECTED") => apiClient.post(`${B}/runs/${cur!.id}/review`, { verdict, note }).then(() => { setMsg(tx("Review recorded.")); setNote(""); load(); open(cur!.id); }).catch((e) => setMsg(err(e)));
  const compare = () => apiClient.get(`${B}/compare`, { params: { a: other, b: cur!.id } }).then((r) => setCmp(r.data)).catch((e) => setMsg(err(e)));
  const sc = cur?.summary?.scorers ?? {};

  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex justify-between items-center"><h2 className="text-lg font-semibold">{tx("AI evaluation")}</h2><Link className="text-xs underline" href="/dashboard/ai/agents">{tx("AI agents")}</Link></div>
      <p role="note" className="text-xs border border-amber-300 bg-amber-50 rounded p-2">{label || tx("SYNTHETIC test data.")}</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      <section className="border rounded p-2 bg-white space-y-2">
        <div className="flex flex-wrap gap-2 items-end text-xs">
          <label>{tx("Corpus")} <select aria-label={tx("Corpus")} className="border rounded block" value={corpus} onChange={(e) => { setCorpus(e.target.value); setVerify(null); }}>{corpora.map((c) => <option key={c.corpus_id} value={c.corpus_id}>{c.corpus_id} {tx("v")}{c.version} ({c.cases} {tx("cases)")}</option>)}</select></label>
          <label>{tx("Adapter")} <select aria-label={tx("Adapter")} className="border rounded block" value={adapter} onChange={(e) => setAdapter(e.target.value)}>{Object.entries(adapters).map(([k, a]) => <option key={k} value={k}>{k}{a.available ? "" : tx(" (unavailable)")}</option>)}</select></label>
          <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={start}>{tx("Run evaluation")}</button>
          <button className="border rounded px-2 py-1" onClick={doVerify}>{tx("Check scorers on this corpus")}</button>
        </div>
        {adapters[adapter] && <p className="text-xs text-gray-600">{adapters[adapter].provider} {tx("· model")} {adapters[adapter].model_id}{adapters[adapter].tasks ? ` · tasks ${adapters[adapter].tasks!.join(", ")}` : tx(" · all tasks")}{adapters[adapter].unavailable_reason ? ` · unavailable: ${adapters[adapter].unavailable_reason}` : ""}</p>}
        {verify && (verify.length ? <ul className="text-xs text-red-700 list-disc pl-5">{verify.map((p, i) => <li key={i}>{p}</li>)}</ul> : <p className="text-xs text-green-700">{tx("Every golden answer passes and every adversarial output is caught by the scorers it names.")}</p>)}
      </section>
      <div className="grid lg:grid-cols-[320px_1fr] gap-4">
        <aside className="space-y-1">{runs.map((r) => <button key={r.id} onClick={() => open(r.id)} className={`block w-full text-left border rounded px-2 py-1 text-xs ${cur?.id === r.id ? "bg-indigo-50" : "bg-white"}`}>
          <b>{r.corpus_id}</b> {tx("v")}{r.corpus_version} · {r.adapter} · {r.status === "DONE" ? `${r.passed}/${r.total}` : r.status.toLowerCase()} · {r.review_status.toLowerCase()}<br /><span className="text-gray-500">{new Date(r.created_at).toLocaleString()} · {r.data_kind}</span></button>)}
          {!runs.length && <p className="text-xs text-gray-500">{tx("No runs yet.")}</p>}</aside>
        {cur && <section className="space-y-2">
          <div className="border rounded p-2 bg-white text-xs space-y-1">
            <p><b>{cur.corpus_id}</b> {tx("v")}{cur.corpus_version} {tx("· adapter")} {cur.adapter} {tx("· model")} {cur.model_id} ({cur.provider}) · <span className="font-semibold">{cur.data_kind}</span></p>
            <p className="text-gray-600 break-all">{tx("corpus sha256")} {cur.corpus_sha256.slice(0, 16)}{tx("… · config")} {cur.config_hash.slice(0, 16)}{tx("… · result digest")} {cur.summary?.digest?.slice(0, 16)}…</p>
            <p>{tx("Real-world calibration:")} {cur.real_calibration ? tx("recorded") : tx("none (this run says nothing about production accuracy)")}</p>
            {cur.status !== "DONE" && <p className="text-red-700">{tx("Not scored:")} {cur.note}</p>}
            <table className="border w-full"><thead><tr className="bg-gray-50 text-left"><th className="p-1">{tx("Scorer")}</th><th>{tx("Passed")}</th></tr></thead><tbody>{Object.entries(sc).map(([k, v]) => <tr key={k} className="border-t"><td className="p-1">{k}</td><td className={v.passed < v.total ? "text-red-700" : ""}>{v.passed}/{v.total}</td></tr>)}</tbody></table>
          </div>
          <div className="flex flex-wrap gap-2 items-center text-xs">
            <label className="inline-flex gap-1"><input type="checkbox" checked={failedOnly} onChange={(e) => { setFailedOnly(e.target.checked); open(cur.id, e.target.checked); }} />{tx("Failures only")}</label>
            <select aria-label={tx("Compare with")} className="border rounded" value={other} onChange={(e) => setOther(e.target.value)}><option value="">{tx("Compare with an earlier run…")}</option>{runs.filter((r) => r.corpus_id === cur.corpus_id && r.id !== cur.id).map((r) => <option key={r.id} value={r.id}>{r.adapter} {new Date(r.created_at).toLocaleString()}</option>)}</select>
            <button className="border rounded px-2 py-1 disabled:opacity-50" disabled={!other} onClick={compare}>{tx("Compare")}</button>
            {cmp && <span>{cmp.same_digest ? tx("identical results") : `regressions: ${cmp.regressions.join(", ") || "none"}; fixed: ${cmp.fixed.join(", ") || "none"}`}{cmp.same_config ? "" : tx(" (different configuration)")}</span>}
          </div>
          <ul className="space-y-1 text-xs">{cur.results.map((c) => <li key={c.case_id} className={`border rounded p-2 bg-white ${c.passed ? "" : "border-red-300"}`}>
            <b>{c.case_id}</b> · {c.passed ? tx("pass") : "FAIL"} · {c.latency_ms} {tx("ms (")}{c.actual?.latency_source ?? tx("measured")}) · {c.tokens} {tx("tokens · cost")} {c.cost}{c.error ? tx(" · error {error}", { error: c.error }) : ""}
            <div className="flex flex-wrap gap-1 mt-1">{Object.entries(c.scores).map(([k, s]) => <span key={k} title={s.detail} className={`px-1 rounded border ${s.passed ? "bg-green-50 border-green-200" : "bg-red-50 border-red-300"}`}>{k}: {s.passed ? tx("ok") : s.detail}</span>)}</div>
            <details><summary className="cursor-pointer">{tx("expected vs actual")}</summary>
              <p className="font-semibold">{tx("Expected")}</p><pre className="whitespace-pre-wrap break-all">{JSON.stringify(c.expected, null, 1)}</pre>
              <p className="font-semibold">{tx("Actual")}</p><pre className="whitespace-pre-wrap break-all">{JSON.stringify(c.actual, null, 1)}</pre></details></li>)}</ul>
          <div className="border rounded p-2 bg-white text-xs space-y-1">
            <p>{tx("Review:")} <b>{cur.review_status.toLowerCase()}</b>{cur.reviewed_by ? tx(" by {reviewed_by}: {review_note}", { reviewed_by: cur.reviewed_by, review_note: cur.review_note }) : tx(" (a second person with approval rights reviews the evidence)")}</p>
            <input aria-label={tx("Review note")} className="border rounded w-full px-1" placeholder={tx("What you inspected and decided")} value={note} onChange={(e) => setNote(e.target.value)} />
            <button className="border rounded px-2 py-1 mr-2 disabled:opacity-50" disabled={note.length < 3} onClick={() => review("ACCEPTED")}>{tx("Accept results")}</button>
            <button className="border rounded px-2 py-1 disabled:opacity-50" disabled={note.length < 3} onClick={() => review("REJECTED")}>{tx("Reject results")}</button>
          </div>
        </section>}
      </div>
    </div>
  );
}
