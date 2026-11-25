"use client";
// M45.S01.T008/T009 AI agent builder: template gallery, step editor, simulation, versions (second-person publish,
// rollback), schedule, budgets, per-agent and global emergency stop, job history with traces.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Step = { id: string; type: "tool" | "llm"; tool?: string; args?: Record<string, unknown>; prompt?: string; template?: string; foreach?: string; next?: string };
type Def = { trigger: { type: string; event?: string }; tools: string[]; knowledge?: Record<string, unknown>; steps: Step[] };
type Agent = { id: string; name: string; template: string | null; status: string; stopped: boolean; current_version: number | null; schedule: Record<string, unknown> | null; budgets: Record<string, number>; next_run_at: string | null; last_run_at: string | null };
type Job = { id: string; version: number; trigger: string; status: string; tokens: number; cost: string; error: string | null; trace: { step: string; type: string; tool: string | null; items: number; output: string }[] | null; created_at: string };
type Detail = Agent & { versions: { version: number; status: string; definition: Def; created_by: string; approved_by: string | null }[]; jobs: Job[] };
type Catalog = { tools: Record<string, { label: string; write: boolean }>; templates: Record<string, { name: string; description: string; definition: Def }> };

const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export default function AgentsPage() {
  const [cat, setCat] = useState<Catalog | null>(null);
  const [list, setList] = useState<Agent[]>([]);
  const [gov, setGov] = useState<Record<string, number | boolean>>({});
  const [cur, setCur] = useState<Detail | null>(null);
  const [def, setDef] = useState<Def | null>(null);
  const [input, setInput] = useState("{}");
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => {
    apiClient.get("/api/v1/ai-agents").then((r) => { setList(r.data.agents); setGov(r.data.settings); }).catch((e) => setMsg(err(e)));
  }, []);
  useEffect(() => { load(); apiClient.get("/api/v1/ai-agents/catalog").then((r) => setCat(r.data)).catch(() => setCat(null)); }, [load]);
  const open = (id: string) => apiClient.get(`/api/v1/ai-agents/${id}`).then((r) => { setCur(r.data); setDef(r.data.versions[0]?.definition ?? null); }).catch((e) => setMsg(err(e)));
  const act = (p: Promise<unknown>, ok: string) => p.then(() => { setMsg(ok); load(); if (cur) open(cur.id); }).catch((e) => setMsg(err(e)));
  const fromTemplate = (key: string) => apiClient.post("/api/v1/ai-agents", { name: cat!.templates[key].name, template: key }).then((r) => { load(); open(r.data.id); setMsg("Agent created as draft v1."); }).catch((e) => setMsg(err(e)));
  const setStep = (i: number, patch: Partial<Step>) => def && setDef({ ...def, steps: def.steps.map((s, j) => (j === i ? { ...s, ...patch } : s)) });
  const latest = cur?.versions[0];
  const run = (simulate: boolean) => {
    let parsed: unknown; try { parsed = JSON.parse(input || "{}"); } catch { return setMsg("Input must be JSON."); }
    act(apiClient.post(`/api/v1/ai-agents/${cur!.id}/run`, { simulate, version: simulate ? latest?.version : undefined, input: parsed }), simulate ? "Simulated (nothing was written)." : "Run finished.");
  };

  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <h2 className="text-lg font-semibold">AI agents</h2>
        <label className={`flex items-center gap-2 text-xs px-2 py-1 rounded border ${gov.kill_switch ? "bg-red-50 border-red-300" : ""}`}>
          <input type="checkbox" checked={!!gov.kill_switch} onChange={(e) => act(apiClient.put("/api/v1/ai-agents/settings/governance", { kill_switch: e.target.checked }), e.target.checked ? "All agents stopped." : "Agents may run again.")} />
          Emergency stop (all agents)</label>
      </div>
      <p className="text-xs text-gray-500">Model: {gov.use_provider ? "configured AI provider" : "deterministic templates (no AI calls)"} · rates {String(gov.rate_input_per_1k)}/{String(gov.rate_output_per_1k)} per 1k tokens · company budget {String(gov.company_cost_per_day)}/day</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {cat && <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-2">{Object.entries(cat.templates).map(([k, t]) =>
        <button key={k} className="border rounded p-2 bg-white text-left hover:bg-indigo-50" onClick={() => fromTemplate(k)}><b className="text-xs">{t.name}</b><p className="text-xs text-gray-500">{t.description}</p></button>)}</section>}
      <div className="grid lg:grid-cols-[240px_1fr] gap-4">
        <aside className="space-y-1">{list.map((a) => <button key={a.id} onClick={() => open(a.id)} className={`block w-full text-left border rounded px-2 py-1 text-xs ${cur?.id === a.id ? "bg-indigo-50" : "bg-white"}`}>
          {a.name} · {a.status.toLowerCase()}{a.stopped ? " · stopped" : ""}{a.current_version ? ` · v${a.current_version}` : ""}</button>)}</aside>
        {cur && def && <section className="space-y-3">
          <div className="flex flex-wrap gap-2 items-center">
            <b>{cur.name}</b>
            <select aria-label="Agent status" className="border rounded px-1 text-xs" value={cur.status} onChange={(e) => act(apiClient.patch(`/api/v1/ai-agents/${cur.id}`, { status: e.target.value }), "Status changed.")}>
              {["DRAFT", "ACTIVE", "PAUSED"].map((s) => <option key={s}>{s}</option>)}</select>
            <button className="text-xs border rounded px-2" onClick={() => act(apiClient.patch(`/api/v1/ai-agents/${cur.id}`, { stopped: !cur.stopped }), cur.stopped ? "Agent restarted." : "Agent stopped.")}>{cur.stopped ? "Restart agent" : "Stop agent"}</button>
            <span className="text-xs text-gray-500">next run {cur.next_run_at ? new Date(cur.next_run_at).toLocaleString() : "—"}</span>
          </div>
          <div className="flex flex-wrap gap-2 text-xs items-end">
            <label>Run daily at<input aria-label="Daily at" className="border rounded px-1 block w-20" placeholder="07:30" defaultValue={String(cur.schedule?.daily_at ?? "")} onBlur={(e) => e.target.value && act(apiClient.patch(`/api/v1/ai-agents/${cur.id}`, { schedule: { daily_at: e.target.value, time_zone: "Africa/Nairobi" } }), "Schedule saved (Africa/Nairobi).")} /></label>
            {(["max_runs_per_day", "max_tokens_per_run", "max_cost_per_day"] as const).map((k) => <label key={k}>{k.replaceAll("_", " ")}<input aria-label={k} type="number" min={0} className="border rounded px-1 block w-24" defaultValue={cur.budgets[k]}
              onBlur={(e) => act(apiClient.patch(`/api/v1/ai-agents/${cur.id}`, { budgets: { ...cur.budgets, [k]: +e.target.value } }), "Budget saved.")} /></label>)}
          </div>
          <div className="border rounded p-2 bg-white space-y-2">
            <div className="text-xs">Allowed tools: {cat && Object.entries(cat.tools).map(([k, t]) => <label key={k} className="inline-flex items-center gap-1 mr-3">
              <input type="checkbox" checked={def.tools.includes(k)} onChange={(e) => setDef({ ...def, tools: e.target.checked ? [...def.tools, k] : def.tools.filter((x) => x !== k) })} />{k}{t.write ? " (approval)" : ""}</label>)}</div>
            {def.steps.map((s, i) => <div key={i} className="border rounded p-2 space-y-1 text-xs">
              <div className="flex flex-wrap gap-2 items-center"><b>{s.id}</b>
                <select aria-label="Step type" className="border rounded" value={s.type} onChange={(e) => setStep(i, { type: e.target.value as Step["type"] })}><option value="tool">tool</option><option value="llm">llm</option></select>
                {s.type === "tool" && <select aria-label="Tool" className="border rounded" value={s.tool ?? ""} onChange={(e) => setStep(i, { tool: e.target.value })}>{def.tools.map((t) => <option key={t}>{t}</option>)}</select>}
                <label>for each <input aria-label="For each" className="border rounded w-14" value={s.foreach ?? ""} onChange={(e) => setStep(i, { foreach: e.target.value || undefined })} /></label>
                <label>next <input aria-label="Next step" className="border rounded w-14" value={s.next ?? ""} onChange={(e) => setStep(i, { next: e.target.value || undefined })} /></label>
              </div>
              {s.type === "tool" ? <textarea aria-label="Arguments (JSON)" className="border rounded w-full font-mono" rows={2} defaultValue={JSON.stringify(s.args ?? {})} onBlur={(e) => { try { setStep(i, { args: JSON.parse(e.target.value) }); } catch { setMsg("Arguments must be JSON."); } }} />
                : <><input aria-label="Prompt" className="border rounded w-full" value={s.prompt ?? ""} onChange={(e) => setStep(i, { prompt: e.target.value })} />
                  <textarea aria-label="Template" className="border rounded w-full" rows={2} value={s.template ?? ""} onChange={(e) => setStep(i, { template: e.target.value })} /></>}
            </div>)}
            <div className="flex flex-wrap gap-2">
              <button className="border rounded px-2 py-1 text-xs" onClick={() => setDef({ ...def, steps: [...def.steps, { id: `s${def.steps.length + 1}`, type: "llm", prompt: "", template: "" }] })}>+ Step</button>
              <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions`, { definition: def }), "Saved as a new draft version.")}>Save as new version</button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 items-end text-xs">
            <label>Input (JSON)<input aria-label="Run input" className="border rounded px-1 block w-64 font-mono" value={input} onChange={(e) => setInput(e.target.value)} /></label>
            <button className="border rounded px-2 py-1" onClick={() => run(true)}>Simulate v{latest?.version}</button>
            <button className="border rounded px-2 py-1" disabled={!cur.current_version} onClick={() => run(false)}>Run published v{cur.current_version ?? "—"}</button>
          </div>
          <table className="text-xs w-full bg-white border"><thead><tr className="bg-gray-50 text-left"><th className="p-1">Version</th><th>Status</th><th>By</th><th></th></tr></thead>
            <tbody>{cur.versions.map((v) => <tr key={v.version} className="border-t"><td className="p-1">v{v.version}{cur.current_version === v.version ? " (running)" : ""}</td><td>{v.status.toLowerCase()}</td><td>{v.created_by}{v.approved_by ? ` / approved ${v.approved_by}` : ""}</td>
              <td className="space-x-2">{["DRAFT", "REJECTED"].includes(v.status) && <button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions/${v.version}/request`), "Sent for approval.")}>Request publish</button>}
                {v.status === "PENDING" && <><button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions/${v.version}/approve`), "Published.")}>Approve</button><button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions/${v.version}/reject`), "Rejected.")}>Reject</button></>}
                {v.status === "PUBLISHED" && cur.current_version !== v.version && <button className="underline" onClick={() => act(apiClient.post(`/api/v1/ai-agents/${cur.id}/versions/${v.version}/rollback`), "Rolled back.")}>Roll back to this</button>}
                <button className="underline" onClick={() => setDef(v.definition)}>Edit from here</button></td></tr>)}</tbody></table>
          <h3 className="font-semibold text-xs">Runs</h3>
          <ul className="text-xs space-y-1">{cur.jobs.map((j) => <li key={j.id} className="border rounded p-1 bg-white"><b>{j.trigger.toLowerCase()}</b> v{j.version} · {j.status.toLowerCase()} · {j.tokens} tokens · cost {j.cost}{j.error ? ` · ${j.error}` : ""} · {new Date(j.created_at).toLocaleString()}
            {j.trace && <details><summary className="cursor-pointer">trace</summary><ul>{j.trace.map((t, i) => <li key={i} className="break-all">{t.step} ({t.tool ?? t.type}, {t.items}): {t.output}</li>)}</ul></details>}</li>)}</ul>
        </section>}
      </div>
    </div>
  );
}
