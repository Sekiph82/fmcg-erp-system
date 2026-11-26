"use client";
// M44.S01.T009 first-party website analytics: consented visitors only, bots dropped, no IP or raw ids stored.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import EventTags from "@/components/EventTags";
import { tx } from "@/lib/i18n/core";

interface Summary { visitors: number; sessions: number; page_views: number; identified_visitors: number; note: string;
  top_pages: [string, number][]; sources: [string, number][]; events: [string, number][] }
interface Step { step: string; visitors: number; of_previous: number | null }
interface Journey { linked: boolean; first_touch: { source: string; medium: string | null; campaign: string | null; at: string } | null;
  events: { at: string; kind: string; name: string | null; path: string }[] }

interface EventDef { id: string; name: string; description: string | null; properties: Record<string, string>; active: boolean }
const parseProps = (t: string) => Object.fromEntries(t.split(",").map((x) => x.trim()).filter(Boolean).map((x) => { const [k, v] = x.split(":").map((y) => y.trim()); return [k, v || "string"]; }));
const err = (e: unknown) => ((e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail as string) || "Request failed.";

function List({ title, rows }: { title: string; rows: [string, number][] }) {
  return (
    <div className="border rounded p-3 bg-white">
      <h3 className="font-semibold text-sm mb-1">{title}</h3>
      {rows.length === 0 ? <p className="text-xs text-gray-500">{tx("No data yet.")}</p> :
        <ul className="text-xs space-y-0.5">{rows.map(([k, n]) => <li key={k} className="flex justify-between gap-2"><span className="truncate">{k}</span><b>{n}</b></li>)}</ul>}
    </div>
  );
}

export default function WebAnalyticsPage() {
  const [days, setDays] = useState(30);
  const [sum, setSum] = useState<Summary | null>(null);
  const [steps, setSteps] = useState("/, /products, FORM:contact");
  const [funnel, setFunnel] = useState<Step[] | null>(null);
  const [email, setEmail] = useState("");
  const [journey, setJourney] = useState<Journey | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [defs, setDefs] = useState<EventDef[]>([]);
  const [edit, setEdit] = useState<{ id?: string; name: string; description: string; props: string; active: boolean }>({ name: "", description: "", props: "", active: true });
  const loadDefs = useCallback(() => apiClient.get("/api/v1/web-analytics/event-definitions").then((r) => setDefs(r.data)).catch(() => setDefs([])), []);
  useEffect(() => { loadDefs(); }, [loadDefs]);
  const saveDef = async () => {
    setMsg(null);
    const body = { name: edit.name, description: edit.description || null, properties: parseProps(edit.props), active: edit.active };
    try { await (edit.id ? apiClient.put(`/api/v1/web-analytics/event-definitions/${edit.id}`, body) : apiClient.post("/api/v1/web-analytics/event-definitions", body));
      setEdit({ name: "", description: "", props: "", active: true }); loadDefs(); } catch (x) { setMsg(err(x)); }
  };
  useEffect(() => { setSum(null); apiClient.get(`/api/v1/web-analytics/summary?days=${days}`).then((r) => setSum(r.data)).catch((e) => setMsg(err(e))); }, [days]);
  const api = typeof window !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL || window.location.origin) : "";
  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{tx("Website analytics")}</h2>
        <select aria-label={tx("Period")} className="border rounded px-2 py-1" value={days} onChange={(e) => setDays(+e.target.value)}>
          {[7, 30, 90, 365].map((d) => <option key={d} value={d}>{tx("Last")} {d} {tx("days")}</option>)}</select>
      </div>
      {msg && <p role="alert" className="text-red-600 text-xs">{msg}</p>}
      {!sum ? <p className="text-gray-500">{tx("Loading…")}</p> : <>
        <p className="text-xs text-gray-500">{sum.note}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {([["Visitors", sum.visitors], ["Sessions", sum.sessions], ["Page views", sum.page_views], ["Identified (consented)", sum.identified_visitors]] as const).map(([k, v]) =>
            <div key={k} className="border rounded p-3 bg-white"><div className="text-xs text-gray-500">{k}</div><div className="text-xl font-semibold">{v}</div></div>)}
        </div>
        <div className="grid md:grid-cols-3 gap-2"><List title={tx("Top pages")} rows={sum.top_pages} /><List title={tx("First-touch sources")} rows={sum.sources} /><List title={tx("Events")} rows={sum.events} /></div>
      </>}
      <form className="border rounded p-3 bg-white space-y-2" onSubmit={(e) => { e.preventDefault(); setMsg(null);
        apiClient.get("/api/v1/web-analytics/funnel", { params: { steps, days } }).then((r) => setFunnel(r.data)).catch((x) => setMsg(err(x))); }}>
        <h3 className="font-semibold">{tx("Funnel")}</h3>
        <div className="flex flex-wrap gap-2"><input aria-label={tx("Funnel steps")} className="border rounded px-2 py-1 flex-1 min-w-0" value={steps} onChange={(e) => setSteps(e.target.value)} />
          <button className="border rounded px-3 py-1">{tx("Show")}</button></div>
        <p className="text-xs text-gray-500">{tx("Comma-separated, in order: page paths (/pricing) or events (CTA:demo, FORM:contact).")}</p>
        {funnel && <ol className="text-xs space-y-1">{funnel.map((s) => <li key={s.step}><b>{s.step}</b>: {s.visitors} {tx("visitors")}{s.of_previous != null ? ` (${Math.round(s.of_previous * 100)}% of previous)` : ""}</li>)}</ol>}
      </form>
      <form className="border rounded p-3 bg-white space-y-2" onSubmit={(e) => { e.preventDefault(); setMsg(null);
        apiClient.get("/api/v1/web-analytics/journey", { params: { email } }).then((r) => setJourney(r.data)).catch((x) => setMsg(err(x))); }}>
        <h3 className="font-semibold">{tx("Contact journey")}</h3>
        <div className="flex flex-wrap gap-2"><input aria-label={tx("Contact e-mail")} type="email" required className="border rounded px-2 py-1 flex-1 min-w-0" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className="border rounded px-3 py-1">{tx("Show")}</button></div>
        {journey && (!journey.linked ? <p className="text-xs text-gray-500">{tx("No website visits linked to this address (links exist only after the visitor gave marketing consent).")}</p> : <>
          {journey.first_touch && <p className="text-xs">{tx("First touch:")} <b>{journey.first_touch.source}</b>{journey.first_touch.campaign ? ` / ${journey.first_touch.campaign}` : ""} {tx("on")} {new Date(journey.first_touch.at).toLocaleString()}</p>}
          <ul className="text-xs max-h-60 overflow-auto">{journey.events.map((ev, i) => <li key={i}>{new Date(ev.at).toLocaleString()} · {ev.kind}{ev.name ? `:${ev.name}` : ""} · {ev.path}</li>)}</ul></>)}
      </form>
      <section className="border rounded p-3 bg-white space-y-2">
        <h3 className="font-semibold">{tx("Custom event definitions")}</h3>
        <p className="text-xs text-gray-500">{tx("Custom events sent by the site keep only the properties defined here (wrong type or unknown: dropped). Defined events can start CRM workflows (identified visitors) and be used in audiences. Consent rules are unchanged.")}</p>
        <ul className="text-xs divide-y">{defs.map((d) => <li key={d.id} className="py-1 flex flex-wrap justify-between gap-2">
          <span><b>{d.name}</b>{d.active ? "" : tx(" (inactive)")} · {Object.entries(d.properties).map(([k, t]) => `${k}: ${t}`).join(", ") || tx("no properties")}{d.description ? ` · ${d.description}` : ""}</span>
          <button className="underline" onClick={() => setEdit({ id: d.id, name: d.name, description: d.description ?? "", props: Object.entries(d.properties).map(([k, t]) => `${k}:${t}`).join(", "), active: d.active })}>{tx("Edit")}</button></li>)}
          {defs.length === 0 && <li className="py-1 text-gray-500">{tx("No events defined yet.")}</li>}</ul>
        <form className="grid gap-2 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); saveDef(); }}>
          <input aria-label={tx("Event name")} required placeholder={tx("event name, e.g. demo_requested")} className="border rounded px-2 py-1" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} />
          <input aria-label={tx("Event description")} placeholder={tx("description")} className="border rounded px-2 py-1" value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} />
          <input aria-label={tx("Event properties")} placeholder={tx("product:string, cartons:number, trial:boolean")} className="border rounded px-2 py-1 sm:col-span-2" value={edit.props} onChange={(e) => setEdit({ ...edit, props: e.target.value })} />
          <label className="text-xs flex items-center gap-2"><input type="checkbox" checked={edit.active} onChange={(e) => setEdit({ ...edit, active: e.target.checked })} /> {tx("Active")}</label>
          <div className="flex gap-2 justify-end"><button className="border rounded px-3 py-1">{edit.id ? tx("Save changes") : tx("Add event")}</button>
            {edit.id && <button type="button" className="text-xs underline" onClick={() => setEdit({ name: "", description: "", props: "", active: true })}>{tx("Cancel")}</button>}</div>
        </form>
      </section>
      <details className="border rounded p-3 bg-white"><summary className="font-semibold cursor-pointer">{tx("Install on the website")}</summary>
        <pre className="text-xs overflow-x-auto mt-2">{`<script src="${typeof window !== "undefined" ? window.location.origin : ""}/povu-analytics.js" data-api="${api}" defer></script>`}</pre>
        <p className="text-xs text-gray-500">{tx("Shows a cookie banner (necessary / analytics / marketing). Nothing is sent before the visitor chooses. Mark buttons with data-povu-cta=\"name\" and forms with data-povu-form=\"name\".")}</p>
      </details>
      <EventTags events={defs.filter((d) => d.active).map((d) => d.name)} />
    </div>
  );
}
