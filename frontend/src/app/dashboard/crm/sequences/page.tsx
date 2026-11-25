"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, type CRMRecord, type Enrollment, type Sequence, type SequenceStep } from "@/lib/crm_pipeline";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg).join("; ");
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Request failed.";
}

const NEW_STEP = (n: number): SequenceStep => ({ step_no: n, delay_days: n === 1 ? 0 : 3, subject: "", body: "" });

export default function CRMSequencesPage() {
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [selected, setSelected] = useState<Sequence | null>(null);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [leads, setLeads] = useState<CRMRecord[]>([]);
  const [recordId, setRecordId] = useState("");
  const [name, setName] = useState("");
  const [track, setTrack] = useState(false);
  const [steps, setSteps] = useState<SequenceStep[]>([NEW_STEP(1)]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSequences(await crmApi.getSequences());
      setLeads((await crmApi.getAllRecords({ status: "OPEN", limit: 200 })).filter((r) => r.contact_email));
    } catch (e) { setError(errorText(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (selected) crmApi.getEnrollments(selected.id).then(setEnrollments).catch((e) => setError(errorText(e)));
  }, [selected]);

  async function act(fn: () => Promise<unknown>, msg: string) {
    setError(null);
    try {
      await fn();
      setInfo(msg);
      await load();
      if (selected) setEnrollments(await crmApi.getEnrollments(selected.id));
    } catch (e) { setError(errorText(e)); }
  }

  const input = "text-sm border rounded-lg px-2 py-1.5";
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Sales Sequences</h1>
        <p className="text-sm text-gray-500">Timed follow-up e-mails through the outbox. A sequence stops when the contact replies, unsubscribes, has no consent, or the deal closes. Placeholders: {"{contact_name}"} {"{company_name}"}. Each record goes through a sequence once.</p>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {info && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}

      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-2">Sequences</h2>
        {sequences.length === 0 ? <p className="text-sm text-gray-400">No sequences yet.</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">Name</th><th>Steps</th><th>Active / done / stopped</th><th /></tr></thead>
            <tbody>{sequences.map((q) => (
              <tr key={q.id} className="border-t">
                <td className="py-1.5"><button className="text-indigo-700 underline" onClick={() => setSelected(q)}>{q.name}</button>{!q.active_flag && " (paused)"}</td>
                <td className="text-xs">{q.steps.map((st) => `#${st.step_no} +${st.delay_days}d`).join(" → ")}</td>
                <td>{q.enrollments.ACTIVE ?? 0} / {q.enrollments.COMPLETED ?? 0} / {q.enrollments.STOPPED ?? 0}</td>
                <td className="text-right"><button className="text-xs underline" onClick={() => act(() => crmApi.setSequenceActive(q.id, !q.active_flag), q.active_flag ? "Paused." : "Resumed.")}>{q.active_flag ? "Pause" : "Resume"}</button></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>

      <form aria-label="New sequence" className="bg-white rounded-xl border shadow-sm p-4 space-y-2"
        onSubmit={(e) => { e.preventDefault(); act(() => crmApi.createSequence({ name, steps, track_engagement: track }), "Sequence created."); setName(""); setTrack(false); setSteps([NEW_STEP(1)]); }}>
        <h2 className="font-semibold text-gray-800">New sequence</h2>
        <input aria-label="Sequence name" required placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} className={`${input} w-full`} />
        {steps.map((st, i) => (
          <div key={st.step_no} className="grid md:grid-cols-6 gap-2 border-t pt-2">
            <span className="text-xs text-gray-500 self-center">Step {st.step_no}</span>
            <label className="text-xs text-gray-500">Wait (days)
              <input aria-label={`Step ${st.step_no} delay`} type="number" min={0} max={365} value={st.delay_days}
                onChange={(e) => setSteps(steps.map((x, j) => (j === i ? { ...x, delay_days: +e.target.value } : x)))} className={`${input} w-full`} />
            </label>
            <input aria-label={`Step ${st.step_no} subject`} required placeholder="Subject" value={st.subject}
              onChange={(e) => setSteps(steps.map((x, j) => (j === i ? { ...x, subject: e.target.value } : x)))} className={`${input} md:col-span-4`} />
            <textarea aria-label={`Step ${st.step_no} body`} required rows={2} placeholder="Message" value={st.body}
              onChange={(e) => setSteps(steps.map((x, j) => (j === i ? { ...x, body: e.target.value } : x)))} className={`${input} md:col-span-6`} />
          </div>
        ))}
        <label className="flex items-center gap-2 text-xs text-gray-600"><input type="checkbox" checked={track} onChange={(e) => setTrack(e.target.checked)} /> Track opens and clicks (only if tracking is switched on for the company; recipients can opt out; opens are an indicator, not proof of reading)</label>
        <div className="flex gap-2">
          <button type="button" className="px-3 py-1.5 text-sm border rounded-lg" onClick={() => setSteps([...steps, NEW_STEP(steps.length + 1)])}>Add step</button>
          <button type="submit" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg">Create sequence</button>
        </div>
      </form>

      {selected && (
        <div className="bg-white rounded-xl border shadow-sm p-4 space-y-3 overflow-x-auto">
          <h2 className="font-semibold text-gray-800">{selected.name}: enrolments</h2>
          <form aria-label="Enroll record" className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); act(() => crmApi.enrollInSequence(selected.id, recordId), "Enrolled."); }}>
            <select aria-label="Record to enroll" required value={recordId} onChange={(e) => setRecordId(e.target.value)} className={input}>
              <option value="">Choose an open record with an e-mail…</option>
              {leads.map((l) => <option key={l.id} value={l.id}>{l.company_name} — {l.contact_email}</option>)}
            </select>
            <button type="submit" className="px-3 py-1.5 text-sm border rounded-lg">Enroll</button>
          </form>
          {enrollments.length === 0 ? <p className="text-sm text-gray-400">Nobody enrolled yet.</p> : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">Record</th><th>E-mail</th><th>Status</th><th>Next</th><th /></tr></thead>
              <tbody>{enrollments.map((en) => (
                <tr key={en.id} className="border-t">
                  <td className="py-1.5"><Link className="underline" href={`/dashboard/crm/records/${en.crm_record_id}`}>{en.company_name}</Link></td>
                  <td>{en.email}</td><td>{en.status}{en.stop_reason ? ` — ${en.stop_reason}` : ""}</td>
                  <td>{en.status === "ACTIVE" ? `step ${en.next_step_no}, ${new Date(en.next_due_at).toLocaleString()}` : "—"}</td>
                  <td>{en.status === "ACTIVE" && <button className="text-xs underline" onClick={() => act(() => crmApi.stopEnrollment(en.id, "contact replied (logged by rep)"), "Stopped.")}>Mark replied</button>}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
