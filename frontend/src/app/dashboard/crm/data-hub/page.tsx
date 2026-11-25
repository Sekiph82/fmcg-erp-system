"use client";
// M45.S01.T001–T003: authorized data sources, prospecting with evidence, company research/enrichment, business cards.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Ev = { criterion: string; value: string; citation: string };
type Result = { kind: string; id: string; company_name: string; city: string | null; channel: string | null; email: string | null; score: number; confidence: number; unknown: string[]; evidence: Ev[]; can_email: boolean; source_age_days: number | null };
type Cand = { id: string; value: string; citation: string; confidence: number; status: string; age_days: number };
type FieldView = { field: string; current: string | null; verified: boolean; applicable: boolean; unknown: boolean; conflict: boolean; candidates: Cand[] };
type Source = { id: string; name: string; rows: number; license_note: string; expires_at: string };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : (d as { message?: string })?.message ?? "Something went wrong."; };
const box = "border rounded p-3 bg-white space-y-2";
const inp = "border rounded px-2 py-1";

export default function DataHubPage() {
  const [msg, setMsg] = useState<string | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [provider, setProvider] = useState<{ enrichment_provider: string; note: string } | null>(null);
  const [src, setSrc] = useState({ name: "", license_note: "", csv: "company_name,city,channel,segment,size,email,phone\n", mapping: "company_name=company_name, city=city, channel=channel, segment=segment, size_band=size, email=email, phone=phone" });
  const [crit, setCrit] = useState({ city: "", channel: "", segment: "", keywords: "" });
  const [run, setRun] = useState<{ run_id: string; results: Result[] } | null>(null);
  const [q, setQ] = useState("");
  const [custs, setCusts] = useState<{ id: string; name: string }[]>([]);
  const [research, setResearch] = useState<{ customer_id: string; name: string; fields: FieldView[] } | null>(null);
  const [card, setCard] = useState("");
  const [cardFields, setCardFields] = useState<Record<string, string> | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const load = useCallback(() => {
    apiClient.get("/api/v1/customer-data/sources").then((r) => setSources(r.data)).catch(() => setSources([]));
    apiClient.get("/api/v1/customer-data/provider").then((r) => setProvider(r.data)).catch(() => setProvider(null));
  }, []);
  useEffect(() => { load(); }, [load]);
  const go = (p: Promise<unknown>, ok?: string) => p.then(() => { if (ok) setMsg(ok); }).catch((e) => setMsg(err(e)));

  const importSrc = () => {
    const mapping = Object.fromEntries(src.mapping.split(",").map((x) => x.split("=").map((y) => y.trim())).filter((x) => x.length === 2 && x[1]));
    go(apiClient.post("/api/v1/customer-data/sources", { name: src.name, license_note: src.license_note, csv: src.csv, mapping }).then((r) => { setMsg(`Imported ${r.data.stored} rows; ${r.data.errors.length} notes.`); load(); }));
  };
  const search = () => {
    const body: Record<string, unknown> = {};
    (["city", "channel", "segment"] as const).forEach((k) => { if (crit[k]) body[k] = crit[k]; });
    if (crit.keywords) body.keywords = crit.keywords.split(",").map((s) => s.trim()).filter(Boolean);
    go(apiClient.post("/api/v1/customer-data/prospect", body).then((r) => setRun(r.data)));
  };
  const outreach = (r: Result) => go(apiClient.post(`/api/v1/customer-data/prospect/runs/${run!.run_id}/outreach`, { result_id: r.id }), "E-mail proposed: a colleague approves it under CRM → Add-ins & AI access.");
  const findCust = () => apiClient.get("/api/v1/customer-intel/customers", { params: { q, limit: 10 } }).then((r) => setCusts(r.data)).catch((e) => setMsg(err(e)));
  const doResearch = (id: string) => go(apiClient.post(`/api/v1/customer-data/research/${id}`).then((r) => setResearch(r.data)));
  const apply = (c: Cand, overwrite = false) => apiClient.post(`/api/v1/customer-data/facts/${c.id}/apply`, { overwrite }).then(() => { setMsg("Applied."); doResearch(research!.customer_id); })
    .catch((e) => { const m = err(e); if (m.includes("confirm the overwrite") && window.confirm(`${m} Overwrite?`)) apply(c, true); else setMsg(m); });

  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">Prospecting &amp; customer data</h2>
      {provider && <p className="text-xs text-gray-500">External data provider: {provider.enrichment_provider.toLowerCase().replace("_", " ")}. {provider.note}</p>}
      {msg && <p role="status" className="text-xs">{msg}</p>}

      <section className={box}>
        <h3 className="font-semibold">Authorized data sources</h3>
        <div className="grid md:grid-cols-2 gap-2">
          <input aria-label="Source name" className={inp} placeholder="Name (e.g. Trade fair list 2026)" value={src.name} onChange={(e) => setSrc({ ...src, name: e.target.value })} />
          <input aria-label="Licence note" className={inp} placeholder="Why we may use it" value={src.license_note} onChange={(e) => setSrc({ ...src, license_note: e.target.value })} />
        </div>
        <textarea aria-label="CSV" className={`${inp} w-full font-mono text-xs`} rows={4} value={src.csv} onChange={(e) => setSrc({ ...src, csv: e.target.value })} />
        <input aria-label="Column mapping" className={`${inp} w-full text-xs`} value={src.mapping} onChange={(e) => setSrc({ ...src, mapping: e.target.value })} />
        <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={importSrc}>Import</button>
        <ul className="text-xs">{sources.map((s) => <li key={s.id}>{s.name} · {s.rows} rows · {s.license_note} · deleted on {new Date(s.expires_at).toLocaleDateString()}
          <button className="ml-2 text-red-600 underline" onClick={() => go(apiClient.delete(`/api/v1/customer-data/sources/${s.id}`).then(load), "Source deleted.")}>Delete</button></li>)}</ul>
      </section>

      <section className={box}>
        <h3 className="font-semibold">Find prospects</h3>
        <div className="flex flex-wrap gap-2">{(["city", "channel", "segment", "keywords"] as const).map((k) =>
          <input key={k} aria-label={k} className={inp} placeholder={k === "keywords" ? "keywords, comma separated" : k} value={crit[k]} onChange={(e) => setCrit({ ...crit, [k]: e.target.value })} />)}
          <button className="border rounded px-3 py-1" onClick={search}>Search</button></div>
        <p className="text-xs text-gray-500">Existing customers are left out. Nothing is contacted automatically.</p>
        {run && (run.results.length === 0 ? <p className="text-xs text-gray-500">No matches.</p> :
          <ul className="text-xs divide-y">{run.results.map((r) => <li key={r.id} className="py-1 space-y-0.5">
            <div className="flex flex-wrap justify-between gap-2"><b>{r.company_name}</b><span>match {Math.round(r.score * 100)}% · known data {Math.round(r.confidence * 100)}%</span></div>
            <div className="text-gray-600">{r.evidence.map((e) => `${e.criterion}: ${e.value} (${e.citation})`).join(" · ")}</div>
            {r.unknown.length > 0 && <div className="text-gray-400">unknown: {r.unknown.join(", ")}</div>}
            {r.can_email ? <button className="underline" onClick={() => outreach(r)}>Propose first e-mail</button> : <span className="text-gray-400">no e-mail on file</span>}</li>)}</ul>)}
      </section>

      <section className={box}>
        <h3 className="font-semibold">Research &amp; enrich a customer</h3>
        <div className="flex gap-2"><input aria-label="Customer search" className={inp} placeholder="Customer name" value={q} onChange={(e) => setQ(e.target.value)} /><button className="border rounded px-3" onClick={findCust}>Find</button></div>
        <div className="flex flex-wrap gap-2 text-xs">{custs.map((c) => <button key={c.id} className="border rounded px-2" onClick={() => doResearch(c.id)}>{c.name}</button>)}</div>
        {research && <table className="text-xs w-full"><thead><tr className="text-left bg-gray-50"><th className="p-1">Field</th><th>Now</th><th>Sourced values</th></tr></thead>
          <tbody>{research.fields.map((f) => <tr key={f.field} className="border-t align-top"><td className="p-1">{f.field}{f.verified ? " ✓ verified" : ""}{f.conflict ? " · conflict" : ""}</td>
            <td>{f.current ?? "—"} {f.applicable && <button className="underline ml-1" onClick={() => go(apiClient.put(`/api/v1/customer-data/customers/${research.customer_id}/verified/${f.field}`, { verified: !f.verified }).then(() => doResearch(research.customer_id)))}>{f.verified ? "unverify" : "verify"}</button>}</td>
            <td>{f.unknown ? <span className="text-gray-400">unknown</span> : f.candidates.map((c) => <div key={c.id}>{c.value} <span className="text-gray-500">({c.citation}; {c.age_days} days old; confidence {c.confidence})</span>
              {c.status === "PROPOSED" && f.applicable && <><button className="underline ml-1" onClick={() => apply(c)}>apply</button><button className="underline ml-1" onClick={() => go(apiClient.post(`/api/v1/customer-data/facts/${c.id}/reject`).then(() => doResearch(research.customer_id)))}>reject</button></>}
              {c.status !== "PROPOSED" && <span className="ml-1">{c.status.toLowerCase()}</span>}</div>)}</td></tr>)}</tbody></table>}
      </section>

      <section className={box}>
        <h3 className="font-semibold">Business card to contact</h3>
        <textarea aria-label="Card text" className={`${inp} w-full`} rows={4} placeholder="Paste the card text (from your phone's text recognition) or type it" value={card} onChange={(e) => setCard(e.target.value)} />
        <button className="border rounded px-3 py-1 text-xs" onClick={() => go(apiClient.post("/api/v1/customer-data/business-card/parse", { text: card }).then((r) => {
          setCardFields(Object.fromEntries(["full_name", "job_title", "company", "email", "phone"].map((k) => [k, r.data.fields[k]?.value ?? ""]))); setConfirmed(false); }))}>Read fields</button>
        {cardFields && <div className="grid sm:grid-cols-2 gap-2 text-xs">{Object.keys(cardFields).map((k) => <label key={k}>{k.replace("_", " ")}<input aria-label={k} className={`${inp} w-full`} value={cardFields[k]} onChange={(e) => setCardFields({ ...cardFields, [k]: e.target.value })} /></label>)}
          <label className="flex items-center gap-2 sm:col-span-2"><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />I checked every field</label>
          <button className="bg-indigo-600 text-white rounded px-3 py-1" disabled={!confirmed} onClick={() => go(apiClient.post("/api/v1/customer-data/business-card/save", { ...cardFields, email: cardFields.email || null, phone: cardFields.phone || null, confirmed }).then(() => { setCardFields(null); setCard(""); }), "Contact created.")}>Create contact</button></div>}
      </section>
    </div>
  );
}
