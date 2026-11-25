"use client";
// M43.S01.T010 playbooks: author → submit → approve (another manager) → run on a deal with conditional questions;
// stage guidance; mutual deal plan shared with the customer; outcome report.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";

interface Q { key: string; text: string; type: "text" | "yesno" | "number" | "choice"; required: boolean; choices: string[];
  maps_to: string | null; show_if: { key: string; equals: unknown } | null; help: string | null }
interface Playbook { id: string; family_id: string; version: number; name: string; purpose: string; stage_id: string | null;
  guidance: string | null; questions: Q[]; blocks_stage_exit: boolean; status: string }
interface Step { id?: string; title: string; owner: "us" | "customer"; due_date: string | null; done: boolean }

const err = (e: unknown, fb: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof d === "string" ? d : (d as { message?: string })?.message ?? fb;
};
const SAMPLE = JSON.stringify([
  { key: "decision_maker", text: "Did we meet the person who signs the order?", type: "yesno", required: true },
  { key: "who", text: "Who signs?", type: "text", required: true, show_if: { key: "decision_maker", equals: false } },
  { key: "monthly_cases", text: "Expected POVU cases per month", type: "number", required: true },
  { key: "value", text: "Expected order value (KES)", type: "number", maps_to: "expected_revenue" },
], null, 2);

export default function CRMPlaybooksPage() {
  const [items, setItems] = useState<Playbook[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", purpose: "QUALIFICATION", stage_id: "", guidance: "", questions: SAMPLE, blocks_stage_exit: false });
  const [recordId, setRecordId] = useState("");
  const load = useCallback(() => { apiClient.get("/api/v1/crm-playbooks").then((r) => setItems(r.data)).catch(() => setItems([])); }, []);
  useEffect(() => { load(); }, [load]);
  const act = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); setMsg(ok); load(); } catch (e) { setMsg(err(e, "Not allowed.")); } };

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-lg font-semibold">Playbooks &amp; guided selling</h2>
      {msg && <p role="status" className="text-sm text-gray-700">{msg}</p>}
      <div className="grid lg:grid-cols-2 gap-4">
        <section className="space-y-2">
          <h3 className="text-sm font-semibold">Library</h3>
          {items.length === 0 && <p className="text-xs text-gray-500">No playbooks yet.</p>}
          {items.map((p) => (
            <div key={p.id} className="border rounded p-2 text-xs bg-white space-y-1">
              <div className="flex justify-between gap-2"><span className="font-medium">{p.name} · v{p.version}</span><span>{p.purpose} · {p.status}{p.blocks_stage_exit && " · stage gate"}</span></div>
              {p.guidance && <p className="text-gray-600">{p.guidance}</p>}
              <div className="flex flex-wrap gap-2">
                {p.status === "DRAFT" && <button className="underline" onClick={() => act(() => apiClient.post(`/api/v1/crm-playbooks/${p.id}/lifecycle/submit`), "Sent for approval.")}>Submit</button>}
                {p.status === "PENDING_APPROVAL" && <>
                  <button className="underline text-green-700" onClick={() => act(() => apiClient.post(`/api/v1/crm-playbooks/${p.id}/lifecycle/approve`), "Published.")}>Approve</button>
                  <button className="underline" onClick={() => act(() => apiClient.post(`/api/v1/crm-playbooks/${p.id}/lifecycle/reject`), "Back to draft.")}>Reject</button></>}
                {p.status === "PUBLISHED" && <button className="underline" onClick={() => act(() => apiClient.post(`/api/v1/crm-playbooks/${p.id}/lifecycle/new-version`), "New draft version created.")}>New version</button>}
                <button className="underline" onClick={async () => { try { const r = (await apiClient.get(`/api/v1/crm-playbooks/${p.family_id}/report`)).data;
                  setMsg(`${p.name}: ${r.completed}/${r.runs} runs completed · win rate with ${r.with_playbook.win_rate ?? "—"} vs without ${r.without_playbook.win_rate ?? "—"} (${r.note})`); } catch (e) { setMsg(err(e, "Managers only.")); } }}>Report</button>
              </div>
            </div>
          ))}
          <form className="border rounded p-2 bg-white space-y-1 text-xs" onSubmit={(e) => { e.preventDefault();
            let questions; try { questions = JSON.parse(draft.questions); } catch { setMsg("Questions must be valid JSON."); return; }
            act(() => apiClient.post("/api/v1/crm-playbooks", { ...draft, stage_id: draft.stage_id || null, questions }), "Draft saved."); }}>
            <div className="font-semibold">New playbook (CRM managers)</div>
            <input className="border rounded px-2 py-1 w-full" required placeholder="Name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
            <select className="border rounded px-2 py-1" value={draft.purpose} onChange={(e) => setDraft({ ...draft, purpose: e.target.value })}>
              {["CALL", "VISIT", "QUALIFICATION", "STAGE"].map((x) => <option key={x}>{x}</option>)}</select>
            {draft.purpose === "STAGE" && <>
              <input className="border rounded px-2 py-1 w-full" placeholder="Pipeline stage id" value={draft.stage_id} onChange={(e) => setDraft({ ...draft, stage_id: e.target.value })} />
              <label className="flex gap-1 items-center"><input type="checkbox" checked={draft.blocks_stage_exit} onChange={(e) => setDraft({ ...draft, blocks_stage_exit: e.target.checked })} /> Must be completed before the deal leaves this stage</label></>}
            <textarea className="border rounded px-2 py-1 w-full" rows={2} placeholder="Stage guidance" value={draft.guidance} onChange={(e) => setDraft({ ...draft, guidance: e.target.value })} />
            <textarea aria-label="Questions (JSON)" className="border rounded px-2 py-1 w-full font-mono" rows={8} value={draft.questions} onChange={(e) => setDraft({ ...draft, questions: e.target.value })} />
            <button className="bg-indigo-600 text-white rounded px-3 py-1">Save draft</button>
          </form>
        </section>
        <section className="space-y-2">
          <h3 className="text-sm font-semibold">Run on a deal</h3>
          <EntityPicker kind="crm_record" value={recordId} onChange={setRecordId} placeholder="Choose a lead or deal…" />
          {recordId && <DealScore recordId={recordId} />}
          {recordId && <Guide recordId={recordId} onMsg={setMsg} />}
          {recordId && <DealPlan recordId={recordId} onMsg={setMsg} />}
          {recordId && <Splits recordId={recordId} onMsg={setMsg} />}
        </section>
      </div>
    </div>
  );
}

