"use client";
// M46/M51 visual layout editor. Blocks are typed data (never HTML/CSS/JS): the structure tree supports nesting
// (section > row > column, grid), drag and drop with a full keyboard alternative, per-breakpoint style controls built from
// the server's allow-lists, per-breakpoint visibility, a live canvas preview rendered by the server's validated output,
// and undo/redo. The server validates everything again on save and rejects unknown properties and values.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "@/lib/api";
import { BpContext, CanvasContext, SiteBlocks, type Block, type Bp, type Theme } from "./SiteBlocks";

const TYPES = ["section", "row", "grid", "hero", "heading", "text", "image", "button", "cta", "faq", "table", "video", "audio", "product", "form", "embed", "component", "divider", "spacer", "columns"];
const CONTAINERS = ["section", "row", "column", "grid"];
const BPS: Bp[] = ["desktop", "tablet", "mobile"];
const BP_WIDTH: Record<Bp, string | number> = { desktop: "100%", tablet: 768, mobile: 375 };
const GROUPS: [string, string[]][] = [
  ["Spacing", ["padding_top", "padding_bottom", "padding_left", "padding_right", "margin_top", "margin_bottom", "gap"]],
  ["Alignment and layout", ["align", "width", "justify", "valign", "span", "cols"]],
  ["Typography", ["font_size", "font_weight", "font_family", "line_height"]],
  ["Colour and decoration", ["color", "background", "border", "border_color", "radius", "shadow"]]];
type Meta = { style: Record<string, (string | number)[]>; type_only: Record<string, string[]>; max_depth: number };
type Library = { key: string; kind: string; name: string; id?: string };
const csv = (v: unknown) => (Array.isArray(v) ? v.join(", ") : "");
const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const newId = () => Math.random().toString(36).slice(2, 10);
const label = (s: string) => s.replace(/_/g, " ");

function Field({ label: l, value, onChange, area }: { label: string; value: string; onChange: (v: string) => void; area?: boolean }) {
  return <label className="block text-xs">{l}{area
    ? <textarea aria-label={l} className="border rounded px-1 w-full block" rows={3} value={value} onChange={(e) => onChange(e.target.value)} />
    : <input aria-label={l} className="border rounded px-1 w-full block" value={value} onChange={(e) => onChange(e.target.value)} />}</label>;
}

// ── pure tree helpers (the tree is cloned before every change) ─────────────────
type Loc = { list: Block[]; idx: number; parent: Block | null };
function locate(root: Block[], id: string, parent: Block | null = null): Loc | null {
  for (let i = 0; i < root.length; i++) {
    if (root[i].id === id) return { list: root, idx: i, parent };
    if (Array.isArray(root[i].children)) { const f = locate(root[i].children, id, root[i]); if (f) return f; }
  }
  return null;
}
const flat = (bs: Block[]): Block[] => bs.flatMap((b) => [b, ...(Array.isArray(b.children) ? flat(b.children) : [])]);
const accepts = (parent: Block | null, child: Block) =>
  child.type === "column" ? parent?.type === "row" : parent === null ? true : parent.type === "row" ? child.type === "column" : ["section", "column", "grid"].includes(parent.type);
const describe = (b: Block) => `${b.type}${b.text || b.title || b.label || b.name || b.key ? `: ${String(b.text ?? b.title ?? b.label ?? b.name ?? b.key).slice(0, 30)}` : ""}`;

