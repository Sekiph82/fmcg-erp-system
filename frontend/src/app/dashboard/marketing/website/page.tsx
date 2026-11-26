"use client";
// M46.S01.T001/T002/T004/T005 website builder: sites, page tree, block editor, staging → review → publish, versions and
// rollback, preview (phone/desktop), SEO/AEO audits, translations, redirects, CTAs, data tables, keywords, experiments.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import BlockEditor from "@/components/site/BlockEditor";
import LibraryPanel from "@/components/site/LibraryPanel";
import { SiteBlocks, type Block, type Theme } from "@/components/site/SiteBlocks";

type Site = { id: string; key: string; name: string; locales: string[]; default_locale: string; domain: string | null; domain_status: string; theme: Theme; nav: { label: string; path: string }[]; require_approval: boolean; local_url: string };
type Page = { id: string; title: string; path: string; slug: string; kind: string; locale: string; status: string; access: string; access_list_id: string | null; live_version: number | null;
  translation_state: string; parent_id: string | null; table_id: string | null; author: string | null; category: string | null; tags: string[]; submitted_by: string | null; approved_by: string | null };
type Detail = Page & { draft: { blocks: Block[]; seo: any }; versions: { version: number; title: string; note: string | null; published_by: string; published_at: string; live: boolean }[];
  translations: { id: string; locale: string; path: string; status: string; translation_state: string }[] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : Array.isArray(d) ? String(d[0]?.msg ?? "Invalid input") : typeof (d as { detail?: unknown })?.detail === "string" ? (d as { detail: string }).detail : "Something went wrong."; };
const LOC = ["en", "sw", "tr"];

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="border rounded p-3 bg-white space-y-2"><h3 className="font-semibold text-sm">{title}</h3>{children}</section>;
}

function SiteSettings({ site, onSaved, say }: { site: Site; onSaved: () => void; say: (m: string) => void }) {
  const [f, setF] = useState({ name: site.name, locales: site.locales, default_locale: site.default_locale, domain: site.domain ?? "", theme: site.theme,
    nav: site.nav.map((n) => `${n.label} | ${n.path}`).join("\n"), require_approval: site.require_approval });
  const save = () => apiClient.patch(`/api/v1/cms/sites/${site.id}`, { ...f, nav: f.nav.split("\n").filter((l) => l.includes("|")).map((l) => { const [label, path] = l.split("|"); return { label: label.trim(), path: path.trim() }; }) })
    .then(() => { say("Site saved."); onSaved(); }).catch((e) => say(err(e)));
  return <Panel title="Site settings">
    <div className="grid gap-2 sm:grid-cols-3 text-xs">
      <label>Name<input aria-label="Site name" className="border rounded px-1 block w-full" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
      <label>Custom domain<input aria-label="Custom domain" className="border rounded px-1 block w-full" placeholder="www.povu.example.com" value={f.domain} onChange={(e) => setF({ ...f, domain: e.target.value })} /></label>
      <p className="self-end">Status: <b>{site.domain_status === "LOCAL_ONLY" ? "served locally" : "DNS pending (activation)"}</b> · <a className="underline" href={site.local_url} target="_blank" rel="noreferrer">{site.local_url}</a></p>
      <fieldset className="flex gap-2 items-center"><legend>Languages</legend>{LOC.map((l) => <label key={l} className="flex gap-1"><input type="checkbox" checked={f.locales.includes(l)}
        onChange={(e) => setF({ ...f, locales: e.target.checked ? [...f.locales, l] : f.locales.filter((x) => x !== l) })} />{l}</label>)}</fieldset>
      <label>Default<select aria-label="Default language" className="border rounded block" value={f.default_locale} onChange={(e) => setF({ ...f, default_locale: e.target.value })}>{f.locales.map((l) => <option key={l}>{l}</option>)}</select></label>
      <label className="flex items-center gap-1"><input type="checkbox" checked={f.require_approval} onChange={(e) => setF({ ...f, require_approval: e.target.checked })} />Second-person review before publishing</label>
      {(["brand_color", "text_color", "background", "accent"] as const).map((k) => <label key={k}>{k.replace("_", " ")}<input type="color" aria-label={k} className="block" value={f.theme[k]} onChange={(e) => setF({ ...f, theme: { ...f.theme, [k]: e.target.value } })} /></label>)}
      <label className="sm:col-span-3">Navigation (one per line: Label | /path)<textarea aria-label="Navigation" rows={3} className="border rounded px-1 block w-full" value={f.nav} onChange={(e) => setF({ ...f, nav: e.target.value })} /></label>
    </div>
    <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={save}>Save site</button>
  </Panel>;
}