function Guide({ recordId, onMsg }: { recordId: string; onMsg: (m: string) => void }) {
  const [g, setG] = useState<{ playbooks: Playbook[]; runs: { id: string; playbook_id: string; completed: boolean }[] } | null>(null);
  const [active, setActive] = useState<Playbook | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [runId, setRunId] = useState<string | null>(null);
  useEffect(() => { apiClient.get(`/api/v1/crm-playbooks/records/${recordId}/guide`).then((r) => setG(r.data)).catch(() => setG(null)); setActive(null); }, [recordId]);
  const shown = (active?.questions ?? []).filter((q) => !q.show_if || answers[q.show_if.key] === q.show_if.equals);
  async function save(complete: boolean) {
    if (!active) return;
    try {
      const r = (await apiClient.post(`/api/v1/crm-playbooks/records/${recordId}/runs`, { playbook_id: active.id, answers, complete, run_id: runId })).data;
      setRunId(r.completed ? null : r.id);
      onMsg(r.completed ? `Playbook completed${r.updated_fields.length ? `; updated ${r.updated_fields.join(", ")}` : ""}.` : "Saved.");
      if (r.completed) setActive(null);
    } catch (e) { onMsg(err(e, "Check the answers.")); }
  }
  if (!g) return null;
  return (
    <div className="border rounded p-2 bg-white text-xs space-y-2">
      {g.playbooks.length === 0 && <p className="text-gray-500">No published playbook applies to this record.</p>}
      <div className="flex flex-wrap gap-2">{g.playbooks.map((p) => (
        <button key={p.id} className={`border rounded px-2 py-1 ${active?.id === p.id ? "bg-indigo-600 text-white" : ""}`}
                onClick={() => { setActive(p); setAnswers({}); setRunId(null); }}>{p.name}{g.runs.some((r) => r.playbook_id === p.id && r.completed) ? " ✓" : ""}</button>
      ))}</div>
      {active && (
        <div className="space-y-2">
          {active.guidance && <p className="bg-indigo-50 rounded p-2">{active.guidance}</p>}
          {shown.map((q) => (
            <label key={q.key} className="block">
              <span>{q.text}{q.required && " *"}</span>
              {q.type === "yesno" ? (
                <span className="flex gap-3 mt-1">{[true, false].map((v) => (
                  <label key={String(v)} className="flex gap-1 items-center"><input type="radio" name={q.key} checked={answers[q.key] === v} onChange={() => setAnswers({ ...answers, [q.key]: v })} />{v ? "Yes" : "No"}</label>))}</span>
              ) : q.type === "choice" ? (
                <select className="border rounded px-2 py-1 w-full mt-1" value={String(answers[q.key] ?? "")} onChange={(e) => setAnswers({ ...answers, [q.key]: e.target.value })}>
                  <option value="">—</option>{q.choices.map((c) => <option key={c}>{c}</option>)}</select>
              ) : (
                <input className="border rounded px-2 py-1 w-full mt-1" type={q.type === "number" ? "number" : "text"} value={String(answers[q.key] ?? "")}
                       onChange={(e) => setAnswers({ ...answers, [q.key]: q.type === "number" ? (e.target.value === "" ? "" : +e.target.value) : e.target.value })} />
              )}
              {q.help && <span className="text-gray-500">{q.help}</span>}
            </label>
          ))}
          <div className="flex gap-2"><button className="border rounded px-2 py-1" onClick={() => save(false)}>Save progress</button>
            <button className="bg-green-600 text-white rounded px-2 py-1" onClick={() => save(true)}>Complete</button></div>
        </div>
      )}
    </div>
  );
}

