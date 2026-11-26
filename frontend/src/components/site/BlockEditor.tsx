"use client";
// M46 visual block editor: add, edit, reorder and remove blocks; per-block audience (personalization), slot/fallback
// and experiment variant. The server validates everything again (links, media, sizes) on save.
import { useState } from "react";
import type { Block } from "./SiteBlocks";

const TYPES = ["hero", "heading", "text", "image", "button", "cta", "faq", "table", "video", "audio", "product", "form", "embed", "divider", "spacer", "columns"];
const csv = (v: unknown) => (Array.isArray(v) ? v.join(", ") : "");
const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

function Field({ label, value, onChange, area }: { label: string; value: string; onChange: (v: string) => void; area?: boolean }) {
  return <label className="block text-xs">{label}{area
    ? <textarea aria-label={label} className="border rounded px-1 w-full block" rows={3} value={value} onChange={(e) => onChange(e.target.value)} />
    : <input aria-label={label} className="border rounded px-1 w-full block" value={value} onChange={(e) => onChange(e.target.value)} />}</label>;
}

function One({ b, set }: { b: Block; set: (b: Block) => void }) {
  const f = (k: string, label: string, area = false) => <Field key={k} label={label} area={area} value={String(b[k] ?? "")} onChange={(v) => set({ ...b, [k]: v })} />;
  switch (b.type) {
    case "hero": return <>{f("title", "Title")}{f("subtitle", "Subtitle", true)}{f("image", "Background image (https)")}{f("cta_key", "CTA key")}</>;
    case "heading": return <>{f("text", "Text")}<label className="text-xs">Level <select aria-label="Heading level" className="border rounded" value={b.level ?? 2}
      onChange={(e) => set({ ...b, level: +e.target.value })}>{[1, 2, 3].map((n) => <option key={n} value={n}>H{n}</option>)}</select></label></>;
    case "text": return f("text", "Text (**bold**, [label](/path))", true);
    case "image": return <>{f("url", "Image URL (https)")}{f("alt", "Alternative text")}</>;
    case "button": return <>{f("label", "Label")}{f("href", "Link (/path or https://…)")}</>;
    case "cta": return f("cta_key", "CTA key");
    case "form": return f("form_slug", "Lead form slug");
    case "embed": return f("page_id", "Embed the live blocks of page (id)");
    case "table": return <>{f("table_key", "Data table key")}<Field label="Columns (comma separated)" value={csv(b.columns)} onChange={(v) => set({ ...b, columns: list(v) })} />{f("link_prefix", "Row link prefix (/products)")}</>;
    case "video": case "audio": return <>{f("media_id", "Media id")}{f("title", "Title")}</>;
    case "product": return <>{f("name", "Name")}{f("size", "Size")}{f("price", "Price text")}{f("image", "Image (https)")}</>;
    case "spacer": return <Field label="Height (px)" value={String(b.height ?? 24)} onChange={(v) => set({ ...b, height: +v || 24 })} />;
    case "faq": return <Field label="Questions — one per line: question | answer" area value={(b.items ?? []).map((i: { q: string; a: string }) => `${i.q} | ${i.a}`).join("\n")}
      onChange={(v) => set({ ...b, items: v.split("\n").map((l) => { const [q, ...a] = l.split("|"); return { q: (q ?? "").trim(), a: a.join("|").trim() }; }) })} />;
    case "columns": return <p className="text-xs text-gray-500">Two columns: edit their blocks in the JSON view.</p>;
    default: return null;
  }
}

