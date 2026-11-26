"use client";
// M45.S01.T019 service desk setup and insight: CSAT/CES/post-chat results, SLA met, business hours, agents (skills,
// capacity, presence), SLA policies, macros, and a ticket panel (SLA timers, hand-off summary, suggested articles).
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Ov = { report: Record<string, { sent?: number; answered?: number; average?: number | null; tickets?: number; breached?: number; met_pct?: number | null }>;
  settings: { time_zone: string; weekdays: number[]; open: string; close: string; holidays: string[]; category_skills: Record<string, string> };
  agents: { user_id: string; skills: string[]; capacity: number; presence: string }[];
  policies: { id: string; name: string; priority: string | null; channel: string | null; customer_tier: number | null; first_response_hours: number; resolution_hours: number; business_hours: boolean }[];
  macros: { id: string; name: string; body: string }[] };
type Panel = { sla: { first_response_due: string; resolution_due: string; paused: boolean; breached_first: boolean; breached_resolution: boolean } | null; handoff: string; recommendations: { title: string; summary: string; link: string }[] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : tx("Something went wrong."); };
const inp = "border rounded px-2 py-1 text-xs";

export default function ServiceDeskPage() {
  const [o, setO] = useState<Ov | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [pol, setPol] = useState({ name: "", priority: "", channel: "", customer_tier: "", first_response_hours: "2", resolution_hours: "24", business_hours: true });
  const [agent, setAgent] = useState({ user_id: "", skills: "", capacity: "10" });
  const [macro, setMacro] = useState({ name: "", body: "" });
  const [tid, setTid] = useState("");
  const [panel, setPanel] = useState<Panel | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/service-desk/overview").then((r) => setO(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const act = (p: Promise<unknown>, ok: string) => p.then(() => { setMsg(ok); load(); }).catch((e) => setMsg(err(e)));
  if (!o) return <p className="p-4 text-sm">{msg ?? tx("Loading…")}</p>;
  const r = o.report;
  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap justify-between gap-2"><h2 className="text-lg font-semibold">{tx("Service desk")}</h2>
        <select aria-label={tx("My presence")} className={inp} defaultValue="" onChange={(e) => e.target.value && act(apiClient.put("/api/v1/service-desk/me/presence", { presence: e.target.value }), tx("Presence updated."))}>
          <option value="">{tx("My presence…")}</option><option>AVAILABLE</option><option>AWAY</option><option>OFFLINE</option></select></div>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">{(["CSAT", "CES", "POST_CHAT"] as const).map((k) => <div key={k} className="border rounded p-2 bg-white">
        <div className="text-xs text-gray-500">{k.replace("_", "-").toLowerCase()} {tx("(30 days)")}</div><div className="text-xl font-semibold">{r[k]?.average ?? "—"}</div>
        <div className="text-xs text-gray-500">{r[k]?.answered}/{r[k]?.sent} {tx("answered")}</div></div>)}
        <div className="border rounded p-2 bg-white"><div className="text-xs text-gray-500">{tx("SLA met")}</div><div className="text-xl font-semibold">{r.sla?.met_pct ?? "—"}%</div><div className="text-xs text-gray-500">{r.sla?.breached} {tx("of")} {r.sla?.tickets} {tx("breached")}</div></div></div>
      <section className="border rounded p-3 bg-white space-y-1 text-xs"><h3 className="font-semibold text-sm">{tx("Business hours")}</h3>
        <p>{o.settings.time_zone} {tx("· days")} {o.settings.weekdays.map((d) => ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d]).join(", ")} · {o.settings.open}–{o.settings.close}{o.settings.holidays.length ? tx(" · holidays {holidays}", { holidays: o.settings.holidays.join(", ") }) : ""}</p>
        <p>{tx("Skill routing:")} {Object.entries(o.settings.category_skills).map(([c, s]) => `${c.toLowerCase()} → ${s}`).join(", ")}</p></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">{tx("Agents")}</h3>
        <ul className="text-xs">{o.agents.map((a) => <li key={a.user_id}>{a.user_id.slice(0, 8)} · {a.presence.toLowerCase()} {tx("· skills")} {a.skills.join(", ") || "—"} {tx("· up to")} {a.capacity} {tx("open")}</li>)}</ul>
        <div className="flex flex-wrap gap-2"><input aria-label={tx("Agent user id")} className={inp} placeholder={tx("user id")} value={agent.user_id} onChange={(e) => setAgent({ ...agent, user_id: e.target.value })} />
          <input aria-label={tx("Agent skills")} className={inp} placeholder={tx("skills, comma separated")} value={agent.skills} onChange={(e) => setAgent({ ...agent, skills: e.target.value })} />
          <input aria-label={tx("Agent capacity")} className={`${inp} w-16`} value={agent.capacity} onChange={(e) => setAgent({ ...agent, capacity: e.target.value })} />
          <button className="border rounded px-2 text-xs" onClick={() => act(apiClient.put(`/api/v1/service-desk/agents/${agent.user_id}`, { skills: agent.skills.split(","), capacity: +agent.capacity }), tx("Agent saved."))}>{tx("Save agent")}</button></div></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">{tx("SLA policies (first match wins)")}</h3>
        <ul className="text-xs">{o.policies.map((p) => <li key={p.id}>{p.name}: {p.priority ?? tx("any priority")} · {p.channel ?? tx("any channel")} · {p.customer_tier ? tx("tier {customer_tier}", { customer_tier: p.customer_tier }) : tx("any customer")} {tx("→ respond")} {p.first_response_hours} {tx("h, resolve")} {p.resolution_hours} {tx("h")}{p.business_hours ? tx(" (business hours)") : tx(" (clock)")}</li>)}</ul>
        <div className="flex flex-wrap gap-2 items-center text-xs">{(["name", "first_response_hours", "resolution_hours"] as const).map((k) => <input key={k} aria-label={k} className={`${inp} w-28`} placeholder={k.replaceAll("_", " ")} value={pol[k]} onChange={(e) => setPol({ ...pol, [k]: e.target.value })} />)}
          <select aria-label={tx("Priority")} className={inp} value={pol.priority} onChange={(e) => setPol({ ...pol, priority: e.target.value })}><option value="">{tx("any priority")}</option>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((x) => <option key={x}>{x}</option>)}</select>
          <select aria-label={tx("Channel")} className={inp} value={pol.channel} onChange={(e) => setPol({ ...pol, channel: e.target.value })}><option value="">{tx("any channel")}</option>{["PHONE", "EMAIL", "PORTAL", "WHATSAPP", "MANUAL"].map((x) => <option key={x}>{x}</option>)}</select>
          <select aria-label={tx("Customer tier")} className={inp} value={pol.customer_tier} onChange={(e) => setPol({ ...pol, customer_tier: e.target.value })}><option value="">{tx("any customer")}</option><option value="1">{tx("tier 1")}</option><option value="2">{tx("tier 2")}</option><option value="3">{tx("tier 3")}</option></select>
          <label><input type="checkbox" checked={pol.business_hours} onChange={(e) => setPol({ ...pol, business_hours: e.target.checked })} /> {tx("business hours")}</label>
          <button className="border rounded px-2" onClick={() => act(apiClient.post("/api/v1/service-desk/policies", { ...pol, priority: pol.priority || null, channel: pol.channel || null, customer_tier: pol.customer_tier ? +pol.customer_tier : null, first_response_hours: +pol.first_response_hours, resolution_hours: +pol.resolution_hours }), tx("Policy added."))}>{tx("Add policy")}</button></div></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">{tx("Macros")}</h3>
        <ul className="text-xs">{o.macros.map((m) => <li key={m.id}><b>{m.name}</b>: {m.body.slice(0, 80)}</li>)}</ul>
        <div className="flex flex-wrap gap-2"><input aria-label={tx("Macro name")} className={inp} placeholder={tx("name")} value={macro.name} onChange={(e) => setMacro({ ...macro, name: e.target.value })} />
          <input aria-label={tx("Macro text")} className={`${inp} flex-1`} placeholder={tx("reply text ({ticket_no} allowed)")} value={macro.body} onChange={(e) => setMacro({ ...macro, body: e.target.value })} />
          <button className="border rounded px-2 text-xs" onClick={() => act(apiClient.post("/api/v1/service-desk/macros", macro), tx("Macro added."))}>{tx("Add")}</button></div></section>
      <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold">{tx("Ticket panel")}</h3>
        <div className="flex gap-2"><input aria-label={tx("Ticket id")} className={`${inp} w-80`} placeholder={tx("ticket id")} value={tid} onChange={(e) => setTid(e.target.value)} />
          <button className="border rounded px-2 text-xs" onClick={() => apiClient.get(`/api/v1/service-desk/tickets/${tid}`).then((r) => setPanel(r.data)).catch((e) => setMsg(err(e)))}>{tx("Open")}</button>
          {panel && <><button className="border rounded px-2 text-xs" onClick={() => act(apiClient.post(`/api/v1/service-desk/tickets/${tid}/${panel.sla?.paused ? "resume" : "pause"}`), panel.sla?.paused ? tx("SLA resumed.") : tx("Waiting for customer: SLA paused."))}>{panel.sla?.paused ? tx("Resume SLA") : tx("Waiting for customer")}</button>
            {o.macros.map((m) => <button key={m.id} className="border rounded px-2 text-xs" onClick={() => act(apiClient.post(`/api/v1/service-desk/tickets/${tid}/macro/${m.id}`), tx("Macro applied."))}>{m.name}</button>)}</>}</div>
        {panel && <div className="text-xs space-y-1"><pre className="whitespace-pre-wrap bg-gray-50 p-2 rounded">{panel.handoff}</pre>
          {panel.recommendations.length > 0 && <div><b>{tx("Suggested articles")}</b>{panel.recommendations.map((x) => <div key={x.link}>{x.title} ({x.link})</div>)}</div>}</div>}</section>
    </div>
  );
}
