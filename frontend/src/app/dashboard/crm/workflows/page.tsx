"use client";
// Visual workflow designer (M36.S03.T004): build trigger → condition / delay / approval / action → end as a flow chart,
// validate, simulate on a real record, save versions, publish or roll back, and decide waiting approvals.
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api";
import { EntityPicker } from "@/components/EntityPicker";
import { tx } from "@/lib/i18n/core";

type NodeType = "trigger" | "condition" | "delay" | "approval" | "action" | "end";
interface WNode { id: string; type: NodeType; config?: Record<string, unknown> }
interface Edge { from: string; to: string; branch?: "yes" | "no" }
interface Graph { nodes: WNode[]; edges: Edge[] }
interface Version { id: string; version_no: number; status: string; graph: Graph; published_at: string | null }
interface Run { id: string; crm_record_id: string; status: string; log: { at?: string; node?: string; note: string }[] }
const STARTER: Graph = { nodes: [{ id: "start", type: "trigger", config: { event: "created" } }, { id: "done", type: "end" }], edges: [{ from: "start", to: "done" }] };
const EVENTS = ["created", "stage_changed", "won", "lost", "status_changed", "scheduled", "inbound_webhook", "web_event"];
const DATE_PROPS = ["expected_close_date", "next_action_date", "qualified_date", "converted_date"];
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
interface Hook { path: string; token_hint: string; rotated_at: string; last_used_at: string | null }
const FIELDS = ["temperature", "record_type", "source_type", "to_stage_code", "industry_segment", "expected_revenue", "assigned_rep_id"];
const ACTIONS = ["create_task", "notify", "set_field", "assign_owner", "enroll_in_sequence"];
// fixed colours (not theme classes) so the cards stay readable in light and dark mode
const COLORS: Record<NodeType, [string, string]> = { trigger: ["#6366f1", "#eef2ff"], condition: ["#f59e0b", "#fffbeb"], delay: ["#0ea5e9", "#f0f9ff"],
  approval: ["#d946ef", "#fdf4ff"], action: ["#10b981", "#ecfdf5"], end: ["#9ca3af", "#f9fafb"] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail; return Array.isArray(d) ? d.join(" ") : typeof d === "string" ? d : "Request failed."; };
const newId = (t: string) => `${t}-${Math.random().toString(36).slice(2, 6)}`;

function summary(n: WNode): string {
  const c = n.config ?? {};
  if (n.type === "trigger") {
    const s = (c.schedule ?? {}) as Record<string, unknown>;
    if (c.event === "scheduled") return s.kind === "relative" ? `${Math.abs(Number(s.offset_days ?? 0))} day(s) ${Number(s.offset_days ?? 0) < 0 ? "before" : "after"} ${String(s.property ?? "")} at ${s.time ?? ""}`
      : `Every ${s.kind === "weekly" ? DAYS[Number(s.weekday ?? 0)] : "day"} at ${s.time ?? ""}`;
    if (c.event === "inbound_webhook") return "When another system calls the webhook";
    if (c.event === "web_event") return `When an identified visitor sends ${String(c.name ?? "?")}`;
    return `When a CRM record is ${String(c.event ?? "").replace("_", " ")}`;
  }
  if (n.type === "condition") return `If ${c.field ?? "?"} ${c.operator ?? "eq"} ${c.value ?? ""}`;
  if (n.type === "delay") return `Wait ${c.days ?? 0} day(s)`;
  if (n.type === "approval") return `Approval: ${c.title ?? ""}`;
  if (n.type === "action") return `Do: ${String(c.action_type ?? "").replace(/_/g, " ")}`;
  return "End";
}

