"use client";
// M51.S01.T002 shared library: header/footer/navigation, reusable sections and components, brand themes and page
// templates. Everything is versioned and goes through two-person approval; pages pick the live version by key.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import BlockEditor from "./BlockEditor";
import type { Block } from "./SiteBlocks";

type Item = { id: string; key: string; kind: string; name: string; status: string; live_version_id: string | null; submitted_by: string | null; approved_by: string | null };
type Detail = Item & { draft: any; versions: { version: number; note: string | null; approved_by: string | null; published_by: string; published_at: string; live: boolean }[] };
type Brand = { brand: string; brand_source: string; assets: { asset_ref: string; name: string; type: string }[]; tokens: any; email_theme: Record<string, string> };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };
const COLORS = ["brand", "text", "background", "accent", "muted", "surface", "onbrand"];
const FONTS = ["sans", "serif", "mono", "rounded"];
const KINDS = ["HEADER", "NAV", "FOOTER", "SECTION", "COMPONENT", "THEME", "PAGE_TEMPLATE"];
const base = "/api/v1/cms-layout";

function Tokens({ draft, assets, onChange }: { draft: any; assets: Brand["assets"]; onChange: (d: any) => void }) {
  const t = draft?.tokens ?? {};
  const set = (patch: object) => onChange({ tokens: { ...t, ...patch } });
  return <div className="grid gap-2 sm:grid-cols-4 text-xs">
    {COLORS.map((c) => <label key={c} className="block capitalize">{c}
      <span className="flex gap-1"><input type="color" aria-label={`${c} colour`} value={t.colors?.[c] ?? "#000000"} onChange={(e) => set({ colors: { ...t.colors, [c]: e.target.value.toUpperCase() } })} />
        <input aria-label={`${c} hex`} className="border rounded px-1 w-24" value={t.colors?.[c] ?? ""} onChange={(e) => set({ colors: { ...t.colors, [c]: e.target.value } })} /></span></label>)}
    {(["body_font", "heading_font"] as const).map((k) => <label key={k} className="block">{k.replace("_", " ")}<select aria-label={k.replace("_", " ")} className="border rounded block w-full" value={t[k] ?? "sans"} onChange={(e) => set({ [k]: e.target.value })}>
      {FONTS.map((f) => <option key={f}>{f}</option>)}</select></label>)}
    <label className="block">Corner radius (0–24)<input aria-label="Corner radius" type="number" min={0} max={24} className="border rounded px-1 block w-full" value={t.radius ?? 8} onChange={(e) => set({ radius: +e.target.value })} /></label>
    <label className="block">Approved logo (Brand Vault)<select aria-label="Approved logo" className="border rounded block w-full" value={t.logo_asset_ref ?? ""} onChange={(e) => set({ logo_asset_ref: e.target.value || undefined })}>
      <option value="">none</option>{assets.map((a) => <option key={a.asset_ref} value={a.asset_ref}>{a.name} ({a.asset_ref})</option>)}</select></label>
  </div>;
}

