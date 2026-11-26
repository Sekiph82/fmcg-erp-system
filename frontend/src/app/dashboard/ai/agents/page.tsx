"use client";
// M45.S01.T008/T009 AI agent builder + M50.S01.T007/T008: conditionals, bounded loops, delegation with a permission ceiling,
// approval and error paths, reusable templates, live validation, version rollback; atomic budgets, approvals waiting for a
// person, stuck-run recovery and dead-letter controls.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Cond = { ref: string; op: string; value?: string | number; agg?: string };
type Step = {
  id: string; type: "tool" | "llm" | "condition" | "loop" | "delegate" | "approval"; tool?: string; args?: Record<string, unknown>; prompt?: string; template?: string;
  foreach?: string; next?: string; on_error?: string; if?: Cond; then?: string; else?: string; max_iterations?: number; body?: string[]; until?: Cond;
  agent?: string; input?: Record<string, unknown>; message?: string; on_deny?: string;
};
type Def = { trigger: { type: string; event?: string }; tools: string[]; knowledge?: Record<string, unknown>; steps: Step[]; delegates?: string[]; input_schema?: unknown; output_schema?: unknown };
type Agent = { id: string; name: string; template: string | null; status: string; stopped: boolean; current_version: number | null; schedule: Record<string, unknown> | null; budgets: Record<string, number>; next_run_at: string | null; last_run_at: string | null };
type Job = { id: string; version: number; trigger: string; status: string; attempts: number; tokens: number; cost: string; error: string | null; trace: { step: string; type: string; tool: string | null; items: number; output: string }[] | null; created_at: string };
type Detail = Agent & { versions: { version: number; status: string; definition: Def; created_by: string; approved_by: string | null }[]; jobs: Job[] };
type Catalog = {
  tools: Record<string, { label: string; write: boolean }>; templates: Record<string, { name: string; description: string; definition: Def }>;
  step_types: string[]; condition_ops: string[]; limits: { max_steps: number; max_loop_iterations: number; max_step_executions: number; max_delegation_depth: number };
  saved_templates: { id: string; name: string; description: string | null; definition: Def; created_by: string }[];
};
type Gate = { id: string; job_id: string; agent_id: string; step: string; message: string; requested_by: string; created_at: string };
type Usage = {
  counters: { scope: string; id: string; cap_cost: string; reserved_cost: string; spent_cost: string; reserved_tokens: number; spent_tokens: number }[];
  reservations: { id: string; job_id: string | null; status: string; reserved_cost: string; actual_cost: string; worker: string | null; expires_at: string; stuck: boolean }[];
  dead_letter: Job[]; usage: { source: string; outcome: string; calls: number; tokens: number; cost: string }[];
};

const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const GOV = ["company_cost_per_day", "user_cost_per_day", "reserve_tokens", "user_manual_runs_per_day"] as const;
const STEP_FIELDS: Record<Step["type"], string> = { tool: "Call a tool", llm: "Write with the model", condition: "If / else", loop: "Repeat (max 10)", delegate: "Hand to another agent", approval: "Ask a person" };