function DealPlan({ recordId, onMsg }: { recordId: string; onMsg: (m: string) => void }) {
  const [title, setTitle] = useState("Path to first POVU order");
  const [steps, setSteps] = useState<Step[]>([]);
  const [link, setLink] = useState<string | null>(null);
  useEffect(() => {
    apiClient.get(`/api/v1/crm-playbooks/records/${recordId}/plan`).then((r) => {
      if (r.data) { setTitle(r.data.title); setSteps(r.data.steps); } else setSteps([]);
    }).catch(() => setSteps([]));
    setLink(null);
  }, [recordId]);
  const save = async () => { try { await apiClient.put(`/api/v1/crm-playbooks/records/${recordId}/plan`, { title, steps }); onMsg("Deal plan saved."); } catch (e) { onMsg(err(e, "Check the steps.")); } };
  return (
    <div className="border rounded p-2 bg-white text-xs space-y-1">
      <div className="font-semibold">Deal plan (shared with the customer)</div>
      <input className="border rounded px-2 py-1 w-full" value={title} onChange={(e) => setTitle(e.target.value)} />
      {steps.map((s, i) => (
        <div key={s.id ?? i} className="flex flex-wrap gap-1 items-center">
          <input type="checkbox" checked={s.done} onChange={(e) => setSteps(steps.map((x, j) => j === i ? { ...x, done: e.target.checked } : x))} aria-label="Done" />
          <input className="border rounded px-1 flex-1 min-w-[8rem]" value={s.title} onChange={(e) => setSteps(steps.map((x, j) => j === i ? { ...x, title: e.target.value } : x))} />
          <select className="border rounded" value={s.owner} onChange={(e) => setSteps(steps.map((x, j) => j === i ? { ...x, owner: e.target.value as Step["owner"] } : x))}>
            <option value="us">POVU</option><option value="customer">Customer</option></select>
          <input type="date" className="border rounded" value={s.due_date ?? ""} onChange={(e) => setSteps(steps.map((x, j) => j === i ? { ...x, due_date: e.target.value || null } : x))} />
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        <button className="underline" onClick={() => setSteps([...steps, { title: "", owner: "us", due_date: null, done: false }])}>+ Step</button>
        <button className="bg-indigo-600 text-white rounded px-2 py-0.5" onClick={save}>Save</button>
        <button className="underline" onClick={async () => { try { const r = (await apiClient.post(`/api/v1/crm-playbooks/records/${recordId}/plan/share`, null, { params: { on: true } })).data; setLink(r.share_url); } catch (e) { onMsg(err(e, "Save the plan first.")); } }}>Share link</button>
        <button className="underline text-red-600" onClick={async () => { await apiClient.post(`/api/v1/crm-playbooks/records/${recordId}/plan/share`, null, { params: { on: false } }).catch(() => null); setLink(null); onMsg("Sharing stopped."); }}>Stop sharing</button>
      </div>
      {link && <p className="break-all">Send this to the customer: <a className="text-indigo-600 underline" href={link}>{link}</a></p>}
    </div>
  );
}

// M43.S01.T012: transparent deal score with factors, missing data, buying-group coverage and trend
function DealScore({ recordId }: { recordId: string }) {
  const [d, setD] = useState<{ score: number; method: string; missing: string[];
    factors: { factor: string; value: number; weight: number; reason: string }[];
    buying_group: { roles: string[]; coverage: number; missing: string[]; blockers: number };
    trend: { at: string; score: number }[] } | null>(null);
  useEffect(() => { apiClient.get(`/api/v1/crm-playbooks/records/${recordId}/score`).then((r) => setD(r.data)).catch(() => setD(null)); }, [recordId]);
  if (!d) return null;
  return (
    <div className="border rounded p-2 bg-white text-xs space-y-1">
      <div className="flex justify-between"><span className="font-semibold">Deal score {d.score}/100</span>
        <span className="text-gray-500">{d.trend.length > 1 ? `was ${d.trend[d.trend.length - 2].score}` : ""}</span></div>
      {d.factors.map((f) => <div key={f.factor} className="flex justify-between gap-2"><span>{f.reason}</span><span className="text-gray-500">{Math.round(f.value * 100)}% × {f.weight}</span></div>)}
      {d.missing.length > 0 && <p className="text-gray-500">No data yet (left out): {d.missing.join(", ")}.</p>}
      {d.buying_group.missing.length > 0 && <p className="text-amber-700">Buying group: add {d.buying_group.missing.join(", ")} (link contacts with these roles).</p>}
      {d.buying_group.blockers > 0 && <p className="text-red-600">{d.buying_group.blockers} known blocker(s) on this deal.</p>}
      <p className="text-gray-400">{d.method}</p>
    </div>
  );
}

// M43.S01.T014: deal splits (shares must total 100%)
function Splits({ recordId, onMsg }: { recordId: string; onMsg: (m: string) => void }) {
  const [rows, setRows] = useState<{ user_id: string; share_pct: number }[]>([]);
  const [pick, setPick] = useState("");
  useEffect(() => { apiClient.get(`/api/v1/crm-routing/records/${recordId}/splits`).then((r) => setRows(r.data)).catch(() => setRows([])); }, [recordId]);
  const total = rows.reduce((a, r) => a + (+r.share_pct || 0), 0);
  return (
    <div className="border rounded p-2 bg-white text-xs space-y-1">
      <div className="font-semibold">Deal split (credit sharing)</div>
      {rows.map((r, i) => (
        <div key={r.user_id} className="flex gap-2 items-center"><span className="flex-1">{r.user_id.slice(0, 8)}…</span>
          <input type="number" min={1} max={100} className="border rounded w-16 px-1" value={r.share_pct} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, share_pct: +e.target.value } : x))} />%
          <button className="text-red-600" onClick={() => setRows(rows.filter((_, j) => j !== i))}>×</button></div>))}
      <EntityPicker kind="user" value={pick} onChange={(id) => { if (id && !rows.some((r) => r.user_id === id)) setRows([...rows, { user_id: id, share_pct: 0 }]); setPick(""); }} placeholder="Add a person…" />
      <div className={total === 100 || rows.length === 0 ? "text-gray-500" : "text-red-600"}>Total {total}%</div>
      <button className="border rounded px-2 py-0.5" onClick={async () => {
        try { await apiClient.put(`/api/v1/crm-routing/records/${recordId}/splits`, rows); onMsg("Split saved."); }
        catch (e) { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; onMsg(typeof d === "string" ? d : "Shares must total 100%."); }
      }}>Save split</button>
    </div>
  );
}