export default function LibraryPanel({ siteId, locales, say }: { siteId: string; locales: string[]; say: (m: string) => void }) {
  const [items, setItems] = useState<Item[]>([]);
  const [presets, setPresets] = useState<{ key: string; kind: string; name: string }[]>([]);
  const [sel, setSel] = useState<Detail | null>(null);
  const [draft, setDraft] = useState<any>(null);
  const [loc, setLoc] = useState("");
  const [nf, setNf] = useState({ preset: "", name: "", key: "", kind: "SECTION" });
  const [frame, setFrame] = useState({ header_key: "", footer_key: "", nav_key: "", theme_key: "" });
  const [usage, setUsage] = useState<{ pages: { path: string; locale: string; title: string; where: string }[]; site_slots: string[] } | null>(null);
  const [brand, setBrand] = useState<Brand | null>(null);
  const [rb, setRb] = useState("");
  const load = useCallback(() => {
    apiClient.get(`${base}/sites/${siteId}/components`).then((r) => setItems(r.data)).catch((e) => say(err(e)));
    apiClient.get(`${base}/sites/${siteId}/layout`).then((r) => setFrame({ header_key: r.data.header_key ?? "", footer_key: r.data.footer_key ?? "", nav_key: r.data.nav_key ?? "", theme_key: r.data.theme_key ?? "" })).catch(() => {});
    apiClient.get(`${base}/sites/${siteId}/brand`).then((r) => setBrand(r.data)).catch(() => setBrand(null));
  }, [siteId, say]);
  useEffect(() => { load(); apiClient.get(`${base}/meta`).then((r) => setPresets(r.data.presets)).catch(() => {}); }, [load]);
  const open = (id: string) => apiClient.get(`${base}/components/${id}`).then((r) => { setSel(r.data); setDraft(r.data.draft); setLoc(""); setUsage(null); }).catch((e) => say(err(e)));
  const act = (path: string, body: object = {}) => sel && apiClient.post(`${base}/components/${sel.id}/${path}`, body).then(() => { say("Done."); load(); open(sel.id); }).catch((e) => say(err(e)));
  const blocks: Block[] = sel && sel.kind !== "THEME" ? (loc ? draft?.locales?.[loc] ?? [] : draft?.blocks ?? []) : [];
  const setBlocks = (b: Block[]) => setDraft(loc ? { ...draft, locales: { ...(draft.locales ?? {}), [loc]: b } } : { ...draft, blocks: b });
  const live = (kind: string) => items.filter((i) => i.kind === kind && i.live_version_id);
  const pick = (slot: keyof typeof frame, kind: string) => <label className="block capitalize">{slot.replace("_key", "")}<select aria-label={`Site ${slot.replace("_key", "")}`} className="border rounded block w-full" value={frame[slot]} onChange={(e) => setFrame({ ...frame, [slot]: e.target.value })}>
    <option value="">none</option>{live(kind).map((i) => <option key={i.key} value={i.key}>{i.name} ({i.key})</option>)}</select></label>;
  return <div className="space-y-3">
    <div className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-sm">Shared library</h3>
      <div className="flex flex-wrap gap-2 text-xs items-end">
        <label>Start from<select aria-label="Preset" className="border rounded block" value={nf.preset} onChange={(e) => { const p = presets.find((x) => x.key === e.target.value); setNf({ ...nf, preset: e.target.value, kind: p?.kind ?? nf.kind, name: p?.name ?? nf.name, key: e.target.value }); }}>
          <option value="">blank</option>{presets.map((p) => <option key={p.key} value={p.key}>{p.name} ({p.kind.toLowerCase()})</option>)}</select></label>
        <label>Kind<select aria-label="Item kind" className="border rounded block" value={nf.kind} disabled={!!nf.preset} onChange={(e) => setNf({ ...nf, kind: e.target.value })}>{KINDS.map((k) => <option key={k}>{k}</option>)}</select></label>
        <label>Name<input aria-label="Item name" className="border rounded px-1 block" value={nf.name} onChange={(e) => setNf({ ...nf, name: e.target.value })} /></label>
        <label>Key<input aria-label="Item key" className="border rounded px-1 block w-32" value={nf.key} onChange={(e) => setNf({ ...nf, key: e.target.value })} /></label>
        <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={() => apiClient.post(`${base}/sites/${siteId}/components`, { name: nf.name || undefined, key: nf.key || undefined, kind: nf.kind, preset: nf.preset || undefined })
          .then((r) => { say("Created as a draft."); load(); open(r.data.id); }).catch((e) => say(err(e)))}>Create</button></div>
      <ul className="divide-y border rounded text-xs">{items.length === 0 ? <li className="p-2 text-gray-500">Nothing in the library yet. Start from a preset.</li> : items.map((i) =>
        <li key={i.id} className={`p-2 flex gap-2 items-center ${sel?.id === i.id ? "bg-indigo-50" : ""}`}><button className="underline font-medium" onClick={() => open(i.id)}>{i.name}</button>
          <span className="text-gray-500">{i.key} · {i.kind.toLowerCase().replace("_", " ")} · {i.status.toLowerCase().replace("_", " ")}{i.live_version_id ? " · live" : ""}</span></li>)}</ul>
    </div>
    <div className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-sm">Site header, navigation, footer and theme</h3>
      <div className="grid gap-2 sm:grid-cols-4 text-xs">{pick("header_key", "HEADER")}{pick("nav_key", "NAV")}{pick("footer_key", "FOOTER")}{pick("theme_key", "THEME")}</div>
      <button className="border rounded px-3 py-1 text-xs" onClick={() => apiClient.put(`${base}/sites/${siteId}/layout`, Object.fromEntries(Object.entries(frame).map(([k, v]) => [k, v || null]))).then(() => say("Site frame saved.")).catch((e) => say(err(e)))}>Save site frame (approvers)</button>
      <p className="text-xs text-gray-500">Only published items can be assigned. A page can still hide or replace each slot in its own settings.</p></div>
    {brand && <div className="border rounded p-3 bg-white space-y-1 text-xs"><h3 className="font-semibold text-sm">Brand tokens in use</h3>
      <p>Brand <b>{brand.brand}</b> (source: {brand.brand_source}). {brand.assets.length} approved brand assets.</p>
      <div className="flex flex-wrap gap-2" aria-label="Colour tokens">{Object.entries(brand.tokens.colors as Record<string, string>).map(([k, v]) => <span key={k} className="flex items-center gap-1"><i className="inline-block w-4 h-4 border" style={{ background: v }} />{k} {v}</span>)}</div>
      <p>E-mail designer (read-only, derived): {Object.entries(brand.email_theme).filter(([k]) => k !== "font").map(([k, v]) => <span key={k} className="mr-2"><i className="inline-block w-3 h-3 border align-middle mr-1" style={{ background: v }} />{k.replace("_", " ")} {v}</span>)}</p></div>}
    {sel && <div className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-sm">{sel.name} <span className="text-gray-500 font-normal">({sel.kind.toLowerCase().replace("_", " ")}, {sel.status.toLowerCase().replace("_", " ")})</span></h3>
      {sel.kind === "THEME" ? <Tokens draft={draft} assets={brand?.assets ?? []} onChange={setDraft} />
        : <>{sel.kind !== "PAGE_TEMPLATE" && <label className="text-xs">Language variant <select aria-label="Language variant" className="border rounded" value={loc} onChange={(e) => setLoc(e.target.value)}>
            <option value="">default (all languages)</option>{locales.map((l) => <option key={l} value={l}>{l} only</option>)}</select></label>}
          <BlockEditor key={`${sel.id}-${loc}`} blocks={blocks} onChange={setBlocks} siteId={siteId} locale={loc || undefined} kind={sel.kind} /></>}
      <div className="flex flex-wrap gap-2 text-xs pt-2 border-t">
        <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={() => apiClient.patch(`${base}/components/${sel.id}`, { draft }).then((r) => { say(r.data.warnings?.length ? `Saved. ${r.data.warnings.join(" ")}` : "Draft saved (not live until published)."); load(); open(sel.id); }).catch((e) => say(err(e)))}>Save draft</button>
        {["DRAFT", "PUBLISHED", "APPROVED"].includes(sel.status) && <button className="border rounded px-3 py-1" onClick={() => act("submit")}>Submit for review</button>}
        {sel.status === "IN_REVIEW" && <><button className="border rounded px-3 py-1 bg-green-50" onClick={() => act("approve", { ok: true })}>Approve</button>
          <button className="border rounded px-3 py-1" onClick={() => act("approve", { ok: false, note: "Changes needed" })}>Send back</button></>}
        {sel.status === "APPROVED" && <button className="bg-green-600 text-white rounded px-3 py-1" onClick={() => act("publish", { note: "" })}>Publish new version</button>}
        <button className="border rounded px-3 py-1" onClick={() => apiClient.get(`${base}/components/${sel.id}/usage`).then((r) => setUsage(r.data)).catch((e) => say(err(e)))}>Where is it used?</button>
        {sel.versions.length > 0 && <span className="flex gap-1 items-center"><select aria-label="Version to restore" className="border rounded" value={rb} onChange={(e) => setRb(e.target.value)}><option value="">version…</option>
          {sel.versions.map((v) => <option key={v.version} value={v.version}>v{v.version}{v.live ? " (live)" : ""} {v.note ?? ""}</option>)}</select>
          <button className="border rounded px-2 py-1" disabled={!rb} onClick={() => act("rollback", { version: +rb })}>Roll back (approvers)</button></span>}
      </div>
      <p className="text-xs text-gray-500">Status {sel.status.toLowerCase().replace("_", " ")}{sel.submitted_by ? ` · submitted by ${sel.submitted_by}` : ""}{sel.approved_by ? ` · approved by ${sel.approved_by}` : ""}. A second person approves before anything goes live; pages update automatically when a new version is published.</p>
      {usage && <div className="text-xs"><b>Used by</b> {usage.pages.length === 0 && usage.site_slots.length === 0 ? "nothing yet" : ""}<ul className="list-disc pl-4">{usage.pages.map((u, i) => <li key={i}>{u.title} ({u.locale} {u.path}, {u.where})</li>)}{usage.site_slots.map((s) => <li key={s}>site {s}</li>)}</ul></div>}
    </div>}
  </div>;
}
