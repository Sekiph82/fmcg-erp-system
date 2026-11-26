"use client";
// Landing pages + A/B tests (M36.S05.T002): pages on a lead form, variants with weights, live results with guardrails.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

interface Page { id: string; slug: string; name: string; status: string; lead_form_id: string; min_sample: number }
interface Variant { id: string; key: string; headline: string; weight: number; active: boolean; views: number; conversions: number; rate_pct: number | null; ci95_pct: [number, number] | null; p_value?: number | null }
interface Stats { page: { id: string; slug: string; status: string; min_sample: number }; variants: Variant[]; enough_data: boolean; verdict: string }
interface Form { id: string; name: string; slug: string }
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail; return typeof d === "string" ? d : tx("Request failed."); };

export default function LandingPages() {
  const [pages, setPages] = useState<Page[]>([]);
  const [forms, setForms] = useState<Form[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [st, setSt] = useState<Stats | null>(null);
  const [np, setNp] = useState({ slug: "", name: "", lead_form_id: "", min_sample: "100" });
  const [v, setV] = useState({ key: "A", headline: "", body: "", cta_label: "Send", weight: "50" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const loadPages = useCallback(() => apiClient.get<Page[]>("/api/v1/landing/pages").then((r) => setPages(r.data)).catch((e) => setMsg({ ok: false, text: err(e) })), []);
  const loadStats = useCallback((id: string) => apiClient.get<Stats>(`/api/v1/landing/pages/${id}/stats`).then((r) => setSt(r.data)), []);
  useEffect(() => { loadPages(); apiClient.get<Form[]>("/api/v1/crm/lead-forms").then((r) => setForms(r.data)).catch(() => setForms([])); }, [loadPages]);
  useEffect(() => { if (sel) loadStats(sel); else setSt(null); }, [sel, loadStats]);
  const act = async (fn: () => Promise<unknown>, ok: string) => { try { await fn(); setMsg({ ok: true, text: ok }); loadPages(); if (sel) loadStats(sel); } catch (e) { setMsg({ ok: false, text: err(e) }); } };
  const input = "border rounded px-3 py-2 text-sm";
  const publicUrl = (slug: string) => `${typeof window !== "undefined" ? window.location.origin : ""}/lp/${slug}`;

  return (
    <div className="p-4 sm:p-6 space-y-4">
      <div><h1 className="text-xl font-bold text-gray-900">{tx("Landing pages & A/B tests")}</h1>
        <p className="text-xs text-gray-500">{tx("Each visitor always sees the same variant. A winner is only named with enough data and a significant difference.")}</p></div>
      {msg && <p role="status" className={`text-sm rounded px-3 py-2 ${msg.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{msg.text}</p>}

      <div className="bg-white border rounded-xl p-3 grid gap-2 sm:grid-cols-5">
        <input aria-label={tx("Page address")} placeholder={tx("address (e.g. stockists)")} value={np.slug} onChange={(e) => setNp({ ...np, slug: e.target.value.toLowerCase() })} className={input} />
        <input aria-label={tx("Page name")} placeholder={tx("Name")} value={np.name} onChange={(e) => setNp({ ...np, name: e.target.value })} className={input} />
        <select aria-label={tx("Lead form")} value={np.lead_form_id} onChange={(e) => setNp({ ...np, lead_form_id: e.target.value })} className={input}>
          <option value="">{tx("Lead form…")}</option>{forms.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
        <input aria-label={tx("Minimum views per variant")} type="number" min={10} value={np.min_sample} onChange={(e) => setNp({ ...np, min_sample: e.target.value })} className={input} />
        <button disabled={!np.slug || !np.name || !np.lead_form_id} onClick={() => act(async () => { const r = await apiClient.post<{ id: string }>("/api/v1/landing/pages", { ...np, min_sample: Number(np.min_sample) }); setSel(r.data.id); }, tx("Page created."))}
          className="rounded bg-blue-600 text-white text-sm disabled:opacity-50">{tx("Create page")}</button>
      </div>

      <div className="flex flex-wrap gap-2">{pages.map((p) => (
        <button key={p.id} onClick={() => setSel(p.id)} className={`rounded-full border px-3 py-1 text-xs ${sel === p.id ? "bg-blue-600 text-white" : ""}`}>{p.name} · {p.status.toLowerCase()}</button>))}</div>

      {st && (<>
        <div className="bg-white border rounded-xl p-3 space-y-2 text-sm">
          <div className="flex flex-wrap gap-2 items-center justify-between">
            <a href={`/lp/${st.page.slug}`} target="_blank" rel="noreferrer" className="text-blue-700 underline break-all">{publicUrl(st.page.slug)}</a>
            <div className="flex gap-2">{(["LIVE", "PAUSED", "DRAFT"] as const).map((s) => (
              <button key={s} disabled={st.page.status === s} onClick={() => act(() => apiClient.post(`/api/v1/landing/pages/${st.page.id}/status`, { status: s }), `Page is ${s.toLowerCase()}.`)}
                className="rounded border px-2 py-1 text-xs disabled:opacity-40">{s === "LIVE" ? tx("Go live") : s === "PAUSED" ? tx("Pause") : tx("Draft")}</button>))}</div>
          </div>
          <p className={`text-sm ${st.enough_data ? "text-gray-900 font-medium" : "text-amber-700"}`}>{st.verdict}</p>
          <div className="overflow-x-auto"><table className="w-full">
            <thead className="text-xs text-gray-500"><tr>{[tx("Variant"), tx("Headline"), tx("Weight"), tx("Views"), tx("Conversions"), tx("Rate"), tx("95% range"), tx("p vs A")].map((h) => <th key={h} className="text-left px-2 py-1">{h}</th>)}</tr></thead>
            <tbody>{st.variants.map((r) => <tr key={r.id} className="border-t"><td className="px-2 py-1">{r.key}{!r.active && tx(" (off)")}</td><td className="px-2 py-1">{r.headline}</td><td className="px-2 py-1">{r.weight}</td>
              <td className="px-2 py-1">{r.views}</td><td className="px-2 py-1">{r.conversions}</td><td className="px-2 py-1">{r.rate_pct === null ? "—" : `${r.rate_pct}%`}</td>
              <td className="px-2 py-1">{r.ci95_pct ? `${r.ci95_pct[0]}–${r.ci95_pct[1]}%` : "—"}</td><td className="px-2 py-1">{r.p_value === undefined || r.p_value === null ? "—" : r.p_value.toFixed(3)}</td></tr>)}</tbody>
          </table></div>
        </div>
        <div className="bg-white border rounded-xl p-3 grid gap-2 sm:grid-cols-6 text-sm">
          <select aria-label={tx("Variant key")} value={v.key} onChange={(e) => setV({ ...v, key: e.target.value })} className={input}>{["A", "B", "C", "D", "E"].map((k) => <option key={k}>{k}</option>)}</select>
          <input aria-label={tx("Headline")} placeholder={tx("Headline")} value={v.headline} onChange={(e) => setV({ ...v, headline: e.target.value })} className={`${input} sm:col-span-2`} />
          <input aria-label={tx("Button text")} placeholder={tx("Button text")} value={v.cta_label} onChange={(e) => setV({ ...v, cta_label: e.target.value })} className={input} />
          <input aria-label={tx("Weight")} type="number" min={0} max={100} value={v.weight} onChange={(e) => setV({ ...v, weight: e.target.value })} className={input} />
          <button disabled={v.headline.length < 3} onClick={() => act(() => apiClient.put(`/api/v1/landing/pages/${st.page.id}/variants`, { ...v, weight: Number(v.weight), body: v.body || null }), tx("Variant {key} saved.", { key: v.key }))}
            className="rounded bg-blue-600 text-white disabled:opacity-50">{tx("Save variant")}</button>
          <textarea aria-label={tx("Variant text")} placeholder={tx("Text under the headline")} rows={3} value={v.body} onChange={(e) => setV({ ...v, body: e.target.value })} className={`${input} sm:col-span-6`} />
        </div>
      </>)}
    </div>
  );
}