function One({ b, set, library }: { b: Block; set: (b: Block) => void; library: Library[] }) {
  const f = (k: string, l: string, area = false) => <Field key={k} label={l} area={area} value={String(b[k] ?? "")} onChange={(v) => set({ ...b, [k]: v })} />;
  const [src, setSrc] = useState<Block[]>([]);
  const lib = b.type === "component" ? library.find((x) => x.key === b.key) : undefined;
  useEffect(() => {
    if (!lib?.id) { setSrc([]); return; }
    apiClient.get(`/api/v1/cms-layout/components/${lib.id}`).then((r) => setSrc(flat(r.data.draft?.blocks ?? []).filter((x: Block) => ["text", "heading", "button"].includes(x.type)))).catch(() => setSrc([]));
  }, [lib?.id]);
  switch (b.type) {
    case "section": return <><label className="block text-xs">Page landmark<select aria-label="Section element" className="border rounded block w-full" value={b.as ?? "div"} onChange={(e) => set({ ...b, as: e.target.value })}>
      {["div", "section", "aside", "article"].map((t) => <option key={t}>{t}</option>)}</select></label>{f("label", "Accessible name (for section, aside, article)")}</>;
    case "row": return <p className="text-xs text-gray-500">A row holds columns on a 12-column grid. Set each column&apos;s width per breakpoint.</p>;
    case "column": case "grid": return <p className="text-xs text-gray-500">{b.type === "column" ? "Set the column span (1–12) per breakpoint below. On phones it stacks full width unless you choose otherwise." : "Set the number of grid columns per breakpoint below."}</p>;
    case "component": return <>
      <label className="block text-xs">Reusable component<select aria-label="Reusable component" className="border rounded block w-full" value={b.key ?? ""} onChange={(e) => set({ ...b, key: e.target.value, overrides: {} })}>
        <option value="">choose…</option>{library.filter((x) => ["SECTION", "COMPONENT"].includes(x.kind)).map((x) => <option key={x.key} value={x.key}>{x.name} ({x.key})</option>)}</select></label>
      {src.length > 0 && <fieldset className="border rounded p-2 text-xs sm:col-span-2 space-y-1"><legend>Override on this page only</legend>
        {src.map((x) => { const fld = x.type === "button" ? "label" : "text"; return <Field key={x.id} label={`Override ${x.type}: ${String(x[fld]).slice(0, 40)}`} value={b.overrides?.[x.id as string]?.[fld] ?? ""}
          onChange={(v) => { const ov = { ...(b.overrides ?? {}) }; const cur = { ...(ov[x.id as string] ?? {}) }; if (v) cur[fld] = v; else delete cur[fld]; if (Object.keys(cur).length) ov[x.id as string] = cur; else delete ov[x.id as string]; set({ ...b, overrides: ov }); }} />; })}</fieldset>}</>;
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
    case "columns": return <p className="text-xs text-gray-500">Legacy two-column block: edit its blocks in the JSON view, or use a row with columns instead.</p>;
    default: return null;
  }
}

