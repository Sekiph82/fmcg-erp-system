"use client";
// M44.S01.T009 first-party website analytics: consented visitors only, bots dropped, no IP or raw ids stored.
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface Summary { visitors: number; sessions: number; page_views: number; identified_visitors: number; note: string;
  top_pages: [string, number][]; sources: [string, number][]; events: [string, number][] }
interface Step { step: string; visitors: number; of_previous: number | null }
interface Journey { linked: boolean; first_touch: { source: string; medium: string | null; campaign: string | null; at: string } | null;
  events: { at: string; kind: string; name: string | null; path: string }[] }

const err = (e: unknown) => ((e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail as string) || "Request failed.";

function List({ title, rows }: { title: string; rows: [string, number][] }) {
  return (
    <div className="border rounded p-3 bg-white">
      <h3 className="font-semibold text-sm mb-1">{title}</h3>
      {rows.length === 0 ? <p className="text-xs text-gray-500">No data yet.</p> :
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
  useEffect(() => { setSum(null); apiClient.get(`/api/v1/web-analytics/summary?days=${days}`).then((r) => setSum(r.data)).catch((e) => setMsg(err(e))); }, [days]);
  const api = typeof window !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL || window.location.origin) : "";
  return (
    <div className="p-4 space-y-4 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Website analytics</h2>
        <select aria-label="Period" className="border rounded px-2 py-1" value={days} onChange={(e) => setDays(+e.target.value)}>
          {[7, 30, 90, 365].map((d) => <option key={d} value={d}>Last {d} days</option>)}</select>
      </div>
      {msg && <p role="alert" className="text-red-600 text-xs">{msg}</p>}
      {!sum ? <p className="text-gray-500">Loading…</p> : <>
        <p className="text-xs text-gray-500">{sum.note}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {([["Visitors", sum.visitors], ["Sessions", sum.sessions], ["Page views", sum.page_views], ["Identified (consented)", sum.identified_visitors]] as const).map(([k, v]) =>
            <div key={k} className="border rounded p-3 bg-white"><div className="text-xs text-gray-500">{k}</div><div className="text-xl font-semibold">{v}</div></div>)}
        </div>
        <div className="grid md:grid-cols-3 gap-2"><List title="Top pages" rows={sum.top_pages} /><List title="First-touch sources" rows={sum.sources} /><List title="Events" rows={sum.events} /></div>
      </>}
      <form className="border rounded p-3 bg-white space-y-2" onSubmit={(e) => { e.preventDefault(); setMsg(null);
        apiClient.get("/api/v1/web-analytics/funnel", { params: { steps, days } }).then((r) => setFunnel(r.data)).catch((x) => setMsg(err(x))); }}>
        <h3 className="font-semibold">Funnel</h3>
        <div className="flex flex-wrap gap-2"><input aria-label="Funnel steps" className="border rounded px-2 py-1 flex-1 min-w-0" value={steps} onChange={(e) => setSteps(e.target.value)} />
          <button className="border rounded px-3 py-1">Show</button></div>
        <p className="text-xs text-gray-500">Comma-separated, in order: page paths (/pricing) or events (CTA:demo, FORM:contact).</p>
        {funnel && <ol className="text-xs space-y-1">{funnel.map((s) => <li key={s.step}><b>{s.step}</b>: {s.visitors} visitors{s.of_previous != null ? ` (${Math.round(s.of_previous * 100)}% of previous)` : ""}</li>)}</ol>}
      </form>
      <form className="border rounded p-3 bg-white space-y-2" onSubmit={(e) => { e.preventDefault(); setMsg(null);
        apiClient.get("/api/v1/web-analytics/journey", { params: { email } }).then((r) => setJourney(r.data)).catch((x) => setMsg(err(x))); }}>
        <h3 className="font-semibold">Contact journey</h3>
        <div className="flex flex-wrap gap-2"><input aria-label="Contact e-mail" type="email" required className="border rounded px-2 py-1 flex-1 min-w-0" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className="border rounded px-3 py-1">Show</button></div>
        {journey && (!journey.linked ? <p className="text-xs text-gray-500">No website visits linked to this address (links exist only after the visitor gave marketing consent).</p> : <>
          {journey.first_touch && <p className="text-xs">First touch: <b>{journey.first_touch.source}</b>{journey.first_touch.campaign ? ` / ${journey.first_touch.campaign}` : ""} on {new Date(journey.first_touch.at).toLocaleString()}</p>}
          <ul className="text-xs max-h-60 overflow-auto">{journey.events.map((ev, i) => <li key={i}>{new Date(ev.at).toLocaleString()} · {ev.kind}{ev.name ? `:${ev.name}` : ""} · {ev.path}</li>)}</ul></>)}
      </form>
      <details className="border rounded p-3 bg-white"><summary className="font-semibold cursor-pointer">Install on the website</summary>
        <pre className="text-xs overflow-x-auto mt-2">{`<script src="${typeof window !== "undefined" ? window.location.origin : ""}/povu-analytics.js" data-api="${api}" defer></script>`}</pre>
        <p className="text-xs text-gray-500">Shows a cookie banner (necessary / analytics / marketing). Nothing is sent before the visitor chooses. Mark buttons with data-povu-cta=&quot;name&quot; and forms with data-povu-form=&quot;name&quot;.</p>
      </details>
    </div>
  );
}
