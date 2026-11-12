"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, type AutomationMeta, type AutomationRun } from "@/lib/crm_pipeline";

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg).join("; ");
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Request failed.";
}

const TRIGGER_LABELS: Record<string, string> = {
  created: "Record created", stage_changed: "Stage changed", won: "Deal won", lost: "Deal lost", status_changed: "Status changed",
};
const ACTION_LABELS: Record<string, string> = {
  create_task: "Create follow-up task", assign_owner: "Assign owner (round robin)", set_field: "Set a field", notify: "Notify users",
};

type Draft = { rule_name: string; trigger_event: string; condition_field: string; condition_value: string; action_type: string;
  subject: string; due_in_days: number; rep_ids: string; field: string; value: string; usernames: string; title: string };
const EMPTY: Draft = { rule_name: "", trigger_event: "created", condition_field: "", condition_value: "", action_type: "create_task",
  subject: "", due_in_days: 1, rep_ids: "", field: "temperature", value: "HOT", usernames: "", title: "" };

function payloadFor(d: Draft): Record<string, unknown> {
  if (d.action_type === "create_task") return { subject: d.subject, due_in_days: d.due_in_days };
  if (d.action_type === "assign_owner") return { rep_ids: d.rep_ids.split(",").map((x) => x.trim()).filter(Boolean) };
  if (d.action_type === "set_field") return { field: d.field, value: d.field === "temperature" ? d.value : Number(d.value) };
  return { usernames: d.usernames.split(",").map((x) => x.trim()).filter(Boolean), title: d.title };
}