export default function BlockEditor({ blocks, onChange, siteId, locale, kind = "PAGE", extraDoc, library = [] }: {
  blocks: Block[]; onChange: (b: Block[]) => void; siteId?: string; locale?: string; kind?: string; extraDoc?: Record<string, unknown>; library?: Library[] }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [bp, setBp] = useState<Bp>("desktop");
  const [add, setAdd] = useState("text");
  const [past, setPast] = useState<Block[][]>([]);
  const [future, setFuture] = useState<Block[][]>([]);
  const [drag, setDrag] = useState<string | null>(null);
  const [drop, setDrop] = useState<{ id: string; pos: "before" | "after" | "inside" } | null>(null);
  const [said, setSaid] = useState("");
  const [prev, setPrev] = useState<{ blocks: Block[]; theme: Theme; error?: string; warnings?: string[] } | null>(null);
  const tree = useRef<HTMLUListElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const focusId = useRef<string | null>(null);
  const last = useRef<{ key: string; at: number }>({ key: "", at: 0 });

  useEffect(() => { apiClient.get("/api/v1/cms-layout/meta").then((r) => setMeta(r.data)).catch(() => setMeta(null)); }, []);
  // every block needs an id (older drafts may not have one): add them once, quietly
  useEffect(() => { if (flat(blocks).some((b) => !b.id)) { const t = structuredClone(blocks); flat(t).forEach((b) => { if (!b.id) b.id = newId(); }); onChange(t); } }, [blocks, onChange]);

  const commit = useCallback((next: Block[], coalesce?: string) => {
    const now = Date.now();
    if (!(coalesce && last.current.key === coalesce && now - last.current.at < 1200)) { setPast((p) => [...p.slice(-49), blocks]); setFuture([]); }
    last.current = { key: coalesce ?? "", at: now };
    onChange(next);
  }, [blocks, onChange]);
  const undo = () => { const p = past[past.length - 1]; if (!p) return; setPast(past.slice(0, -1)); setFuture([blocks, ...future]); onChange(p); setSaid("Undone."); };
  const redo = () => { const n = future[0]; if (!n) return; setFuture(future.slice(1)); setPast([...past, blocks]); onChange(n); setSaid("Redone."); };

  // live canvas: the server validates the unsaved document, resolves reusable components and returns css per breakpoint
  const body = useMemo(() => JSON.stringify({ site_id: siteId, locale, kind: kind === "PAGE" ? undefined : kind, doc: { blocks, ...(extraDoc ?? {}) } }), [blocks, siteId, locale, kind, extraDoc]);
  useEffect(() => {
    if (!siteId) return;
    const t = setTimeout(() => apiClient.post("/api/v1/cms-layout/preview", JSON.parse(body))
      .then((r) => setPrev({ blocks: r.data.blocks, theme: r.data.theme, warnings: r.data.warnings }))
      .catch((e) => setPrev((p) => ({ blocks: p?.blocks ?? [], theme: p?.theme as Theme, error: String(e?.response?.data?.detail ?? "Preview failed.") }))), 400);
    return () => clearTimeout(t);
  }, [body, siteId]);
  useEffect(() => {
    const root = canvas.current; if (!root) return;
    root.querySelectorAll<HTMLElement>("[data-block-id]").forEach((el) => { el.style.outline = el.dataset.blockId === sel ? "2px solid #4f46e5" : ""; el.style.outlineOffset = "-2px"; });
  });
  useEffect(() => { if (focusId.current) { tree.current?.querySelector<HTMLElement>(`[data-tree-id="${focusId.current}"]`)?.focus(); focusId.current = null; } });

  const selected = sel ? flat(blocks).find((b) => b.id === sel) ?? null : null;
  const setBlock = (b: Block, coalesce?: string) => { const t = structuredClone(blocks); const l = locate(t, b.id as string); if (!l) return; l.list[l.idx] = b; commit(t, coalesce ? `${b.id}:${coalesce}` : undefined); };

  const moveTo = (id: string, parentId: string | null, index: number) => {
    const t = structuredClone(blocks);
    const from = locate(t, id); if (!from) return;
    const node = from.list[from.idx];
    if (parentId && flat([node]).some((x) => x.id === parentId)) { setSaid("A block cannot go inside itself."); return; }
    const target = parentId ? locate(t, parentId)?.list[locate(t, parentId)!.idx] ?? null : null;
    if (parentId && !target) return;
    if (!accepts(target, node)) { setSaid(node.type === "column" ? "Columns can only go inside a row." : target?.type === "row" ? "A row holds columns only." : "That block cannot hold other blocks."); return; }
    const dest = target ? (target.children ??= []) : t;
    from.list.splice(from.idx, 1);
    const at = dest === from.list && from.idx < index ? index - 1 : index;
    dest.splice(Math.max(0, Math.min(at, dest.length)), 0, node);
    focusId.current = id; commit(t); setSaid(`Moved ${describe(node)}.`);
  };
  const step = (id: string, d: number) => { const l = locate(blocks, id); if (l && l.idx + d >= 0 && l.idx + d < l.list.length) moveTo(id, l.parent?.id ?? null, d > 0 ? l.idx + 2 : l.idx - 1); };
  const indent = (id: string) => { const l = locate(blocks, id); const p = l && l.idx > 0 ? l.list[l.idx - 1] : null; if (p && CONTAINERS.includes(p.type)) moveTo(id, p.id as string, (p.children ?? []).length); else setSaid("Cannot indent: the block above is not a container."); };
  const outdent = (id: string) => { const l = locate(blocks, id); if (!l?.parent) { setSaid("Already at the top level."); return; } const g = locate(blocks, l.parent.id as string); if (g) moveTo(id, g.parent?.id ?? null, g.idx + 1); };
  const remove = (id: string) => { const t = structuredClone(blocks); const l = locate(t, id); if (!l) return; const [x] = l.list.splice(l.idx, 1); setSel(null); commit(t); setSaid(`Removed ${describe(x)}. Undo is available.`); };

  const addBlock = () => {
    const t = structuredClone(blocks);
    const nb: Block = { type: add, id: newId(), ...(CONTAINERS.includes(add) ? { children: [] } : add === "faq" ? { items: [] } : add === "table" ? { columns: [] } : add === "columns" ? { left: [], right: [] } : {}) };
    if (add === "row") nb.children = [0, 1].map(() => ({ type: "column", id: newId(), style: { desktop: { span: 6 }, mobile: { span: 12 } }, children: [] }));
    const cur = sel ? locate(t, sel) : null;
    const node = cur ? cur.list[cur.idx] : null;
    let dest: Block[] = t, at = t.length;
    if (node && accepts(node, nb) && CONTAINERS.includes(node.type)) { dest = node.children ??= []; at = dest.length; }
    else if (cur && accepts(cur.parent, nb)) { dest = cur.list; at = cur.idx + 1; }
    else if (!accepts(null, nb)) { setSaid("Select a row first: columns go inside rows."); return; }
    dest.splice(at, 0, nb);
    setSel(nb.id as string); focusId.current = nb.id as string; commit(t); setSaid(`Added ${nb.type}.`);
  };

  const key = (e: React.KeyboardEvent, b: Block) => {
    const id = b.id as string;
    if (e.altKey && ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.key)) {
      e.preventDefault();
      if (e.key === "ArrowUp") step(id, -1); else if (e.key === "ArrowDown") step(id, 1); else if (e.key === "ArrowRight") indent(id); else outdent(id);
    } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      e.preventDefault();
      const items = Array.from(tree.current?.querySelectorAll<HTMLElement>("[data-tree-id]") ?? []);
      items[items.findIndex((x) => x.dataset.treeId === id) + (e.key === "ArrowDown" ? 1 : -1)]?.focus();
    } else if (e.key === "Delete") { e.preventDefault(); remove(id); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSel(id); }
  };
  const over = (e: React.DragEvent, b: Block) => {
    e.preventDefault(); e.stopPropagation();
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); const y = (e.clientY - r.top) / (r.height || 1);
    setDrop({ id: b.id as string, pos: y < 0.25 ? "before" : y > 0.75 || !CONTAINERS.includes(b.type) ? "after" : "inside" });
  };
  const dropOn = (e: React.DragEvent, b: Block) => {
    e.preventDefault(); e.stopPropagation();
    const d = drag, pos = drop?.pos ?? "after"; setDrag(null); setDrop(null);
    if (!d || d === b.id) return;
    if (pos === "inside") { moveTo(d, b.id as string, (b.children ?? []).length); return; }
    const l = locate(blocks, b.id as string); if (l) moveTo(d, l.parent?.id ?? null, pos === "before" ? l.idx : l.idx + 1);
  };

  const nodes = (bs: Block[], level: number): React.ReactNode => bs.map((b, i) => {
    const id = b.id as string;
    return <li key={id ?? i} role="none">
      <div role="treeitem" aria-level={level} aria-selected={sel === id} data-tree-id={id} tabIndex={sel === id || (!sel && level === 1 && i === 0) ? 0 : -1} draggable
        aria-label={`${describe(b)}, level ${level}`} onKeyDown={(e) => key(e, b)} onClick={() => setSel(id)}
        onDragStart={(e) => { e.stopPropagation(); e.dataTransfer.setData("text/plain", id); setDrag(id); }} onDragEnd={() => { setDrag(null); setDrop(null); }}
        onDragOver={(e) => over(e, b)} onDrop={(e) => dropOn(e, b)}
        className={`flex items-center gap-2 border rounded px-2 py-1 text-xs bg-white cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500 ${sel === id ? "border-indigo-500 bg-indigo-50" : ""} ${drag === id ? "opacity-50" : ""}
          ${drop?.id === id ? (drop.pos === "before" ? "border-t-4 border-t-indigo-500" : drop.pos === "after" ? "border-b-4 border-b-indigo-500" : "ring-2 ring-indigo-400") : ""}`} style={{ marginLeft: (level - 1) * 14 }}>
        <span aria-hidden className="cursor-move">⠿</span><b className="uppercase">{b.type}</b>
        <span className="text-gray-500 truncate">{String(b.text ?? b.title ?? b.label ?? b.name ?? b.key ?? "")}</span>
        {(b.hide ?? []).length > 0 && <span className="bg-gray-100 rounded px-1">hidden: {(b.hide as string[]).join(", ")}</span>}
        {b.audience && <span className="bg-amber-100 rounded px-1">audience</span>}
        {b.experiment && <span className="bg-sky-100 rounded px-1">test {b.experiment.key}:{b.experiment.variant}</span>}
      </div>
      {Array.isArray(b.children) && b.children.length > 0 && <ul role="group" className="space-y-1 mt-1">{nodes(b.children, level + 1)}</ul>}
    </li>;
  });

  const styleSel = (b: Block) => {
    if (!meta) return null;
    const applies = (p: string) => !meta.type_only[p] || meta.type_only[p].includes(b.type);
    const setStyle = (p: string, v: string) => {
      const style = structuredClone(b.style ?? {}); const cur = { ...(style[bp] ?? {}) };
      if (v === "") delete cur[p]; else cur[p] = /^\d+$/.test(v) && ["span", "cols"].includes(p) ? +v : v;
      if (Object.keys(cur).length) style[bp] = cur; else delete style[bp];
      setBlock({ ...b, style: Object.keys(style).length ? style : undefined });
    };
    return <>{GROUPS.map(([g, props]) => { const ps = props.filter((p) => applies(p) && meta.style[p]); return ps.length === 0 ? null : <fieldset key={g} className="border rounded p-2 text-xs sm:col-span-2"><legend>{g} — {bp}</legend>
      <div className="grid gap-1 grid-cols-2 sm:grid-cols-4">{ps.map((p) => <label key={p} className="block capitalize">{label(p)}
        <select aria-label={`${label(p)} (${bp})`} className="border rounded block w-full" value={String(b.style?.[bp]?.[p] ?? "")} onChange={(e) => setStyle(p, e.target.value)}>
          <option value="">{bp === "desktop" ? "default" : "inherit"}</option>{meta.style[p].map((v) => <option key={String(v)} value={String(v)}>{String(v)}</option>)}</select></label>)}</div></fieldset>; })}
      <fieldset className="border rounded p-2 text-xs sm:col-span-2"><legend>Visibility</legend><div className="flex gap-4">{BPS.map((x) =>
        <label key={x} className="flex items-center gap-1"><input type="checkbox" checked={!(b.hide ?? []).includes(x)} onChange={(e) => {
          const hide = BPS.filter((y) => (y === x ? !e.target.checked : (b.hide ?? []).includes(y))); setBlock({ ...b, hide: hide.length ? hide : undefined });
        }} />Show on {x}</label>)}</div></fieldset></>;
  };

  return (
    <div className="space-y-2" onKeyDown={(e) => {
      const el = e.target as HTMLElement; if (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName)) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); }
      else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); redo(); }
    }}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <label>Add <select aria-label="Block type" className="border rounded" value={add} onChange={(e) => setAdd(e.target.value)}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select></label>
        <button className="border rounded px-2 py-1" onClick={addBlock}>Add block</button>
        <button className="border rounded px-2 py-1" onClick={undo} disabled={!past.length} aria-label="Undo (Ctrl+Z)">Undo</button>
        <button className="border rounded px-2 py-1" onClick={redo} disabled={!future.length} aria-label="Redo (Ctrl+Y)">Redo</button>
        <span role="tablist" aria-label="Breakpoint" className="ml-auto flex gap-1">{BPS.map((x) =>
          <button key={x} role="tab" aria-selected={bp === x} className={`border rounded px-2 py-1 ${bp === x ? "bg-indigo-600 text-white" : ""}`} onClick={() => setBp(x)}>{x[0].toUpperCase() + x.slice(1)}</button>)}</span>
      </div>
      <p role="status" aria-live="polite" className="text-xs text-gray-600 min-h-4">{said}</p>
      <div className="grid gap-3 lg:grid-cols-[minmax(14rem,18rem)_1fr]">
        <div className="space-y-1">
          <p id="tree-help" className="text-xs text-gray-500">Drag to reorder or nest. Keyboard: arrows move focus, Alt+arrows move the block (Alt+Right nests it in the block above, Alt+Left lifts it out), Delete removes.</p>
          {blocks.length === 0 ? <p className="text-xs text-gray-500">No blocks yet. Add a section, row or text below.</p>
            : <ul role="tree" aria-label="Page structure" aria-describedby="tree-help" ref={tree} className="space-y-1">{nodes(blocks, 1)}</ul>}
          {selected && <div className="flex flex-wrap gap-1 text-xs" role="toolbar" aria-label={`Actions for ${describe(selected)}`}>
            <button className="border rounded px-2" onClick={() => step(selected.id as string, -1)}>Move up</button>
            <button className="border rounded px-2" onClick={() => step(selected.id as string, 1)}>Move down</button>
            <button className="border rounded px-2" onClick={() => indent(selected.id as string)}>Nest in block above</button>
            <button className="border rounded px-2" onClick={() => outdent(selected.id as string)}>Lift out</button>
            <button className="border rounded px-2 text-red-600" onClick={() => remove(selected.id as string)}>Remove</button></div>}
        </div>
        <div className="space-y-2">
          {siteId && <div>
            <div className="text-xs text-gray-500">Live preview — {bp}</div>
            {prev?.error && <p role="alert" className="text-xs text-red-700 bg-red-50 border rounded p-1">{prev.error}</p>}
            {(prev?.warnings ?? []).map((w, i) => <p key={i} className="text-xs text-amber-700">{w}</p>)}
            <div className="border rounded overflow-auto mx-auto bg-white" style={{ width: BP_WIDTH[bp], maxWidth: "100%", maxHeight: 420 }} ref={canvas}
              onClick={(e) => { const el = (e.target as HTMLElement).closest("[data-block-id]") as HTMLElement | null; e.preventDefault(); if (el?.dataset.blockId) setSel(el.dataset.blockId); }}>
              {prev?.theme ? <div style={{ background: prev.theme.background, color: prev.theme.text_color, fontFamily: prev.theme.font }} className="p-3">
                <CanvasContext.Provider value><BpContext.Provider value={bp}><SiteBlocks blocks={prev.blocks} theme={prev.theme} base="#" siteKey="preview" /></BpContext.Provider></CanvasContext.Provider></div>
                : <p className="p-3 text-xs text-gray-500">Preview loading…</p>}
            </div></div>}
          {selected && <div className="border rounded p-2 bg-white grid gap-2 sm:grid-cols-2" role="group" aria-label={`Properties of ${describe(selected)}`}>
            <b className="text-xs uppercase sm:col-span-2">{selected.type} properties</b>
            <One b={selected} set={(nb) => setBlock(nb, "content")} library={library} />
            {styleSel(selected)}
            <fieldset className="border rounded p-2 text-xs space-y-1 sm:col-span-2"><legend>Personalization &amp; testing</legend>
              <div className="grid gap-1 sm:grid-cols-4">
                <Field label="Lifecycle (e.g. CUSTOMER)" value={csv(selected.audience?.lifecycle)} onChange={(v) => setBlock({ ...selected, audience: { ...selected.audience, lifecycle: list(v) } }, "aud")} />
                <Field label="Audiences" value={csv(selected.audience?.segment)} onChange={(v) => setBlock({ ...selected, audience: { ...selected.audience, segment: list(v) } }, "aud")} />
                <Field label="Languages" value={csv(selected.audience?.locale)} onChange={(v) => setBlock({ ...selected, audience: { ...selected.audience, locale: list(v) } }, "aud")} />
                <label className="text-xs">Visitor<select aria-label="Known visitor" className="border rounded block w-full" value={selected.audience?.known === true ? "yes" : selected.audience?.known === false ? "no" : ""}
                  onChange={(e) => { const known = e.target.value === "yes" ? true : e.target.value === "no" ? false : undefined; const a = { ...selected.audience, known }; if (known === undefined) delete a.known; setBlock({ ...selected, audience: a }); }}>
                  <option value="">anyone</option><option value="yes">known (consented)</option><option value="no">anonymous</option></select></label>
                <Field label="Slot" value={selected.slot ?? ""} onChange={(v) => setBlock({ ...selected, slot: v || undefined }, "slot")} />
                <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={!!selected.fallback} onChange={(e) => setBlock({ ...selected, fallback: e.target.checked || undefined })} />Fallback for the slot</label>
                <Field label="Experiment key" value={selected.experiment?.key ?? ""} onChange={(v) => setBlock({ ...selected, experiment: v ? { key: v, variant: selected.experiment?.variant ?? "a" } : undefined }, "exp")} />
                <Field label="Variant" value={selected.experiment?.variant ?? ""} onChange={(v) => setBlock({ ...selected, experiment: selected.experiment ? { ...selected.experiment, variant: v } : undefined }, "exp")} />
              </div></fieldset>
          </div>}
        </div>
      </div>
    </div>
  );
}
