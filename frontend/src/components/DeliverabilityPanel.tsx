"use client";
// M44.S01.T011: bounces/complaints from signed provider events, suppression counts, SPF/DKIM/DMARC plan and offline check.
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface Summary { events: Record<string, number>; unmatched_ignored: number; suppressed: Record<string, number>; providers: Record<string, boolean> }
interface Rec { type: string; host: string; value: string; purpose: string }

export function DeliverabilityPanel() {
  const [s, setS] = useState<Summary | null>(null);
  const [domain, setDomain] = useState("");
  const [relay, setRelay] = useState("");
  const [plan, setPlan] = useState<Rec[] | null>(null);
  const [vals, setVals] = useState({ spf: "", dkim: "", dmarc: "" });
  const [checks, setChecks] = useState<{ record: string; ok: boolean; detail: string }[]>([]);
  useEffect(() => { apiClient.get("/api/v1/deliverability/summary").then((r) => setS(r.data)).catch(() => setS(null)); }, []);
  const i = "border rounded px-2 py-1 text-xs w-full";
  return (
    <div className="border rounded-lg bg-white p-3 space-y-2 text-xs">
      <div className="text-sm font-semibold">Deliverability</div>
      {s && <>
        <p>Provider event feeds: {Object.entries(s.providers).map(([k, v]) => `${k} ${v ? "connected" : "not set up"}`).join(" · ")}</p>
        <p>Last 30 days: {Object.entries(s.events).map(([k, v]) => `${k.toLowerCase()} ${v}`).join(", ") || "no events"} · ignored (did not match a sent e-mail): {s.unmatched_ignored}</p>
        <p>Suppressed addresses: {Object.entries(s.suppressed).map(([k, v]) => `${k.toLowerCase()} ${v}`).join(", ") || "none"}</p>
      </>}
      <form className="flex flex-wrap gap-1" onSubmit={async (e) => { e.preventDefault(); try { setPlan((await apiClient.get("/api/v1/deliverability/dns-plan", { params: { domain, relay_include: relay } })).data.records); } catch { setPlan(null); } }}>
        <input required className="border rounded px-2 py-1" placeholder="sending domain" value={domain} onChange={(e) => setDomain(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="relay SPF include (e.g. mailgun.org)" value={relay} onChange={(e) => setRelay(e.target.value)} />
        <button className="border rounded px-2">DNS records to publish</button>
      </form>
      {plan?.map((r) => <div key={r.host} className="border rounded p-1 break-all"><b>{r.type} {r.host}</b><br />{r.value}<br /><span className="text-gray-500">{r.purpose}</span></div>)}
      <form className="space-y-1" onSubmit={async (e) => { e.preventDefault(); setChecks((await apiClient.post("/api/v1/deliverability/check", { ...vals, relay_include: relay })).data); }}>
        <input className={i} placeholder="Paste the SPF TXT value you published" value={vals.spf} onChange={(e) => setVals({ ...vals, spf: e.target.value })} />
        <input className={i} placeholder="Paste the DKIM TXT value" value={vals.dkim} onChange={(e) => setVals({ ...vals, dkim: e.target.value })} />
        <input className={i} placeholder="Paste the DMARC TXT value" value={vals.dmarc} onChange={(e) => setVals({ ...vals, dmarc: e.target.value })} />
        <button className="border rounded px-2">Check values</button>
      </form>
      {checks.map((c) => <p key={c.record} className={c.ok ? "text-green-700" : "text-red-600"}>{c.ok ? "✓" : "✗"} {c.record}: {c.detail}</p>)}
    </div>
  );
}