export default function BlockEditor({ blocks, onChange }: { blocks: Block[]; onChange: (b: Block[]) => void }) {
  const [add, setAdd] = useState("text");
  const [open, setOpen] = useState<number | null>(null);
  const set = (i: number, b: Block) => onChange(blocks.map((x, j) => (j === i ? b : x)));
  const [dragFrom, setDragFrom] = useState<number | null>(null);   // M47.S01.T011 drag-and-drop; the arrows stay for keyboard users
  const moveTo = (from: number, to: number) => { if (from === to) return; const n = [...blocks]; const [x] = n.splice(from, 1); n.splice(to, 0, x); onChange(n); };
  const move = (i: number, d: number) => { const n = [...blocks]; const [x] = n.splice(i, 1); n.splice(i + d, 0, x); onChange(n); };
  return (
    <div className="space-y-2">
      {blocks.length === 0 && <p className="text-xs text-gray-500">No blocks yet. Add a hero, text or FAQ below.</p>}
      {blocks.map((b, i) => (
        <div key={b.id ?? i} className={`border rounded p-2 bg-white ${dragFrom === i ? "opacity-50" : ""}`} draggable
          onDragStart={() => setDragFrom(i)} onDragOver={(e) => e.preventDefault()} onDragEnd={() => setDragFrom(null)}
          onDrop={(e) => { e.preventDefault(); if (dragFrom !== null) moveTo(dragFrom, i); setDragFrom(null); }}>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <b className="uppercase cursor-move" title="Drag to reorder">⠿ {b.type}</b>
            <span className="text-gray-500 truncate max-w-[50%]">{String(b.text ?? b.title ?? b.label ?? b.cta_key ?? b.table_key ?? "")}</span>
            {b.audience && <span className="bg-amber-100 rounded px-1">audience</span>}
            {b.experiment && <span className="bg-sky-100 rounded px-1">test {b.experiment.key}:{b.experiment.variant}</span>}
            <span className="ml-auto flex gap-1">
              <button aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)}>↑</button>
              <button aria-label="Move down" disabled={i === blocks.length - 1} onClick={() => move(i, 1)}>↓</button>
              <button className="underline" onClick={() => setOpen(open === i ? null : i)}>{open === i ? "Close" : "Edit"}</button>
              <button className="text-red-600" aria-label="Remove block" onClick={() => onChange(blocks.filter((_, j) => j !== i))}>✕</button></span>
          </div>
          {open === i && <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <One b={b} set={(nb) => set(i, nb)} />
            <fieldset className="border rounded p-2 text-xs space-y-1 sm:col-span-2"><legend>Personalization &amp; testing</legend>
              <div className="grid gap-1 sm:grid-cols-4">
                <Field label="Lifecycle (e.g. CUSTOMER)" value={csv(b.audience?.lifecycle)} onChange={(v) => set(i, { ...b, audience: { ...b.audience, lifecycle: list(v) } })} />
                <Field label="Audiences" value={csv(b.audience?.segment)} onChange={(v) => set(i, { ...b, audience: { ...b.audience, segment: list(v) } })} />
                <Field label="Languages" value={csv(b.audience?.locale)} onChange={(v) => set(i, { ...b, audience: { ...b.audience, locale: list(v) } })} />
                <label className="text-xs">Visitor<select aria-label="Known visitor" className="border rounded block w-full" value={b.audience?.known === true ? "yes" : b.audience?.known === false ? "no" : ""}
                  onChange={(e) => { const known = e.target.value === "yes" ? true : e.target.value === "no" ? false : undefined; const a = { ...b.audience, known }; if (known === undefined) delete a.known; set(i, { ...b, audience: a }); }}>
                  <option value="">anyone</option><option value="yes">known (consented)</option><option value="no">anonymous</option></select></label>
                <Field label="Slot" value={b.slot ?? ""} onChange={(v) => set(i, { ...b, slot: v || undefined })} />
                <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={!!b.fallback} onChange={(e) => set(i, { ...b, fallback: e.target.checked || undefined })} />Fallback for the slot</label>
                <Field label="Experiment key" value={b.experiment?.key ?? ""} onChange={(v) => set(i, { ...b, experiment: v ? { key: v, variant: b.experiment?.variant ?? "a" } : undefined })} />
                <Field label="Variant" value={b.experiment?.variant ?? ""} onChange={(v) => set(i, { ...b, experiment: b.experiment ? { ...b.experiment, variant: v } : undefined })} />
              </div></fieldset>
          </div>}
        </div>))}
      <div className="flex gap-2 items-center text-xs">
        <select aria-label="Block type" className="border rounded" value={add} onChange={(e) => setAdd(e.target.value)}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select>
        <button className="border rounded px-2 py-1" onClick={() => { onChange([...blocks, { type: add, id: Math.random().toString(36).slice(2, 10), ...(add === "faq" ? { items: [] } : add === "columns" ? { left: [], right: [] } : add === "table" ? { columns: [] } : {}) }]); setOpen(blocks.length); }}>Add block</button>
      </div>
    </div>
  );
}