export default function WorkflowDesigner() {
  const [list, setList] = useState<{ id: string; name: string; trigger_event: string | null; published_version_id: string | null }[]>([]);
  const [wid, setWid] = useState<string | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [g, setG] = useState<Graph>(STARTER);
  const [sel, setSel] = useState<string | null>(null);
  const [problems, setProblems] = useState<string[]>([]);
  const [sim, setSim] = useState<{ record: string; approvals: "yes" | "no"; steps: { node: string; note: string }[] | null }>({ record: "", approvals: "yes", steps: null });
  const [name, setName] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [hook, setHook] = useState<Hook | null>(null);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [eventNames, setEventNames] = useState<string[]>([]);
  const say = (ok: boolean, text: string) => setMsg({ ok, text });

  const loadList = useCallback(() => apiClient.get("/api/v1/crm-workflows").then((r) => setList(r.data)).catch((e) => say(false, err(e))), []);
  const loadWf = useCallback((id: string) => apiClient.get(`/api/v1/crm-workflows/${id}`).then((r) => {
    setVersions(r.data.versions); setRuns(r.data.runs); setHook(r.data.webhook ?? null); if (r.data.versions[0]) setG(r.data.versions[0].graph);
  }), []);
  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => { apiClient.get("/api/v1/web-analytics/event-definitions").then((r) => setEventNames(r.data.filter((d: { active: boolean }) => d.active).map((d: { name: string }) => d.name))).catch(() => setEventNames([])); }, []);
  useEffect(() => { setNewToken(null); }, [wid]);
  useEffect(() => { if (wid) loadWf(wid); }, [wid, loadWf]);
  useEffect(() => { const t = setTimeout(() => apiClient.post("/api/v1/crm-workflows/validate", { graph: g }).then((r) => setProblems(r.data.problems)).catch(() => undefined), 300); return () => clearTimeout(t); }, [g]);

  const byId = useMemo(() => Object.fromEntries(g.nodes.map((n) => [n.id, n])), [g]);
  const next = (id: string, branch?: string) => g.edges.find((e) => e.from === id && (branch === undefined || e.branch === branch))?.to;
  const node = sel ? byId[sel] : null;
  const update = (patch: Partial<WNode>) => setG((x) => ({ ...x, nodes: x.nodes.map((n) => (n.id === sel ? { ...n, ...patch, config: { ...(n.config ?? {}), ...(patch.config ?? {}) } } : n)) }));

  // insert a step after `from` (on a branch), keeping what followed
  const insert = (from: string, type: NodeType, branch?: "yes" | "no") => setG((x) => {
    const id = newId(type);
    const old = x.edges.find((e) => e.from === from && (branch ? e.branch === branch : true));
    const after = old?.to;
    const edges = x.edges.filter((e) => e !== old);
    const cfg: Record<string, unknown> = type === "condition" ? { field: "temperature", operator: "eq", value: "HOT" } : type === "delay" ? { days: 1 }
      : type === "approval" ? { title: tx("Approve this step") } : type === "action" ? { action_type: "create_task", payload: { subject: "Follow up", due_in_days: 1 } } : {};
    const nodes = [...x.nodes, { id, type, config: cfg }];
    edges.push({ from, to: id, ...(branch ? { branch } : {}) });
    if (type === "condition" || type === "approval") {
      const endNo = newId("end"); nodes.push({ id: endNo, type: "end" });
      if (after) edges.push({ from: id, to: after, branch: "yes" }); else { const e2 = newId("end"); nodes.push({ id: e2, type: "end" }); edges.push({ from: id, to: e2, branch: "yes" }); }
      edges.push({ from: id, to: endNo, branch: "no" });
    } else if (type !== "end") {
      if (after) edges.push({ from: id, to: after }); else { const e2 = newId("end"); nodes.push({ id: e2, type: "end" }); edges.push({ from: id, to: e2 }); }
    }
    setSel(id);
    return { nodes, edges };
  });
  const remove = (id: string) => setG((x) => {
    const n = x.nodes.find((k) => k.id === id); if (!n || n.type === "trigger") return x;
    const incoming = x.edges.filter((e) => e.to === id);
    const cont = x.edges.find((e) => e.from === id && (e.branch === undefined || e.branch === "yes"))?.to;
    const drop = new Set<string>([id]);
    if (n.type === "condition" || n.type === "approval") { const no = x.edges.find((e) => e.from === id && e.branch === "no")?.to; if (no && x.nodes.find((k) => k.id === no)?.type === "end") drop.add(no); }
    const edges = x.edges.filter((e) => !drop.has(e.from) && !drop.has(e.to));
    for (const inc of incoming) if (cont) edges.push({ ...inc, to: cont });
    setSel(null);
    return { nodes: x.nodes.filter((k) => !drop.has(k.id)), edges };
  });

  function Flow({ id, depth = 0 }: { id?: string; depth?: number }) {
    if (!id || depth > 40) return null;
    const n = byId[id]; if (!n) return null;
    const branching = n.type === "condition" || n.type === "approval";
    return (
      <div className="flex flex-col items-center">
        <button onClick={() => setSel(n.id)} style={{ borderColor: COLORS[n.type][0], background: COLORS[n.type][1], color: "#111827" }}
          className={`w-56 max-w-full rounded-lg border-2 px-3 py-2 text-left text-xs ${sel === n.id ? "ring-2 ring-blue-500" : ""}`}>
          <span className="block font-semibold uppercase tracking-wide text-[10px]" style={{ color: "#4b5563" }}>{n.type}</span>{summary(n)}
        </button>
        {n.type !== "end" && !branching && (<><div className="h-4 w-px bg-gray-400" /><AddMenu onAdd={(t) => insert(n.id, t)} /><div className="h-4 w-px bg-gray-400" /><Flow id={next(n.id)} depth={depth + 1} /></>)}
        {branching && (
          <div className="flex gap-6 mt-2">{(["yes", "no"] as const).map((b) => (
            <div key={b} className="flex flex-col items-center">
              <span className={`text-[10px] font-semibold ${b === "yes" ? "text-emerald-700" : "text-red-700"}`}>{b === "yes" ? (n.type === "approval" ? tx("approved") : "yes") : (n.type === "approval" ? tx("rejected") : "no")}</span>
              <AddMenu onAdd={(t) => insert(n.id, t, b)} /><div className="h-4 w-px bg-gray-400" />
              <Flow id={next(n.id, b)} depth={depth + 1} />
            </div>))}</div>)}
      </div>
    );
  }
  const trigger = g.nodes.find((n) => n.type === "trigger");
  const cfg = (node?.config ?? {}) as Record<string, unknown>;
  const payload = (cfg.payload ?? {}) as Record<string, unknown>;

  return (
    <div className="p-4 sm:p-6 space-y-4">
      <div><h1 className="text-xl font-bold text-gray-900">{tx("Workflow designer")}</h1>
        <p className="text-xs text-gray-500">{tx("Only published versions run. Simulation changes nothing. Loops are not allowed.")}</p></div>
      {msg && <p role="status" className={`text-sm rounded px-3 py-2 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}
      <div className="flex flex-wrap gap-2 items-center">
        <select aria-label={tx("Workflow")} value={wid ?? ""} onChange={(e) => { setWid(e.target.value || null); setSel(null); }} className="border rounded px-3 py-2 text-sm">
          <option value="">{tx("Choose a workflow…")}</option>{list.map((w) => <option key={w.id} value={w.id}>{w.name}{w.published_version_id ? tx(" · live") : ""}</option>)}</select>
        <input aria-label={tx("New workflow name")} placeholder={tx("New workflow name")} value={name} onChange={(e) => setName(e.target.value)} className="border rounded px-3 py-2 text-sm" />
        <button disabled={name.trim().length < 3} onClick={async () => { try { const r = await apiClient.post("/api/v1/crm-workflows", { name }); setName(""); setG(STARTER); await loadList(); setWid(r.data.id); } catch (e) { say(false, err(e)); } }}
          className="rounded bg-blue-600 px-3 py-2 text-sm text-white disabled:opacity-50">{tx("Create")}</button>
      </div>

      {wid && (<div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="bg-white border rounded-xl p-4 overflow-x-auto"><div className="min-w-fit flex justify-center"><Flow id={trigger?.id} /></div></div>
        <div className="space-y-3">
          <div className="bg-white border rounded-xl p-3 space-y-2 text-sm">
            <p className="font-medium">{node ? tx("Step: {type}", { type: node.type }) : tx("Select a step to edit it")}</p>
            {node?.type === "trigger" && <select aria-label={tx("Trigger event")} value={String(cfg.event ?? "")} onChange={(e) => update({ config: { event: e.target.value, schedule: e.target.value === "scheduled" ? { kind: "daily", time: "08:00" } : undefined, name: undefined } })} className="w-full border rounded px-2 py-1.5">{EVENTS.map((x) => <option key={x}>{x}</option>)}</select>}
            {node?.type === "trigger" && cfg.event === "scheduled" && (() => {
              const sc = (cfg.schedule ?? {}) as Record<string, unknown>;
              const m = sc.match as Record<string, unknown> | undefined;
              const setS = (p: Record<string, unknown>) => update({ config: { schedule: { ...sc, ...p } } });
              return (<div className="space-y-1.5">
                <select aria-label={tx("Schedule kind")} value={String(sc.kind ?? "daily")} onChange={(e) => setS({ kind: e.target.value, ...(e.target.value === "weekly" ? { weekday: 0 } : {}), ...(e.target.value === "relative" ? { property: "expected_close_date", offset_days: -7 } : {}) })} className="w-full border rounded px-2 py-1.5">
                  <option value="daily">{tx("every day")}</option><option value="weekly">{tx("every week")}</option><option value="relative">{tx("relative to a date on the record")}</option></select>
                {sc.kind === "weekly" && <select aria-label={tx("Weekday")} value={Number(sc.weekday ?? 0)} onChange={(e) => setS({ weekday: Number(e.target.value) })} className="w-full border rounded px-2 py-1.5">{DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}</select>}
                {sc.kind === "relative" && (<>
                  <select aria-label={tx("Date property")} value={String(sc.property ?? "")} onChange={(e) => setS({ property: e.target.value })} className="w-full border rounded px-2 py-1.5">{DATE_PROPS.map((d) => <option key={d}>{d}</option>)}</select>
                  <label className="block text-xs">{tx("Days (negative = before the date)")}<input aria-label={tx("Offset days")} type="number" min={-365} max={365} value={Number(sc.offset_days ?? 0)} onChange={(e) => setS({ offset_days: Number(e.target.value) })} className="w-full border rounded px-2 py-1.5" /></label></>)}
                <label className="block text-xs">{tx("Time (")}{String(sc.tz ?? "Africa/Nairobi")})<input aria-label={tx("Schedule time")} type="time" value={String(sc.time ?? "08:00")} onChange={(e) => setS({ time: e.target.value })} className="w-full border rounded px-2 py-1.5" /></label>
                <p className="text-[11px] text-gray-500">{tx("Open records only; each record runs once per occurrence. Optional filter:")}</p>
                <select aria-label={tx("Schedule filter field")} value={String(m?.field ?? "")} onChange={(e) => setS({ match: e.target.value ? { field: e.target.value, operator: "eq", value: "" } : undefined })} className="w-full border rounded px-2 py-1.5"><option value="">{tx("all open records")}</option>{FIELDS.map((x) => <option key={x}>{x}</option>)}</select>
                {m && <input aria-label={tx("Schedule filter value")} placeholder={tx("equals")} value={String(m.value ?? "")} onChange={(e) => setS({ match: { ...m, value: e.target.value } })} className="w-full border rounded px-2 py-1.5" />}
              </div>);
            })()}
            {node?.type === "trigger" && cfg.event === "web_event" && <select aria-label={tx("Web event")} value={String(cfg.name ?? "")} onChange={(e) => update({ config: { name: e.target.value } })} className="w-full border rounded px-2 py-1.5">
              <option value="">{tx("Choose a defined event")}</option>{eventNames.map((x) => <option key={x}>{x}</option>)}</select>}
            {node?.type === "trigger" && cfg.event === "web_event" && eventNames.length === 0 && <p className="text-[11px] text-gray-500">{tx("Define events under Web analytics first.")}</p>}
            {node?.type === "condition" && (<>
              <select aria-label={tx("Condition field")} value={String(cfg.field ?? "")} onChange={(e) => update({ config: { field: e.target.value } })} className="w-full border rounded px-2 py-1.5">{FIELDS.map((x) => <option key={x}>{x}</option>)}</select>
              <select aria-label={tx("Operator")} value={String(cfg.operator ?? "eq")} onChange={(e) => update({ config: { operator: e.target.value } })} className="w-full border rounded px-2 py-1.5"><option value="eq">{tx("equals")}</option><option value="in">{tx("is one of (comma list)")}</option><option value="gte">{tx("at least")}</option></select>
              <input aria-label={tx("Condition value")} value={String(cfg.value ?? "")} onChange={(e) => update({ config: { value: e.target.value } })} className="w-full border rounded px-2 py-1.5" /></>)}
            {node?.type === "delay" && <input aria-label={tx("Days")} type="number" min={0} max={365} value={Number(cfg.days ?? 0)} onChange={(e) => update({ config: { days: Number(e.target.value) } })} className="w-full border rounded px-2 py-1.5" />}
            {node?.type === "approval" && <input aria-label={tx("Approval title")} value={String(cfg.title ?? "")} onChange={(e) => update({ config: { title: e.target.value } })} className="w-full border rounded px-2 py-1.5" />}
            {node?.type === "action" && (<>
              <select aria-label={tx("Action")} value={String(cfg.action_type ?? "")} onChange={(e) => update({ config: { action_type: e.target.value, payload: {} } })} className="w-full border rounded px-2 py-1.5">{ACTIONS.map((x) => <option key={x}>{x}</option>)}</select>
              {cfg.action_type === "create_task" && <input aria-label={tx("Task subject")} placeholder={tx("Task subject")} value={String(payload.subject ?? "")} onChange={(e) => update({ config: { payload: { ...payload, subject: e.target.value, due_in_days: payload.due_in_days ?? 1 } } })} className="w-full border rounded px-2 py-1.5" />}
              {cfg.action_type === "notify" && (<>
                <input aria-label={tx("Notify usernames")} placeholder={tx("usernames, comma separated")} value={((payload.usernames as string[]) ?? []).join(",")} onChange={(e) => update({ config: { payload: { ...payload, usernames: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) } } })} className="w-full border rounded px-2 py-1.5" />
                <input aria-label={tx("Notification title")} placeholder={tx("Title")} value={String(payload.title ?? "")} onChange={(e) => update({ config: { payload: { ...payload, title: e.target.value } } })} className="w-full border rounded px-2 py-1.5" /></>)}
              {cfg.action_type === "set_field" && (<>
                <select aria-label={tx("Field to set")} value={String(payload.field ?? "temperature")} onChange={(e) => update({ config: { payload: { ...payload, field: e.target.value } } })} className="w-full border rounded px-2 py-1.5"><option>temperature</option><option>next_action_days</option><option>probability_pct</option></select>
                <input aria-label={tx("Value")} value={String(payload.value ?? "")} onChange={(e) => update({ config: { payload: { ...payload, value: payload.field === "temperature" || !payload.field ? e.target.value : Number(e.target.value) } } })} className="w-full border rounded px-2 py-1.5" /></>)}
              {cfg.action_type === "enroll_in_sequence" && <input aria-label={tx("Sequence id")} placeholder={tx("Sequence id")} value={String(payload.sequence_id ?? "")} onChange={(e) => update({ config: { payload: { sequence_id: e.target.value } } })} className="w-full border rounded px-2 py-1.5" />}
              {cfg.action_type === "assign_owner" && <input aria-label={tx("Rep ids")} placeholder={tx("rep ids, comma separated")} value={((payload.rep_ids as string[]) ?? []).join(",")} onChange={(e) => update({ config: { payload: { rep_ids: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) } } })} className="w-full border rounded px-2 py-1.5" />}
            </>)}
            {node && node.type !== "trigger" && node.type !== "end" && <button onClick={() => remove(node.id)} className="text-xs text-red-700">{tx("Remove step")}</button>}
          </div>

          <div className={`rounded-xl border p-3 text-xs ${problems.length ? "bg-red-50 border-red-200 text-red-700" : "bg-emerald-50 border-emerald-200 text-emerald-800"}`}>
            {problems.length ? <ul className="list-disc pl-4">{problems.map((p) => <li key={p}>{p}</li>)}</ul> : tx("The workflow is valid.")}</div>

          <div className="bg-white border rounded-xl p-3 space-y-2 text-sm">
            <p className="font-medium">{tx("Simulate on a record")}</p>
            <EntityPicker kind="crm_record" label={tx("CRM record")} value={sim.record} onChange={(id) => setSim({ ...sim, record: id, steps: null })} />
            <select aria-label={tx("Simulated approval")} value={sim.approvals} onChange={(e) => setSim({ ...sim, approvals: e.target.value as "yes" | "no" })} className="w-full border rounded px-2 py-1.5"><option value="yes">{tx("approvals: approved")}</option><option value="no">{tx("approvals: rejected")}</option></select>
            <button disabled={!sim.record || problems.length > 0} onClick={async () => { try { const r = await apiClient.post("/api/v1/crm-workflows/simulate", { graph: g, crm_record_id: sim.record, approvals: sim.approvals }); setSim({ ...sim, steps: r.data.steps }); } catch (e) { say(false, err(e)); } }}
              className="w-full rounded border py-1.5 disabled:opacity-50">{tx("Simulate")}</button>
            {sim.steps && <ol className="list-decimal pl-5 text-xs">{sim.steps.map((s, i) => <li key={i}>{s.note}</li>)}</ol>}
          </div>

          <div className="bg-white border rounded-xl p-3 space-y-2 text-sm">
            <button onClick={async () => { try { const r = await apiClient.post(`/api/v1/crm-workflows/${wid}/versions`, { graph: g }); say(r.data.problems.length === 0, `Saved as version ${r.data.version_no}${r.data.problems.length ? " (has problems — cannot be published)" : ""}.`); loadWf(wid); } catch (e) { say(false, err(e)); } }}
              className="w-full rounded bg-blue-600 text-white py-1.5">{tx("Save as new version")}</button>
            <ul className="divide-y text-xs">{versions.map((v) => (
              <li key={v.id} className="py-1.5 flex items-center justify-between gap-2">
                <button onClick={() => setG(v.graph)} className="text-left underline">{tx("v")}{v.version_no}</button>
                <span className={v.status === "PUBLISHED" ? "text-emerald-700 font-semibold" : "text-gray-500"}>{v.status.toLowerCase()}</span>
                {v.status !== "PUBLISHED" && <button onClick={async () => { try { await apiClient.post(`/api/v1/crm-workflows/versions/${v.id}/publish`); say(true, `Version ${v.version_no} is live.`); loadWf(wid); loadList(); } catch (e) { say(false, err(e)); } }}
                  className="rounded border px-2 py-0.5">{v.status === "ARCHIVED" ? tx("Roll back to this") : tx("Publish")}</button>}
              </li>))}</ul>
          </div>

          {trigger?.config?.event === "inbound_webhook" && <div className="bg-white border rounded-xl p-3 space-y-2 text-xs">
            <p className="font-medium text-sm">{tx("Inbound webhook")}</p>
            <p className="text-gray-500">{tx("POST JSON with event_id and record_id or email, header Authorization: Bearer token. The same event id enrols once. Approvers only; the live version must use this trigger.")}</p>
            {hook ? <p>{tx("Path")} <code className="break-all">{hook.path}</code> {tx("· token ending")} {hook.token_hint} · {hook.last_used_at ? `last used ${new Date(hook.last_used_at).toLocaleString()}` : tx("not used yet")}</p> : <p className="text-gray-500">{tx("No token yet.")}</p>}
            {newToken && <p role="status" className="rounded bg-amber-50 p-2 text-amber-900">{tx("Copy this token now; it is not shown again:")} <code className="break-all select-all">{newToken}</code></p>}
            <div className="flex gap-2">
              <button onClick={async () => { try { const r = await apiClient.post(`/api/v1/crm-workflows/${wid}/webhook-token`); setNewToken(r.data.token); loadWf(wid); } catch (e) { say(false, err(e)); } }} className="rounded border px-2 py-1">{hook ? tx("Rotate token") : tx("Create token")}</button>
              {hook && <button onClick={async () => { try { await apiClient.delete(`/api/v1/crm-workflows/${wid}/webhook-token`); setNewToken(null); loadWf(wid); } catch (e) { say(false, err(e)); } }} className="rounded border px-2 py-1 text-red-700">{tx("Revoke")}</button>}
            </div>
          </div>}

          {runs.length > 0 && <div className="bg-white border rounded-xl p-3 space-y-2 text-xs">
            <p className="font-medium text-sm">{tx("Recent runs")}</p>
            {runs.map((r) => <div key={r.id} className="border-t pt-1"><span className="font-medium">{r.status.replace("_", " ").toLowerCase()}</span> · {r.log.slice(-1)[0]?.note ?? ""}
              {r.status === "WAITING_APPROVAL" && <span className="ml-2"><button onClick={async () => { try { await apiClient.post(`/api/v1/crm-workflows/runs/${r.id}/decision`, { approve: true }); loadWf(wid); } catch (e) { say(false, err(e)); } }} className="text-emerald-700 underline">{tx("approve")}</button>
                <button onClick={async () => { try { await apiClient.post(`/api/v1/crm-workflows/runs/${r.id}/decision`, { approve: false }); loadWf(wid); } catch (e) { say(false, err(e)); } }} className="ml-2 text-red-700 underline">{tx("reject")}</button></span>}</div>)}
          </div>}
        </div>
      </div>)}
    </div>
  );
}

function AddMenu({ onAdd }: { onAdd: (t: NodeType) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} aria-label={tx("Add a step here")} className="h-6 w-6 rounded-full border bg-white text-xs text-gray-600 hover:bg-gray-100">+</button>
      {open && <div className="absolute z-10 left-1/2 -translate-x-1/2 mt-1 w-36 rounded border bg-white shadow text-xs">
        {(["condition", "delay", "approval", "action"] as NodeType[]).map((t) => <button key={t} onClick={() => { onAdd(t); setOpen(false); }} className="block w-full text-left px-3 py-1.5 hover:bg-gray-50">{t}</button>)}</div>}
    </div>
  );
}