function Editor({ id, site, pages, acls, tables, reload, say }: { id: string; site: Site; pages: Page[]; acls: { id: string; name: string }[]; tables: { id: string; key: string; name: string }[]; reload: () => void; say: (m: string) => void }) {
  const [d, setD] = useState<Detail | null>(null);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [seo, setSeo] = useState<any>({});
  const [meta, setMeta] = useState({ title: "", slug: "", author: "", category: "", tags: "", parent_id: "" });
  const [json, setJson] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ blocks: Block[] } | null>(null);
  const [wide, setWide] = useState(true);
  const [audit, setAudit] = useState<any>(null);
  const [aeo, setAeo] = useState<any>(null);
  const [exps, setExps] = useState<any[]>([]);
  const [aiTr, setAiTr] = useState(false);
  const [lay, setLay] = useState<Record<string, string>>({});                       // M51 per-page header / nav / footer override
  const [lib, setLib] = useState<{ id: string; key: string; kind: string; name: string; live_version_id: string | null }[]>([]);
  useEffect(() => { apiClient.get(`/api/v1/cms-layout/sites/${site.id}/components`).then((r) => setLib(r.data)).catch(() => setLib([])); }, [site.id]);
  const load = useCallback(() => apiClient.get(`/api/v1/cms/pages/${id}`).then((r) => {
    setD(r.data); setBlocks(r.data.draft?.blocks ?? []); setSeo(r.data.draft?.seo ?? {}); setLay(r.data.draft?.layout ?? {});
    setMeta({ title: r.data.title, slug: r.data.slug, author: r.data.author ?? "", category: r.data.category ?? "", tags: (r.data.tags ?? []).join(", "), parent_id: r.data.parent_id ?? "" });
    apiClient.get(`/api/v1/cms/pages/${id}/experiments`).then((x) => setExps(x.data)).catch(() => setExps([]));
  }).catch((e) => say(err(e))), [id, say]);
  useEffect(() => { load(); setPreview(null); setAudit(null); setAeo(null); }, [load]);
  if (!d) return <p className="text-xs">Loading…</p>;
  const act = (path: string, body: object = {}) => apiClient.post(`/api/v1/cms/pages/${id}/${path}`, body).then(() => { say("Done."); load(); reload(); }).catch((e) => say(err(e)));
  const save = () => {
    let draft: object = { blocks, seo, ...(Object.keys(lay).length ? { layout: lay } : {}) };
    if (json !== null) { try { draft = JSON.parse(json); } catch { say("The JSON is not valid."); return; } }
    return apiClient.patch(`/api/v1/cms/pages/${id}`, { title: meta.title, slug: meta.slug, draft, author: meta.author, category: meta.category,
      tags: meta.tags.split(",").map((t) => t.trim()).filter(Boolean), parent_id: meta.parent_id || null })
      .then((r) => { say(r.data.warnings?.length ? `Saved. ${r.data.warnings.join(" ")}` : "Draft saved (not live until published)."); setJson(null); load(); reload(); }).catch((e) => say(err(e)));
  };
  const setAccess = (access: string, access_list_id: string | null) => apiClient.patch(`/api/v1/cms/pages/${id}`, { access, ...(access_list_id ? { access_list_id } : {}) }).then(() => { load(); reload(); }).catch((e) => say(err(e)));
  return (
    <div className="space-y-3">
      <Panel title={`${d.title} · ${d.locale} · ${d.path}`}>
        <p className="text-xs">Status <b>{d.status}</b>{d.live_version ? ` · live v${d.live_version}` : " · not live"}{d.submitted_by ? ` · submitted by ${d.submitted_by}` : ""}{d.approved_by ? ` · approved by ${d.approved_by}` : ""}
          {d.translation_state !== "SOURCE" && ` · translation ${d.translation_state.replace("_", " ").toLowerCase()}`}</p>
        <div className="grid gap-2 sm:grid-cols-3 text-xs">
          <label>Title<input aria-label="Page title" className="border rounded px-1 block w-full" value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} /></label>
          <label>Slug<input aria-label="Slug" className="border rounded px-1 block w-full" value={meta.slug} onChange={(e) => setMeta({ ...meta, slug: e.target.value })} /></label>
          <label>Parent<select aria-label="Parent page" className="border rounded block w-full" value={meta.parent_id} onChange={(e) => setMeta({ ...meta, parent_id: e.target.value })}>
            <option value="">(top level)</option>{pages.filter((p) => p.id !== id && p.locale === d.locale).map((p) => <option key={p.id} value={p.id}>{p.path}</option>)}</select></label>
          {d.kind === "POST" && <><label>Author<input aria-label="Author" className="border rounded px-1 block w-full" value={meta.author} onChange={(e) => setMeta({ ...meta, author: e.target.value })} /></label>
            <label>Category<input aria-label="Category" className="border rounded px-1 block w-full" value={meta.category} onChange={(e) => setMeta({ ...meta, category: e.target.value })} /></label>
            <label>Tags<input aria-label="Tags" className="border rounded px-1 block w-full" value={meta.tags} onChange={(e) => setMeta({ ...meta, tags: e.target.value })} /></label></>}
          {d.kind === "DYNAMIC" && <p>Data table: <b>{tables.find((t) => t.id === d.table_id)?.name ?? "none"}</b> — use {"{{row.column}}"} in texts; each row gets {d.path}/&lt;row&gt;.</p>}
        </div>
        <fieldset className="border rounded p-2 text-xs"><legend>Search &amp; sharing</legend><div className="grid gap-2 sm:grid-cols-2">
          <label>Meta title ({(seo.meta_title ?? "").length}/65)<input aria-label="Meta title" className="border rounded px-1 block w-full" value={seo.meta_title ?? ""} onChange={(e) => setSeo({ ...seo, meta_title: e.target.value })} /></label>
          <label>Meta description ({(seo.meta_description ?? "").length}/160)<input aria-label="Meta description" className="border rounded px-1 block w-full" value={seo.meta_description ?? ""} onChange={(e) => setSeo({ ...seo, meta_description: e.target.value })} /></label>
          <label>Target keywords<input aria-label="Target keywords" className="border rounded px-1 block w-full" value={(seo.keywords ?? []).join(", ")} onChange={(e) => setSeo({ ...seo, keywords: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></label>
          <label>Canonical (optional)<input aria-label="Canonical" className="border rounded px-1 block w-full" value={seo.canonical ?? ""} onChange={(e) => setSeo({ ...seo, canonical: e.target.value || undefined })} /></label>
          <label className="flex items-center gap-1"><input type="checkbox" checked={!!seo.noindex} onChange={(e) => setSeo({ ...seo, noindex: e.target.checked })} />Hide from search engines</label>
        </div></fieldset>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span>Who can read:</span>
          <select aria-label="Page access" className="border rounded" value={d.access === "MEMBERS" ? d.access_list_id ?? "" : "PUBLIC"} onChange={(e) => setAccess(e.target.value === "PUBLIC" ? "PUBLIC" : "MEMBERS", e.target.value === "PUBLIC" ? null : e.target.value)}>
            <option value="PUBLIC">Everyone</option>{acls.map((a) => <option key={a.id} value={a.id}>Members: {a.name}</option>)}</select>
        </div>
      </Panel>
      <Panel title="Content">
        <div className="flex gap-2 text-xs"><button className="underline" onClick={() => setJson(json === null ? JSON.stringify({ blocks, seo }, null, 2) : null)}>{json === null ? "JSON view" : "Visual editor"}</button></div>
        {json === null ? <>
          <fieldset className="border rounded p-2 text-xs"><legend>Site frame for this page</legend><div className="grid gap-2 sm:grid-cols-3">
            {(["header", "nav", "footer"] as const).map((slot) => <label key={slot} className="block capitalize">{slot}
              <select aria-label={`Page ${slot}`} className="border rounded block w-full" value={lay[slot] ?? "inherit"} onChange={(e) => setLay((l) => { const n = { ...l, [slot]: e.target.value }; if (e.target.value === "inherit") delete n[slot]; return n; })}>
                <option value="inherit">inherit from site</option><option value="none">none on this page</option>
                {lib.filter((i) => i.kind === slot.toUpperCase() && i.live_version_id).map((i) => <option key={i.key} value={i.key}>{i.name}</option>)}</select></label>)}</div></fieldset>
          <BlockEditor blocks={blocks} onChange={setBlocks} siteId={site.id} locale={d.locale} extraDoc={Object.keys(lay).length ? { layout: lay } : undefined} library={lib} /></> : <textarea aria-label="Page JSON" className="w-full border rounded font-mono text-xs" rows={16} value={json} onChange={(e) => setJson(e.target.value)} />}
        <div className="flex flex-wrap gap-2 text-xs pt-2 border-t">
          <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={save}>Save draft</button>
          <button className="border rounded px-3 py-1" onClick={() => apiClient.get(`/api/v1/cms/pages/${id}/preview`).then((r) => setPreview(r.data)).catch((e) => say(err(e)))}>Preview</button>
          {["DRAFT", "PUBLISHED", "APPROVED"].includes(d.status) && <button className="border rounded px-3 py-1" onClick={() => act("submit")}>Submit for review</button>}
          {d.status === "IN_REVIEW" && <><button className="border rounded px-3 py-1 bg-green-50" onClick={() => act("approve", { ok: true })}>Approve</button>
            <button className="border rounded px-3 py-1" onClick={() => act("approve", { ok: false, note: "Changes needed" })}>Send back</button></>}
          {(d.status === "APPROVED" || !site.require_approval) && <button className="bg-green-600 text-white rounded px-3 py-1" onClick={() => act("publish", { note: "" })}>Publish</button>}
          <button className="border rounded px-3 py-1" onClick={() => apiClient.post(`/api/v1/cms/pages/${id}/narrate`).then(() => say("Narration saved in Members & media as staff-only audio; an approver decides who may hear it.")).catch((e) => say(err(e)))}>Narrate (audio)</button>
          {d.live_version && <button className="border rounded px-3 py-1 text-red-600" onClick={() => act("unpublish")}>Unpublish</button>}
          {d.live_version && <a className="underline self-center" target="_blank" rel="noreferrer" href={`/site/${site.key}/${d.locale}${d.path === "/" ? "" : d.path}`}>Open live page</a>}
        </div>
      </Panel>
      {preview && <Panel title="Preview (draft — not public)">
        <div className="flex gap-2 text-xs"><button className={wide ? "font-bold" : ""} onClick={() => setWide(true)}>Desktop</button><button className={!wide ? "font-bold" : ""} onClick={() => setWide(false)}>Phone</button></div>
        <div className="border rounded mx-auto overflow-auto" style={{ width: wide ? "100%" : 375, maxWidth: "100%", background: site.theme.background, color: site.theme.text_color, fontFamily: site.theme.font }}>
          <div className="p-4"><SiteBlocks blocks={preview.blocks} theme={site.theme} base={`/site/${site.key}/${d.locale}`} siteKey={site.key} /></div></div>
      </Panel>}
      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="SEO audit (draft)">
          <button className="border rounded px-2 py-1 text-xs" onClick={() => apiClient.get(`/api/v1/cms/pages/${id}/seo-audit`).then((r) => setAudit(r.data)).catch((e) => say(err(e)))}>Run SEO audit</button>
          {audit && <div className="text-xs space-y-1"><p>Score <b>{audit.score}</b>/100 · {audit.words} words · {audit.internal_links} internal links</p>
            <ul className="list-disc pl-4">{audit.findings.map((f: any, i: number) => <li key={i} className={f.level === "error" ? "text-red-700" : ""}>{f.message}</li>)}</ul>
            <p className="text-gray-500">Search Console: {audit.search_console.status.replace("_", " ").toLowerCase()} — {audit.search_console.detail}</p></div>}
        </Panel>
        <Panel title="Answer-engine readiness (AEO)">
          <button className="border rounded px-2 py-1 text-xs" onClick={() => apiClient.get(`/api/v1/cms/pages/${id}/aeo-audit`).then((r) => setAeo(r.data)).catch((e) => say(err(e)))}>Run AEO check</button>
          {aeo && <div className="text-xs space-y-1"><p>{aeo.ready}/{aeo.total} checks met</p>
            <ul>{aeo.checks.map((c: any) => <li key={c.code}>{c.ok ? "✓" : "✗"} {c.message}</li>)}</ul>
            <p className="text-gray-500">Visibility in answer engines: {aeo.visibility.status.replace("_", " ").toLowerCase()} — {aeo.visibility.detail}</p></div>}
        </Panel>
        <Panel title="Versions">
          <ul className="text-xs divide-y">{d.versions.length === 0 ? <li className="py-1 text-gray-500">Never published.</li> : d.versions.map((v) => <li key={v.version} className="py-1 flex flex-wrap justify-between gap-2">
            <span>v{v.version} · {new Date(v.published_at).toLocaleString()} · {v.published_by}{v.note ? ` · ${v.note}` : ""}{v.live ? " · LIVE" : ""}</span>
            {!v.live && <button className="underline" onClick={() => act("rollback", { version: v.version })}>Roll back to this</button>}</li>)}</ul>
        </Panel>
        <Panel title="Translations">
          <ul className="text-xs">{d.translations.map((t) => <li key={t.id}>{t.locale} · {t.path} · {t.status.toLowerCase()} · {t.translation_state.replace("_", " ").toLowerCase()}</li>)}</ul>
          <div className="flex gap-2 text-xs flex-wrap">{site.locales.filter((l) => l !== d.locale && !d.translations.some((t) => t.locale === l)).map((l) =>
            <button key={l} className="border rounded px-2 py-1" onClick={() => apiClient.post(`/api/v1/cms/pages/${id}/translate`, { locale: l, ai: aiTr }).then((r) => { say(r.data.engine === "copy" ? `Translation draft for ${l} created as a copy${aiTr ? " (no AI budget or provider)" : ""} — translate and review it.` : `Translation draft for ${l} written by ${r.data.engine} (≈ $${Number(r.data.cost).toFixed(4)}) — review it before publishing.`); load(); reload(); }).catch((e) => say(err(e)))}>Translate to {l}</button>)}
            <label className="flex items-center gap-1"><input type="checkbox" checked={aiTr} onChange={(e) => setAiTr(e.target.checked)} />Draft with AI (brand budget)</label>
            {d.translation_state !== "SOURCE" && d.translation_state !== "REVIEWED" && <button className="border rounded px-2 py-1" onClick={() => apiClient.post(`/api/v1/cms/pages/${id}/translation-state`, { state: "REVIEWED" }).then(load).catch((e) => say(err(e)))}>Mark translation reviewed</button>}</div>
        </Panel>
        {exps.length > 0 && <Panel title="Experiments">{exps.map((e) => <div key={e.id} className="text-xs space-y-1">
          <p><b>{e.key}</b> · {e.mode === "BANDIT" ? "adaptive (bandit)" : "A/B split"} · {e.status.toLowerCase()} · {e.views} views{!e.enough_data && " · not enough data yet"}</p>
          <table className="w-full"><thead><tr><th className="text-left">Variant</th><th>Views</th><th>Conv.</th><th>Rate</th><th>P(best)</th></tr></thead>
            <tbody>{e.variants.map((v: any) => <tr key={v.variant}><td>{v.variant}</td><td className="text-center">{v.views}</td><td className="text-center">{v.conversions}</td>
              <td className="text-center">{v.rate === null ? "—" : `${(v.rate * 100).toFixed(1)}%`}</td><td className="text-center">{(v.p_best * 100).toFixed(0)}%</td></tr>)}</tbody></table>
          <div className="flex gap-2">{e.mode === "AB" ? <button className="underline" onClick={() => apiClient.patch(`/api/v1/cms/experiments/${e.id}`, { mode: "BANDIT" }).then(load).catch((x) => say(err(x)))}>Switch to adaptive</button>
            : <button className="underline" onClick={() => apiClient.patch(`/api/v1/cms/experiments/${e.id}`, { mode: "AB" }).then(load).catch((x) => say(err(x)))}>Switch to A/B</button>}
            {e.status === "RUNNING" && <button className="underline" onClick={() => apiClient.patch(`/api/v1/cms/experiments/${e.id}`, { status: "STOPPED", winner: [...e.variants].sort((a: any, b: any) => b.p_best - a.p_best)[0].variant }).then(load).catch((x) => say(err(x)))}>Stop and keep the leader</button>}</div>
        </div>)}</Panel>}
      </div>
    </div>
  );
}

function SiteData({ site, say }: { site: Site; say: (m: string) => void }) {
  const [tab, setTab] = useState("redirects");
  const [rows, setRows] = useState<any[]>([]);
  const [f, setF] = useState<Record<string, string>>({});
  const [tableRows, setTableRows] = useState<{ id: string; text: string } | null>(null);
  const url = { redirects: "redirects", ctas: "ctas", tables: "tables", keywords: "keywords" }[tab]!;
  const load = useCallback(() => apiClient.get(`/api/v1/cms/sites/${site.id}/${url}`).then((r) => setRows(r.data)).catch(() => setRows([])), [site.id, url]);
  useEffect(() => { load(); setF({}); }, [load]);
  const post = (path: string, body: object) => apiClient.post(`/api/v1/cms/sites/${site.id}/${path}`, body).then(() => { say("Saved."); load(); }).catch((e) => say(err(e)));
  const input = (k: string, label: string) => <input aria-label={label} placeholder={label} className="border rounded px-1" value={f[k] ?? ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} />;
  return <Panel title="Site data">
    <div className="flex gap-3 text-xs">{["redirects", "ctas", "tables", "keywords"].map((t) => <button key={t} className={tab === t ? "font-bold underline" : ""} onClick={() => setTab(t)}>{t === "ctas" ? "CTAs" : t[0].toUpperCase() + t.slice(1)}</button>)}</div>
    {tab === "redirects" && <><div className="flex flex-wrap gap-2 text-xs">{input("from_path", "/old-path")}{input("to_path", "/new-path")}<button className="border rounded px-2" onClick={() => post("redirects", { from_path: f.from_path, to_path: f.to_path, code: 301 })}>Add 301</button></div>
      <ul className="text-xs divide-y">{rows.map((r) => <li key={r.id} className="py-1 flex justify-between gap-2"><span>{r.from_path} → {r.to_path} ({r.code}{r.auto ? ", automatic" : ""}) · {r.hits} hits</span>
        <button className="text-red-600" onClick={() => apiClient.delete(`/api/v1/cms/redirects/${r.id}`).then(load)}>Delete</button></li>)}</ul></>}
    {tab === "ctas" && <><div className="flex flex-wrap gap-2 text-xs">{input("key", "key")}{input("label", "Label")}{input("href", "/path or https://…")}<button className="border rounded px-2" onClick={() => post("ctas", { key: f.key, label: f.label, href: f.href })}>Save CTA</button></div>
      <ul className="text-xs divide-y">{rows.map((c) => <li key={c.id} className="py-1">{c.key} · “{c.label}” → {c.href} · {c.views} views · {c.clicks} clicks{c.ctr !== null ? ` · ${(c.ctr * 100).toFixed(1)}%` : ""}</li>)}</ul></>}
    {tab === "tables" && <><div className="flex flex-wrap gap-2 text-xs">{input("key", "key (products)")}{input("name", "Name")}{input("columns", "Columns: name, size, price")}
      <button className="border rounded px-2" onClick={() => post("tables", { key: f.key, name: f.name, columns: (f.columns ?? "").split(",").map((c) => ({ key: c.trim().toLowerCase().replace(/\W+/g, "_"), label: c.trim() })).filter((c) => c.key) })}>Create table</button></div>
      <ul className="text-xs divide-y">{rows.map((t) => <li key={t.id} className="py-1 space-y-1"><div className="flex flex-wrap gap-2 justify-between"><span><b>{t.name}</b> ({t.key}) · {t.rows} rows · {t.published ? "published" : "not published"}</span>
        <span className="flex gap-2"><button className="underline" onClick={() => apiClient.get(`/api/v1/cms/tables/${t.id}/rows`).then((r) => setTableRows({ id: t.id, text: ["slug," + t.columns.map((c: any) => c.key).join(","), ...r.data.map((x: any) => [x.slug, ...t.columns.map((c: any) => x.values[c.key] ?? "")].join(","))].join("\n") }))}>Edit rows</button>
          <button className="underline" onClick={() => apiClient.patch(`/api/v1/cms/tables/${t.id}`, { published: !t.published }).then(load).catch((e) => say(err(e)))}>{t.published ? "Unpublish" : "Publish"}</button></span></div>
        {tableRows && tableRows.id === t.id && <div><textarea aria-label="Rows CSV" rows={6} className="w-full border rounded font-mono" value={tableRows.text} onChange={(e) => setTableRows({ id: tableRows.id, text: e.target.value })} />
          <button className="border rounded px-2" onClick={() => { const [head, ...lines] = tableRows.text.split("\n").filter(Boolean); const cols = head.split(",").map((x) => x.trim());
            apiClient.put(`/api/v1/cms/tables/${t.id}/rows`, { rows: lines.map((l, i) => Object.fromEntries([...cols.map((c, j) => [c, l.split(",")[j]?.trim() ?? ""]), ["position", i]])) }).then(() => { say("Rows saved."); load(); }).catch((e) => say(err(e))); }}>Save rows</button></div>}</li>)}</ul></>}
    {tab === "keywords" && <><p className="text-xs text-gray-500">Paste a keyword export (keyword, volume, difficulty, locale). Only the numbers in your file are shown — nothing is estimated.</p>
      <textarea aria-label="Keyword CSV" rows={3} className="w-full border rounded text-xs font-mono" value={f.csv ?? ""} onChange={(e) => setF({ ...f, csv: e.target.value })} />
      <button className="border rounded px-2 text-xs" onClick={() => post("keywords/import", { csv: f.csv ?? "", source: "import" })}>Import</button>
      <table className="w-full text-xs"><thead><tr><th className="text-left">Keyword</th><th>Lang</th><th>Volume</th><th>Difficulty</th><th>Source</th></tr></thead>
        <tbody>{rows.map((k) => <tr key={k.id}><td>{k.keyword}</td><td className="text-center">{k.locale}</td><td className="text-center">{k.volume ?? "no data"}</td><td className="text-center">{k.difficulty ?? "no data"}</td><td className="text-center">{k.source}</td></tr>)}</tbody></table></>}
  </Panel>;
}

export default function WebsitePage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [site, setSite] = useState<Site | null>(null);
  const [pages, setPages] = useState<Page[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [acls, setAcls] = useState<{ id: string; name: string }[]>([]);
  const [tables, setTables] = useState<{ id: string; key: string; name: string }[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [nf, setNf] = useState({ title: "", kind: "PAGE", locale: "en", table_id: "" });
  const [ns, setNs] = useState({ name: "", key: "" });
  const [tpls, setTpls] = useState<{ key: string; name: string }[]>([]);
  const [tpl, setTpl] = useState("");
  const [view, setView] = useState<"pages" | "settings" | "data" | "library">("pages");
  const say = useCallback((m: string) => setMsg(m), []);
  const loadSites = useCallback(() => apiClient.get("/api/v1/cms/sites").then((r) => { setSites(r.data); setSite((s) => r.data.find((x: Site) => x.id === s?.id) ?? r.data[0] ?? null); }).catch((e) => say(err(e))), [say]);
  const loadPages = useCallback(() => { if (site) apiClient.get(`/api/v1/cms/sites/${site.id}/pages`).then((r) => setPages(r.data)).catch(() => setPages([])); }, [site]);
  useEffect(() => { loadSites(); apiClient.get("/api/v1/cms/access-lists").then((r) => setAcls(r.data)).catch(() => {}); }, [loadSites]);
  useEffect(() => { loadPages(); if (site) apiClient.get(`/api/v1/cms/sites/${site.id}/tables`).then((r) => setTables(r.data)).catch(() => setTables([])); }, [loadPages, site]);
  useEffect(() => { if (site) apiClient.get(`/api/v1/cms-layout/sites/${site.id}/components`, { params: { kind: "PAGE_TEMPLATE" } }).then((r) => setTpls(r.data.filter((i: { live_version_id: string | null }) => i.live_version_id))).catch(() => setTpls([])); setTpl(""); }, [site]);
  const create = () => site && (tpl && nf.kind === "PAGE" ? apiClient.post("/api/v1/cms-layout/pages/from-template", { site_id: site.id, template_key: tpl, title: nf.title, locale: nf.locale }) : apiClient.post("/api/v1/cms/pages", { site_id: site.id, title: nf.title, kind: nf.kind, locale: nf.locale, ...(nf.kind === "DYNAMIC" && nf.table_id ? { table_id: nf.table_id } : {}) }))
    .then((r) => { setSel(r.data.id); setNf({ ...nf, title: "" }); loadPages(); }).catch((e) => say(err(e)));
  return (
    <div className="p-4 space-y-3 text-sm">
      <h2 className="text-lg font-semibold">Website &amp; blog</h2>
      <p className="text-xs text-gray-500">Pages are drafts until a second person approves and publishes them. Custom domains are configuration only for now; sites are served locally.</p>
      {msg && <p role="status" className="text-xs bg-amber-50 border rounded p-2">{msg}</p>}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <select aria-label="Site" className="border rounded" value={site?.id ?? ""} onChange={(e) => { setSite(sites.find((s) => s.id === e.target.value) ?? null); setSel(null); }}>
          {sites.length === 0 && <option value="">No sites yet</option>}{sites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
        <input aria-label="New site name" placeholder="New site name" className="border rounded px-1" value={ns.name} onChange={(e) => setNs({ ...ns, name: e.target.value })} />
        <input aria-label="New site key" placeholder="key" className="border rounded px-1 w-24" value={ns.key} onChange={(e) => setNs({ ...ns, key: e.target.value })} />
        <button className="border rounded px-2" onClick={() => apiClient.post("/api/v1/cms/sites", ns).then(() => { setNs({ name: "", key: "" }); loadSites(); }).catch((e) => say(err(e)))}>Create site</button>
        {site && <span className="ml-auto flex gap-3">{(["pages", "library", "settings", "data"] as const).map((v) => <button key={v} className={view === v ? "font-bold underline" : ""} onClick={() => setView(v)}>{v === "data" ? "Redirects, CTAs, tables, keywords" : v === "library" ? "Library & theme" : v[0].toUpperCase() + v.slice(1)}</button>)}</span>}
      </div>
      {site && view === "settings" && <SiteSettings key={site.id} site={site} onSaved={loadSites} say={say} />}
      {site && view === "data" && <SiteData site={site} say={say} />}
      {site && view === "library" && <LibraryPanel key={site.id} siteId={site.id} locales={site.locales} say={say} />}
      {site && view === "pages" && <div className="grid gap-3 lg:grid-cols-[18rem_1fr]">
        <aside className="space-y-2">
          <div className="border rounded p-2 bg-white space-y-1 text-xs">
            <input aria-label="New page title" placeholder="New page title" className="border rounded px-1 w-full" value={nf.title} onChange={(e) => setNf({ ...nf, title: e.target.value })} />
            <div className="flex gap-1">
              <select aria-label="Page kind" className="border rounded" value={nf.kind} onChange={(e) => setNf({ ...nf, kind: e.target.value })}><option value="PAGE">Page</option><option value="POST">Blog post</option><option value="DYNAMIC">Dynamic (table)</option></select>
              <select aria-label="Page language" className="border rounded" value={nf.locale} onChange={(e) => setNf({ ...nf, locale: e.target.value })}>{site.locales.map((l) => <option key={l}>{l}</option>)}</select>
              {nf.kind === "DYNAMIC" && <select aria-label="Data table" className="border rounded" value={nf.table_id} onChange={(e) => setNf({ ...nf, table_id: e.target.value })}><option value="">table…</option>{tables.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select>}
              <button className="bg-indigo-600 text-white rounded px-2" onClick={create}>Add</button></div>
            {nf.kind === "PAGE" && tpls.length > 0 && <select aria-label="Start from template" className="border rounded w-full" value={tpl} onChange={(e) => setTpl(e.target.value)}><option value="">blank page</option>{tpls.map((t) => <option key={t.key} value={t.key}>Template: {t.name}</option>)}</select>}
          </div>
          <ul className="border rounded bg-white divide-y text-xs">{pages.length === 0 ? <li className="p-2 text-gray-500">No pages yet.</li> : pages.map((p) =>
            <li key={p.id} className={`p-2 cursor-pointer ${sel === p.id ? "bg-indigo-50" : ""}`} onClick={() => setSel(p.id)} style={{ paddingLeft: 8 + 10 * (p.path.split("/").length - 2) }}>
              <span className="font-medium">{p.title}</span> <span className="text-gray-500">{p.locale} · {p.path}</span>
              <div className="text-gray-500">{p.kind === "POST" ? "post" : p.kind === "DYNAMIC" ? "dynamic" : "page"} · {p.status.toLowerCase()}{p.live_version ? ` · v${p.live_version} live` : ""}{p.access === "MEMBERS" ? " · members" : ""}</div></li>)}</ul>
          <a className="text-xs underline block" target="_blank" rel="noreferrer" href={`/site/${site.key}/${site.default_locale}/blog`}>Open blog</a>
        </aside>
        <div>{sel ? <Editor id={sel} site={site} pages={pages} acls={acls} tables={tables} reload={loadPages} say={say} /> : <p className="text-xs text-gray-500">Pick a page or add one.</p>}</div>
      </div>}
    </div>
  );
}
