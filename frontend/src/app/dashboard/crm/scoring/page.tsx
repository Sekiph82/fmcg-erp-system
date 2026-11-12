"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { crmApi, type ScoreQueueItem, type ScoreRuleInput, type ScoreRulesResponse } from "@/lib/crm_pipeline";

const OPS: Record<string, string[]> = { text: ["eq", "in"], number: ["gt", "gte", "lte"], bool: ["true"], count: ["per_item", "gte"] };

function errorText(e: unknown) {
  const detail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "detail" in detail) return String((detail as { detail: unknown }).detail);
  return "Request failed.";
}

const EMPTY: ScoreRuleInput = { name: "", category: "FIT", field: "source_type", operator: "in", value: "", points: 10 };

export default function LeadScoringPage() {
  const [rules, setRules] = useState<ScoreRulesResponse | null>(null);
  const [queue, setQueue] = useState<ScoreQueueItem[]>([]);
  const [draft, setDraft] = useState<ScoreRuleInput>(EMPTY);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [r, q] = await Promise.all([crmApi.getScoreRules(), crmApi.getScoreQueue(50)]);
      setRules(r);
      setQueue(q);
    } catch (e) {
      setError(errorText(e));
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function act(fn: () => Promise<unknown>, done: string) {
    setError(null);
    try {
      await fn();
      setMessage(done);
      await load();
    } catch (e) {
      setError(errorText(e));
    }
  }

  const kind = rules?.fields[draft.field] ?? "text";
  const shownRules = rules ? (rules.using_defaults ? rules.defaults : rules.rules) : [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Lead Scoring</h1>
          <p className="text-sm text-gray-500">Rules add fit and engagement points (0–100). Hot ≥ 70, warm ≥ 40. Every change is kept with its explanation.</p>
        </div>
        <div className="flex gap-2">
          {rules?.using_defaults && (
            <button className="px-3 py-1.5 text-sm border rounded-lg" onClick={() => act(crmApi.seedScoreRules, "Default rules copied; you can now edit them.")}>
              Make default rules editable
            </button>
          )}
          <button className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg"
            onClick={() => act(async () => {
              const r = await crmApi.recalculateScores();
              setMessage(`Rescored ${r.scored} open records; ${r.changed} changed.`);
            }, "Scores recalculated.")}>
            Recalculate all
          </button>
        </div>
      </div>
      {error && <p role="alert" className="rounded-lg p-3 text-sm bg-red-50 border border-red-200 text-red-700">{error}</p>}
      {message && !error && <p role="status" className="rounded-lg p-3 text-sm bg-emerald-50 border border-emerald-200 text-emerald-800">{message}</p>}

      <div className="bg-white rounded-xl border shadow-sm p-4 overflow-x-auto">
        <h2 className="font-semibold text-gray-800 mb-1">Rules {rules?.using_defaults && <span className="text-xs font-normal text-amber-700">(built-in defaults in use)</span>}</h2>
        <table className="w-full text-sm mt-2">
          <thead><tr className="text-left text-xs text-gray-500"><th className="py-1">Rule</th><th>Category</th><th>Condition</th><th className="text-right">Points</th><th /></tr></thead>
          <tbody>
            {shownRules.map((r, i) => (
              <tr key={"id" in r ? String(r.id) : i} className="border-t">
                <td className="py-1.5">{r.name}</td><td>{r.category}</td>
                <td className="font-mono text-xs">{r.field} {r.operator} {r.value ?? ""}</td>
                <td className="text-right">{r.points}{r.max_points != null ? ` (max ${r.max_points})` : ""}</td>
                <td className="text-right">
                  {"id" in r && (
                    <button className="text-xs underline" onClick={() => act(() => crmApi.updateScoreRule(String(r.id), { active_flag: !r.active_flag }), "Rule updated.")}>
                      {r.active_flag ? "Disable" : "Enable"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <form aria-label="New score rule" className="flex flex-wrap items-end gap-2 mt-4"
          onSubmit={(e) => { e.preventDefault(); act(() => crmApi.createScoreRule(draft), "Rule added."); setDraft(EMPTY); }}>
          <input aria-label="Rule name" required placeholder="Rule name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5" />
          <select aria-label="Category" value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value as "FIT" | "ENGAGEMENT" })} className="text-sm border rounded-lg px-2 py-1.5">
            <option value="FIT">Fit</option><option value="ENGAGEMENT">Engagement</option>
          </select>
          <select aria-label="Field" value={draft.field} onChange={(e) => { const f = e.target.value; setDraft({ ...draft, field: f, operator: OPS[rules?.fields[f] ?? "text"][0] }); }} className="text-sm border rounded-lg px-2 py-1.5">
            {Object.keys(rules?.fields ?? {}).map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
          <select aria-label="Operator" value={draft.operator} onChange={(e) => setDraft({ ...draft, operator: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5">
            {OPS[kind].map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
          {draft.operator !== "true" && draft.operator !== "per_item" && (
            <input aria-label="Value" placeholder="Value" value={draft.value ?? ""} onChange={(e) => setDraft({ ...draft, value: e.target.value })} className="text-sm border rounded-lg px-2 py-1.5 w-32" />
          )}
          <input aria-label="Points" type="number" min={-100} max={100} value={draft.points} onChange={(e) => setDraft({ ...draft, points: +e.target.value })} className="text-sm border rounded-lg px-2 py-1.5 w-20" />
          <button type="submit" className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg">Add rule</button>
        </form>
      </div>

      <div className="bg-white rounded-xl border shadow-sm p-4">
        <h2 className="font-semibold text-gray-800 mb-3">Prioritised open leads</h2>
        {queue.length === 0 ? <p className="text-sm text-gray-400">No open leads you can see.</p> : (
          <ul className="divide-y">
            {queue.map((q) => (
              <li key={q.id} className="py-2">
                <div className="flex items-center justify-between gap-2 text-sm">
                  <Link href={`/dashboard/crm/records/${q.id}`} className="font-medium text-indigo-700">{q.lead_code ?? "—"} · {q.company_name}</Link>
                  <span className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">{q.temperature}</span>
                    <span className="font-bold">{q.lead_score}</span>
                    <button className="text-xs underline" onClick={() => setOpen(open === q.id ? null : q.id)}>Why?</button>
                  </span>
                </div>
                {open === q.id && (
                  q.breakdown ? (
                    <ul className="mt-2 text-xs text-gray-600 space-y-0.5">
                      {q.breakdown.map((b) => <li key={b.rule}>{b.points > 0 ? "+" : ""}{b.points} {b.rule} <span className="text-gray-400">({b.reason})</span></li>)}
                    </ul>
                  ) : <p className="mt-2 text-xs text-gray-400">Not scored with rules yet — use Recalculate all.</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