export default function CRMAutomationPage() {
  const [meta, setMeta] = useState<AutomationMeta | null>(null);
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, r] = await Promise.all([crmApi.getAutomationRules(), crmApi.getAutomationRuns()]);
      setMeta(m);
      setRuns(r);
    } catch (e) { setError(errorText(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function act(fn: () => Promise<unknown>, msg?: string) {
    setError(null);
    try { await fn(); if (msg) setInfo(msg); await load(); } catch (e) { setError(errorText(e)); }
  }

  const input = "text-sm border rounded-lg px-2 py-1.5";
  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">CRM Automation</h1>
          <p className="text-sm text-gray-500">Rules run once per event (created, stage change, won, lost) — retried on failure, logged below. Rules never change stage or status.</p>
        </div>
        <button className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg"
          onClick={() => act(async () => { const r = await crmApi.processAutomation(); setInfo(`Queued ${r.queued}, done ${r.done}, retrying ${r.retry}, failed ${r.failed}.`); })}>
          Run now
        </button>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {info && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{info}</p>}

      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-2">Rules</h2>
        {meta && meta.rules.length === 0 ? <p className="text-sm text-gray-400">No automation rules yet.</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">Rule</th><th>When</th><th>If</th><th>Then</th><th /></tr></thead>
            <tbody>
              {meta?.rules.map((r) => (
                <tr key={r.rule_id} className="border-t">
                  <td className="py-1.5">{r.rule_name}</td>
                  <td>{TRIGGER_LABELS[r.trigger_event] ?? r.trigger_event}</td>
                  <td className="text-xs font-mono">{r.condition_field ? `${r.condition_field} ${r.condition_operator} ${r.condition_value}` : "always"}</td>
                  <td className="text-xs">{ACTION_LABELS[r.action_type] ?? r.action_type} <span className="font-mono text-gray-500">{JSON.stringify(r.action_payload)}</span></td>
                  <td className="text-right"><button className="text-xs underline" onClick={() => act(() => crmApi.updateAutomationRule(r.rule_id, { active_flag: !r.active_flag }))}>{r.active_flag ? "Pause" : "Resume"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <form aria-label="New automation rule" className="grid md:grid-cols-4 gap-2 mt-4"
          onSubmit={(e) => {
            e.preventDefault();
            act(() => crmApi.createAutomationRule({
              rule_name: draft.rule_name, trigger_event: draft.trigger_event,
              condition_field: draft.condition_field || null, condition_operator: draft.condition_field ? "eq" : null,
              condition_value: draft.condition_field ? draft.condition_value : null,
              action_type: draft.action_type, action_payload: payloadFor(draft),
            }), "Rule created.");
            setDraft(EMPTY);
          }}>
          <input aria-label="Rule name" required placeholder="Rule name" value={draft.rule_name} onChange={(e) => setDraft({ ...draft, rule_name: e.target.value })} className={input} />
          <select aria-label="When" value={draft.trigger_event} onChange={(e) => setDraft({ ...draft, trigger_event: e.target.value })} className={input}>
            {meta?.triggers.map((t) => <option key={t} value={t}>{TRIGGER_LABELS[t] ?? t}</option>)}
          </select>
          <select aria-label="Condition field" value={draft.condition_field} onChange={(e) => setDraft({ ...draft, condition_field: e.target.value })} className={input}>
            <option value="">Always</option>
            {meta?.condition_fields.map((f) => <option key={f} value={f}>{f} equals…</option>)}
          </select>
          <input aria-label="Condition value" disabled={!draft.condition_field} placeholder="value" value={draft.condition_value} onChange={(e) => setDraft({ ...draft, condition_value: e.target.value })} className={input} />
          <select aria-label="Action" value={draft.action_type} onChange={(e) => setDraft({ ...draft, action_type: e.target.value })} className={input}>
            {meta?.actions.map((a) => <option key={a} value={a}>{ACTION_LABELS[a] ?? a}</option>)}
          </select>
          {draft.action_type === "create_task" && <>
            <input aria-label="Task subject" required placeholder="Task subject" value={draft.subject} onChange={(e) => setDraft({ ...draft, subject: e.target.value })} className={input} />
            <input aria-label="Due in days" type="number" min={0} max={365} value={draft.due_in_days} onChange={(e) => setDraft({ ...draft, due_in_days: +e.target.value })} className={input} />
          </>}
          {draft.action_type === "assign_owner" && <input aria-label="Rep ids" required placeholder="rep ids, comma separated" value={draft.rep_ids} onChange={(e) => setDraft({ ...draft, rep_ids: e.target.value })} className={`${input} md:col-span-2`} />}
          {draft.action_type === "set_field" && <>
            <select aria-label="Field" value={draft.field} onChange={(e) => setDraft({ ...draft, field: e.target.value, value: e.target.value === "temperature" ? "HOT" : "1" })} className={input}>
              {Object.keys(meta?.settable_fields ?? {}).map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
            <input aria-label="Field value" value={draft.value} onChange={(e) => setDraft({ ...draft, value: e.target.value })} className={input} />
          </>}
          {draft.action_type === "notify" && <>
            <input aria-label="Usernames" required placeholder="usernames, comma separated" value={draft.usernames} onChange={(e) => setDraft({ ...draft, usernames: e.target.value })} className={input} />
            <input aria-label="Notification title" required placeholder="Title" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} className={input} />
          </>}
          <button type="submit" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg">Add rule</button>
        </form>
      </div>

      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-2">Run log</h2>
        {runs.length === 0 ? <p className="text-sm text-gray-400">No runs yet.</p> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">When</th><th>Rule</th><th>Event</th><th>Record</th><th>Status</th><th>Result</th><th /></tr></thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="py-1.5">{new Date(r.created_at).toLocaleString()}</td><td>{r.rule_name}</td><td>{r.event_type}</td>
                  <td><Link className="underline" href={`/dashboard/crm/records/${r.crm_record_id}`}>{r.company_name}</Link></td>
                  <td>{r.status}{r.attempts > 1 ? ` (${r.attempts})` : ""}</td>
                  <td className="text-xs">{r.error ?? r.result ?? "—"}</td>
                  <td>{r.status === "FAILED" && <button className="text-xs underline" onClick={() => act(() => crmApi.retryAutomationRun(r.id), "Run queued again.")}>Retry</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