export default function AgentsPage() {
  const [cat, setCat] = useState<Catalog | null>(null);
  const [list, setList] = useState<Agent[]>([]);
  const [gov, setGov] = useState<Record<string, number | boolean>>({});
  const [cur, setCur] = useState<Detail | null>(null);
  const [def, setDef] = useState<Def | null>(null);
  const [input, setInput] = useState("{}");
  const [msg, setMsg] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [gates, setGates] = useState<Gate[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [tplName, setTplName] = useState("");
  const loadCat = useCallback(() => apiClient.get("/api/v1/ai-agents/catalog").then((r) => setCat(r.data)).catch(() => setCat(null)), []);
  const load = useCallback(() => {
    apiClient.get("/api/v1/ai-agents").then((r) => { setList(r.data.agents); setGov(r.data.settings); }).catch((e) => setMsg(err(e)));
    apiClient.get("/api/v1/ai-agents/gates").then((r) => setGates(r.data.gates)).catch(() => setGates([]));
    apiClient.get("/api/v1/ai-agents/budget/usage").then((r) => setUsage(r.data)).catch(() => setUsage(null));
  }, []);
  useEffect(() => { load(); loadCat(); }, [load, loadCat]);
  // live validation: the server is the single source of truth for what a valid definition is
  useEffect(() => {
    if (!def) { setErrors([]); return; }
    const t = setTimeout(() => apiClient.post("/api/v1/ai-agents/validate", { definition: def }).then((r) => setErrors(r.data.errors)).catch(() => setErrors(["Could not validate."])), 350);
    return () => clearTimeout(t);
  }, [def]);
  const open = (id: string) => apiClient.get(`/api/v1/ai-agents/${id}`).then((r) => { setCur(r.data); setDef(r.data.versions[0]?.definition ?? null); }).catch((e) => setMsg(err(e)));
  const act = (p: Promise<unknown>, ok: string) => p.then(() => { setMsg(ok); load(); if (cur) open(cur.id); }).catch((e) => setMsg(err(e)));
  const fromTemplate = (body: Record<string, unknown>, name: string) => apiClient.post("/api/v1/ai-agents", { name, ...body }).then((r) => { load(); open(r.data.id); setMsg(tx("Agent created as draft v1.")); }).catch((e) => setMsg(err(e)));
  const setStep = (i: number, patch: Partial<Step>) => def && setDef({ ...def, steps: def.steps.map((s, j) => (j === i ? { ...s, ...patch } : s)) });
  const latest = cur?.versions[0];
  const stepIds = def?.steps.map((s) => s.id) ?? [];
  const run = (simulate: boolean) => {
    let parsed: unknown; try { parsed = JSON.parse(input || "{}"); } catch { return setMsg(tx("Input must be JSON.")); }
    act(apiClient.post(`/api/v1/ai-agents/${cur!.id}/run`, { simulate, version: simulate ? latest?.version : undefined, input: parsed }), simulate ? "Simulated (nothing was written)." : "Run finished or waiting for approval.");
  };
  const jsonField = (label: string, value: unknown, on: (v: unknown) => void) =>
    <label className="block">{label}<textarea aria-label={label} className="border rounded w-full font-mono" rows={2} defaultValue={value ? JSON.stringify(value) : ""}
      onBlur={(e) => { if (!e.target.value.trim()) return on(undefined); try { on(JSON.parse(e.target.value)); } catch { setMsg(tx("{label} must be JSON.", { label })); } }} /></label>;
  const condEditor = (label: string, c: Cond | undefined, on: (c: Cond | undefined) => void) => <div className="flex flex-wrap gap-1 items-center">
    <span>{label}</span>
    <input aria-label={tx("{label} ref", { label })} className="border rounded w-24" placeholder={tx("s1.score")} value={c?.ref ?? ""} onChange={(e) => on({ op: "eq", ...c, ref: e.target.value })} />
    <select aria-label={tx("{label} operator", { label })} className="border rounded" value={c?.op ?? "eq"} onChange={(e) => on({ ref: "", ...c, op: e.target.value })}>{(cat?.condition_ops ?? []).map((o) => <option key={o}>{o}</option>)}</select>
    <input aria-label={tx("{label} value", { label })} className="border rounded w-20" value={String(c?.value ?? "")} onChange={(e) => on({ ref: "", op: "eq", ...c, value: e.target.value })} />
    <label className="inline-flex gap-1"><input type="checkbox" checked={c?.agg === "count"} onChange={(e) => on({ ref: "", op: "eq", ...c, agg: e.target.checked ? "count" : undefined })} />{tx("count items")}</label></div>;
  const pick = (label: string, value: string | undefined, on: (v: string | undefined) => void) =>
    <label>{label} <select aria-label={label} className="border rounded" value={value ?? ""} onChange={(e) => on(e.target.value || undefined)}><option value="">{tx("(end)")}</option>{stepIds.map((x) => <option key={x}>{x}</option>)}</select></label>;
  const others = list.filter((a) => a.id !== cur?.id && a.current_version);

  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <h2 className="text-lg font-semibold">{tx("AI agents")}</h2>
        <div className="flex items-center gap-3">
          <Link className="text-xs underline" href="/dashboard/ai/evals">{tx("AI evaluation")}</Link>
          <label className={`flex items-center gap-2 text-xs px-2 py-1 rounded border ${gov.kill_switch ? "bg-red-50 border-red-300" : ""}`}>
            <input type="checkbox" checked={!!gov.kill_switch} onChange={(e) => act(apiClient.put("/api/v1/ai-agents/settings/governance", { kill_switch: e.target.checked }), e.target.checked ? "All agents stopped." : "Agents may run again.")} />
            {tx("Emergency stop (all agents)")}</label>
        </div>
      </div>
      <p className="text-xs text-gray-500">{tx("Model:")} {gov.use_provider ? tx("configured AI provider") : tx("deterministic templates (no AI calls)")} {tx("· rates")} {String(gov.rate_input_per_1k)}/{String(gov.rate_output_per_1k)} {tx("per 1k tokens")}</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {cat && <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-2">
        {Object.entries(cat.templates).map(([k, t]) => <button key={k} className="border rounded p-2 bg-white text-left hover:bg-indigo-50" onClick={() => fromTemplate({ template: k }, t.name)}><b className="text-xs">{t.name}</b><p className="text-xs text-gray-500">{t.description}</p></button>)}
        {cat.saved_templates.map((t) => <button key={t.id} className="border border-indigo-300 rounded p-2 bg-white text-left hover:bg-indigo-50" onClick={() => fromTemplate({ saved_template: t.id }, t.name)}><b className="text-xs">{t.name}</b> <span className="text-xs text-indigo-600">{tx("(saved by")} {t.created_by})</span><p className="text-xs text-gray-500">{t.description}</p></button>)}
      </section>}

      {gates.length > 0 && <section className="border rounded p-2 bg-amber-50 space-y-1" aria-label={tx("Waiting for approval")}>
        <h3 className="font-semibold text-xs">{tx("Waiting for a person (")}{gates.length})</h3>
        {gates.map((g) => <div key={g.id} className="flex flex-wrap gap-2 items-center text-xs"><span>{g.message}</span><span className="text-gray-500">{tx("(step")} {g.step}{tx(", agent owner")} {g.requested_by})</span>
          <button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/gates/${g.id}/decide`, { approve: true }), "Approved: the run continues on the next tick.")}>{tx("Approve")}</button>
          <button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/gates/${g.id}/decide`, { approve: false }), "Denied: the run takes its denial path.")}>{tx("Deny")}</button></div>)}
      </section>}

      <details className="border rounded p-2 bg-white" open={!!usage?.reservations.some((r) => r.stuck) || !!usage?.dead_letter.length}>
        <summary className="cursor-pointer text-xs font-semibold">{tx("Budgets, reservations and recovery")}</summary>
        <div className="space-y-2 text-xs mt-2">
          <div className="flex flex-wrap gap-2 items-end">{GOV.map((k) => <label key={k}>{k.replaceAll("_", " ")}<input aria-label={k} type="number" min={0} step="any" className="border rounded px-1 block w-28" defaultValue={Number(gov[k] ?? 0)}
            onBlur={(e) => act(apiClient.put("/api/v1/ai-agents/settings/governance", { [k]: +e.target.value }), "Governance setting saved.")} /></label>)}
            <button className="border rounded px-2 py-1" onClick={() => act(apiClient.post("/api/v1/ai-agents/budget/recover"), "Recovery ran: expired reservations settled, stuck jobs queued or dead-lettered.")}>{tx("Recover stuck runs")}</button></div>
          <table className="w-full border"><thead><tr className="bg-gray-50 text-left"><th className="p-1">{tx("Scope")}</th><th>{tx("Cap / day")}</th><th>{tx("Reserved")}</th><th>{tx("Spent")}</th><th>{tx("Tokens spent")}</th></tr></thead>
            <tbody>{(usage?.counters ?? []).map((c) => <tr key={c.scope + c.id} className="border-t"><td className="p-1">{c.scope}{c.scope === "COMPANY" ? "" : ` ${c.id.slice(0, 8)}`}</td><td>{c.cap_cost}</td><td>{c.reserved_cost}</td><td>{c.spent_cost}</td><td>{c.spent_tokens}</td></tr>)}
              {!usage?.counters.length && <tr><td className="p-1 text-gray-500" colSpan={5}>{tx("No AI spend reserved today.")}</td></tr>}</tbody></table>
          {usage && usage.usage.length > 0 && <p>{tx("Measured usage:")} {usage.usage.map((u) => `${u.source}/${u.outcome}: ${u.calls} calls, ${u.tokens} tokens, ${u.cost}`).join(" · ")}</p>}
          {usage?.reservations.filter((r) => r.stuck).map((r) => <p key={r.id} className="text-red-700">{tx("Stuck reservation")} {r.id.slice(0, 8)} {tx("(worker")} {r.worker}{tx(") expired")} {new Date(r.expires_at).toLocaleString()}{tx(": use Recover.")}</p>)}
          {usage?.dead_letter.map((j) => <p key={j.id} className="flex gap-2"><span>{tx("Dead-lettered run")} {j.id.slice(0, 8)}: {j.error}</span>
            <button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/jobs/${j.id}/requeue`), "Requeued with fresh attempts.")}>{tx("Requeue")}</button></p>)}
        </div>
      </details>

      <div className="grid lg:grid-cols-[240px_1fr] gap-4">
        <aside className="space-y-1">{list.map((a) => <button key={a.id} onClick={() => open(a.id)} className={`block w-full text-left border rounded px-2 py-1 text-xs ${cur?.id === a.id ? "bg-indigo-50" : "bg-white"}`}>
          {a.name} · {a.status.toLowerCase()}{a.stopped ? tx(" · stopped") : ""}{a.current_version ? tx(" · v{current_version}", { current_version: a.current_version }) : ""}</button>)}</aside>
        {cur && def && <section className="space-y-3">
          <div className="flex flex-wrap gap-2 items-center">
            <b>{cur.name}</b>
            <select aria-label={tx("Agent status")} className="border rounded px-1 text-xs" value={cur.status} onChange={(e) => act(apiClient.patch(`/api/v1/ai-agents/${cur.id}`, { status: e.target.value }), "Status changed.")}>
              {["DRAFT", "ACTIVE", "PAUSED"].map((s) => <option key={s}>{s}</option>)}</select>
            <button className="text-xs border rounded px-2" onClick={() => act(apiClient.patch(`/api/v1/ai-agents/${cur.id}`, { stopped: !cur.stopped }), cur.stopped ? "Agent restarted." : "Agent stopped.")}>{cur.stopped ? tx("Restart agent") : tx("Stop agent")}</button>
            <span className="text-xs text-gray-500">{tx("next run")} {cur.next_run_at ? new Date(cur.next_run_at).toLocaleString() : "—"}</span>
          </div>
          <div className="flex flex-wrap gap-2 text-xs items-end">
            <label>{tx("Run daily at")}<input aria-label={tx("Daily at")} className="border rounded px-1 block w-20" placeholder="07:30" defaultValue={String(cur.schedule?.daily_at ?? "")} onBlur={(e) => e.target.value && act(apiClient.patch(`/api/v1/ai-agents/${cur.id}`, { schedule: { daily_at: e.target.value, time_zone: "Africa/Nairobi" } }), "Schedule saved (Africa/Nairobi).")} /></label>
            {(["max_runs_per_day", "max_tokens_per_run", "max_cost_per_day"] as const).map((k) => <label key={k}>{k.replaceAll("_", " ")}<input aria-label={k} type="number" min={0} className="border rounded px-1 block w-24" defaultValue={cur.budgets[k]}
              onBlur={(e) => act(apiClient.patch(`/api/v1/ai-agents/${cur.id}`, { budgets: { ...cur.budgets, [k]: +e.target.value } }), "Budget saved.")} /></label>)}
          </div>
          <div className="border rounded p-2 bg-white space-y-2">
            <div className="flex flex-wrap gap-3 items-end text-xs">
              <label>{tx("Trigger")} <select aria-label={tx("Trigger")} className="border rounded" value={def.trigger.type} onChange={(e) => setDef({ ...def, trigger: { ...def.trigger, type: e.target.value } })}>{[tx("manual"), tx("schedule"), "event"].map((t) => <option key={t}>{t}</option>)}</select></label>
              {def.trigger.type === "event" && <label>{tx("Event name")} <input aria-label={tx("Event name")} className="border rounded w-40" value={def.trigger.event ?? ""} onChange={(e) => setDef({ ...def, trigger: { ...def.trigger, event: e.target.value } })} /></label>}
              <span>{tx("Hands work to:")} {others.length ? others.map((a) => <label key={a.id} className="inline-flex items-center gap-1 mr-2"><input type="checkbox" checked={!!def.delegates?.includes(a.id)}
                onChange={(e) => setDef({ ...def, delegates: e.target.checked ? [...(def.delegates ?? []), a.id] : (def.delegates ?? []).filter((x) => x !== a.id) })} />{a.name}</label>) : <i>{tx("no other published agent")}</i>}</span>
            </div>
            <div className="text-xs">{tx("Allowed tools:")} {cat && Object.entries(cat.tools).map(([k, t]) => <label key={k} className="inline-flex items-center gap-1 mr-3">
              <input type="checkbox" checked={def.tools.includes(k)} onChange={(e) => setDef({ ...def, tools: e.target.checked ? [...def.tools, k] : def.tools.filter((x) => x !== k) })} />{k}{t.write ? tx(" (approval)") : ""}</label>)}
              <p className="text-gray-500">{tx("A delegated agent can only use tools listed here, runs as the same person, and shares the token budget (depth max")} {cat?.limits.max_delegation_depth}).</p></div>
            {def.steps.map((s, i) => <div key={i} className="border rounded p-2 space-y-1 text-xs">
              <div className="flex flex-wrap gap-2 items-center"><b>{s.id}</b>
                <select aria-label={tx("Step type")} className="border rounded" value={s.type} onChange={(e) => setStep(i, { type: e.target.value as Step["type"] })}>{(cat?.step_types ?? Object.keys(STEP_FIELDS)).map((t) => <option key={t} value={t}>{STEP_FIELDS[t as Step["type"]] ?? t}</option>)}</select>
                {s.type === "tool" && <select aria-label={tx("Tool")} className="border rounded" value={s.tool ?? ""} onChange={(e) => setStep(i, { tool: e.target.value })}>{def.tools.map((t) => <option key={t}>{t}</option>)}</select>}
                {(s.type === "tool" || s.type === "llm" || s.type === "delegate") && <label>{tx("for each")} <input aria-label={tx("For each")} className="border rounded w-14" value={s.foreach ?? ""} onChange={(e) => setStep(i, { foreach: e.target.value || undefined })} /></label>}
                {s.type !== "condition" && <label>{tx("next")} <input aria-label={tx("Next step")} className="border rounded w-14" value={s.next ?? ""} onChange={(e) => setStep(i, { next: e.target.value || undefined })} /></label>}
                {s.type !== "approval" && <label>{tx("on error go to")} <input aria-label={tx("On error")} className="border rounded w-14" value={s.on_error ?? ""} onChange={(e) => setStep(i, { on_error: e.target.value || undefined })} /></label>}
                <button className="underline text-red-700" onClick={() => setDef({ ...def, steps: def.steps.filter((_, j) => j !== i) })}>{tx("Remove")}</button>
              </div>
              {s.type === "tool" && <textarea aria-label={tx("Arguments (JSON)")} className="border rounded w-full font-mono" rows={2} defaultValue={JSON.stringify(s.args ?? {})} onBlur={(e) => { try { setStep(i, { args: JSON.parse(e.target.value) }); } catch { setMsg(tx("Arguments must be JSON.")); } }} />}
              {s.type === "llm" && <><input aria-label={tx("Prompt")} className="border rounded w-full" value={s.prompt ?? ""} onChange={(e) => setStep(i, { prompt: e.target.value })} />
                <textarea aria-label={tx("Template")} className="border rounded w-full" rows={2} value={s.template ?? ""} onChange={(e) => setStep(i, { template: e.target.value })} /></>}
              {s.type === "condition" && <div className="space-y-1">{condEditor("If", s.if, (c) => setStep(i, { if: c }))}<div className="flex gap-3">{pick("then", s.then, (v) => setStep(i, { then: v }))}{pick("else", s.else, (v) => setStep(i, { else: v }))}</div></div>}
              {s.type === "loop" && <div className="space-y-1"><div className="flex flex-wrap gap-2 items-center">
                <label>{tx("Repeat at most")} <input aria-label={tx("Max iterations")} type="number" min={1} max={cat?.limits.max_loop_iterations ?? 10} className="border rounded w-14" value={s.max_iterations ?? ""} onChange={(e) => setStep(i, { max_iterations: e.target.value ? +e.target.value : undefined })} /> {tx("times")}</label>
                <label>{tx("body steps")} <input aria-label={tx("Loop body")} className="border rounded w-28" placeholder={tx("s2,s3")} value={(s.body ?? []).join(",")} onChange={(e) => setStep(i, { body: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></label></div>
                {condEditor("Stop when", s.until, (c) => setStep(i, { until: c && c.ref ? c : undefined }))}</div>}
              {s.type === "delegate" && <div className="space-y-1"><label>{tx("Agent")} <select aria-label={tx("Delegate agent")} className="border rounded" value={s.agent ?? ""} onChange={(e) => setStep(i, { agent: e.target.value })}><option value="">{tx("(choose)")}</option>{(def.delegates ?? []).map((id) => <option key={id} value={id}>{list.find((a) => a.id === id)?.name ?? id}</option>)}</select></label>
                {jsonField("Input handed over (JSON)", s.input, (v) => setStep(i, { input: v as Record<string, unknown> }))}</div>}
              {s.type === "approval" && <div className="flex flex-wrap gap-2 items-center"><input aria-label={tx("Approval message")} className="border rounded flex-1 min-w-48" placeholder={tx("What the approver is asked")} value={s.message ?? ""} onChange={(e) => setStep(i, { message: e.target.value })} />{pick("if denied go to", s.on_deny, (v) => setStep(i, { on_deny: v }))}</div>}
            </div>)}
            <div className="grid sm:grid-cols-2 gap-2 text-xs">
              {jsonField("Input schema (JSON Schema)", def.input_schema, (v) => setDef({ ...def, input_schema: v }))}
              {jsonField("Output schema (JSON Schema)", def.output_schema, (v) => setDef({ ...def, output_schema: v }))}
            </div>
            {errors.length > 0 ? <ul role="alert" aria-label={tx("Validation errors")} className="text-xs text-red-700 border border-red-300 bg-red-50 rounded p-2 list-disc pl-5">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
              : <p className="text-xs text-green-700">{tx("Definition is valid (loops capped at")} {cat?.limits.max_loop_iterations}, {cat?.limits.max_step_executions} {tx("step executions per run).")}</p>}
            <div className="flex flex-wrap gap-2">
              <button className="border rounded px-2 py-1 text-xs" onClick={() => setDef({ ...def, steps: [...def.steps, { id: `s${def.steps.length + 1}`, type: "llm", prompt: "", template: "" }] })}>{tx("+ Step")}</button>
              <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs disabled:opacity-50" disabled={errors.length > 0} title={errors[0]} onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions`, { definition: def }), "Saved as a new draft version.")}>{tx("Save as new version")}</button>
              <input aria-label={tx("Template name")} className="border rounded px-1 text-xs" placeholder={tx("Template name")} value={tplName} onChange={(e) => setTplName(e.target.value)} />
              <button className="border rounded px-2 py-1 text-xs disabled:opacity-50" disabled={errors.length > 0 || tplName.length < 3} onClick={() => act(apiClient.post("/api/v1/ai-agents/templates", { name: tplName, definition: def }).then(loadCat), "Saved as a reusable template.")}>{tx("Save as template")}</button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 items-end text-xs">
            <label>{tx("Input (JSON)")}<input aria-label={tx("Run input")} className="border rounded px-1 block w-64 font-mono" value={input} onChange={(e) => setInput(e.target.value)} /></label>
            <button className="border rounded px-2 py-1" onClick={() => run(true)}>{tx("Simulate v")}{latest?.version}</button>
            <button className="border rounded px-2 py-1" disabled={!cur.current_version} onClick={() => run(false)}>{tx("Run published v")}{cur.current_version ?? "—"}</button>
          </div>
          <table className="text-xs w-full bg-white border"><thead><tr className="bg-gray-50 text-left"><th className="p-1">{tx("Version")}</th><th>{tx("Status")}</th><th>{tx("By")}</th><th></th></tr></thead>
            <tbody>{cur.versions.map((v) => <tr key={v.version} className="border-t"><td className="p-1">{tx("v")}{v.version}{cur.current_version === v.version ? tx(" (running)") : ""}</td><td>{v.status.toLowerCase()}</td><td>{v.created_by}{v.approved_by ? tx(" / approved {approved_by}", { approved_by: v.approved_by }) : ""}</td>
              <td className="space-x-2">{["DRAFT", "REJECTED"].includes(v.status) && <button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions/${v.version}/request`), "Sent for approval.")}>{tx("Request publish")}</button>}
                {v.status === "PENDING" && <><button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions/${v.version}/approve`), "Published.")}>{tx("Approve")}</button><button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions/${v.version}/reject`), "Rejected.")}>{tx("Reject")}</button></>}
                {v.status === "PUBLISHED" && cur.current_version !== v.version && <button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions/${v.version}/rollback`), "Rolled back.")}>{tx("Roll back to this")}</button>}
                <button className="underline" onClick={() => setDef(v.definition)}>{tx("Edit from here")}</button></td></tr>)}</tbody></table>
          <h3 className="font-semibold text-xs">{tx("Runs")}</h3>
          <ul className="text-xs space-y-1">{cur.jobs.map((j) => <li key={j.id} className="border rounded p-1 bg-white"><b>{j.trigger.toLowerCase()}</b> {tx("v")}{j.version} · {j.status.toLowerCase()} {tx("· attempt")} {j.attempts} · {j.tokens} {tx("tokens · cost")} {j.cost}{j.error ? ` · ${j.error}` : ""} · {new Date(j.created_at).toLocaleString()}
            {["QUEUED", "WAITING"].includes(j.status) && <button className="underline ml-2" onClick={() => act(apiClient.post(`/api/v1/ai-agents/jobs/${j.id}/cancel`), "Run cancelled.")}>{tx("Cancel")}</button>}
            {["DEAD", "FAILED"].includes(j.status) && <button className="underline ml-2" onClick={() => act(apiClient.post(`/api/v1/ai-agents/jobs/${j.id}/requeue`), "Requeued.")}>{tx("Retry")}</button>}
            {j.trace && <details><summary className="cursor-pointer">{tx("trace")}</summary><ul>{j.trace.map((t, i) => <li key={i} className="break-all">{t.step} ({t.tool ?? t.type}, {t.items}): {t.output}</li>)}</ul></details>}</li>)}</ul>
        </section>}
      </div>
    </div>
  );
}
