"use client";
// M44.S01.T001 visual e-mail designer: blocks, theme, live desktop/phone preview, accessibility warnings, versions.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type Block = { type: string; [k: string]: unknown };
interface Doc { theme: { brand_color: string; text_color: string; background: string; font: string }; blocks: Block[] }
interface Design { id: string; family_id: string; version: number; name: string; preheader: string | null; document: Doc; status: string; warnings: string[] }

const LIFECYCLE = ["SUBSCRIBER", "LEAD", "MQL", "SQL", "OPPORTUNITY", "CUSTOMER", "EVANGELIST"];  // smart content (M44.S01.T012)
const NEW: Record<string, Block> = {
  heading: { type: "heading", text: "Hello {first_name|there}", level: 1 },
  text: { type: "text", text: "Write your message. **Bold** works." },
  image: { type: "image", url: "https://", alt: "" },
  button: { type: "button", label: "Order now", href: "https://" },
  product: { type: "product", name: "POVU Synthetic 500 ml", size: "24 × 500 ml", price: "KES —" },
  divider: { type: "divider" },
  spacer: { type: "spacer", height: 16 },
  footer: { type: "footer", text: "POVU (synthetic sender address)" },
};
const BLANK: Doc = { theme: { brand_color: "#1D4ED8", text_color: "#111827", background: "#F3F4F6", font: "Arial, Helvetica, sans-serif" },
  blocks: [NEW.heading, NEW.text, NEW.button, NEW.footer] };
const FIELDS: Record<string, string[]> = { heading: ["text"], text: ["text"], image: ["url", "alt", "href"], button: ["label", "href"],
  product: ["name", "size", "price", "image_url"], spacer: ["height"], footer: ["text"], divider: [] };
const err = (e: unknown) => {
  let data = (e as { response?: { data?: unknown } }).response?.data;
  if (typeof data === "string") { try { data = JSON.parse(data); } catch { /* not JSON */ } }  // preview uses responseType text
  const d = (data as { detail?: unknown } | undefined)?.detail;
  return typeof d === "string" ? d : "Check the design.";
};

export default function EmailDesignerPage() {
  const [list, setList] = useState<Design[]>([]);
  const [cur, setCur] = useState<Design | null>(null);
  const [name, setName] = useState("New design");
  const [pre, setPre] = useState("");
  const [doc, setDoc] = useState<Doc>(BLANK);
  const [html, setHtml] = useState("");
  const [width, setWidth] = useState(600);
  const [warn, setWarn] = useState<string[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => { apiClient.get("/api/v1/email-designs").then((r) => setList(r.data)).catch(() => setList([])); }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const t = setTimeout(() => {
      apiClient.post("/api/v1/email-designs/preview", { name, preheader: pre, document: doc }, { responseType: "text" })
        .then((r) => { setHtml(r.data); setMsg(null); }).catch((e) => setMsg(err(e)));
    }, 400);
    return () => clearTimeout(t);
  }, [doc, name, pre]);
  const frozen = cur ? cur.status !== "DRAFT" : false;
  const set = (i: number, k: string, v: unknown) => setDoc({ ...doc, blocks: doc.blocks.map((b, j) => (j === i ? { ...b, [k]: v } : b)) });
  const move = (i: number, d: number) => { const b = [...doc.blocks]; const j = i + d; if (j < 0 || j >= b.length) return; [b[i], b[j]] = [b[j], b[i]]; setDoc({ ...doc, blocks: b }); };
  const open = (d: Design) => { setCur(d); setName(d.name); setPre(d.preheader ?? ""); setDoc(d.document); setWarn([]); };
  const save = async () => {
    try {
      const r = cur ? await apiClient.put(`/api/v1/email-designs/${cur.id}`, { name, preheader: pre, document: doc })
        : await apiClient.post("/api/v1/email-designs", { name, preheader: pre, document: doc });
      setCur(r.data); setWarn(r.data.warnings ?? []); setMsg("Saved."); load();
    } catch (e) { setMsg(err(e)); }
  };
  const act = async (path: string, ok: string) => { if (!cur) return; try { const r = await apiClient.post(`/api/v1/email-designs/${cur.id}/${path}`); if (r.data?.id) open(r.data); setMsg(r.data?.reason ? `Not sent: ${r.data.reason}` : ok); load(); } catch (e) { setMsg(err(e)); } };
  const input = "border rounded px-2 py-1 text-xs w-full";

  return (
    <div className="p-4 grid xl:grid-cols-[220px_1fr_auto] gap-4 text-sm">
      <aside className="space-y-1">
        <button className="text-xs text-indigo-600 underline" onClick={() => { setCur(null); setName("New design"); setPre(""); setDoc(BLANK); }}>+ New design</button>
        {list.map((d) => <button key={d.id} onClick={() => open(d)} className={`block w-full text-left text-xs border rounded px-2 py-1 ${cur?.id === d.id ? "bg-indigo-50" : "bg-white"}`}>{d.name} · v{d.version} · {d.status.toLowerCase()}</button>)}
      </aside>
      <section className="space-y-2">
        <div className="flex flex-wrap gap-2 items-center">
          <input aria-label="Design name" className="border rounded px-2 py-1" value={name} disabled={frozen} onChange={(e) => setName(e.target.value)} />
          <input aria-label="Preheader" className="border rounded px-2 py-1 flex-1" placeholder="Preheader (inbox preview text)" value={pre} disabled={frozen} onChange={(e) => setPre(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-3 text-xs items-center">
          {(["brand_color", "text_color", "background"] as const).map((k) => (
            <label key={k} className="flex items-center gap-1">{k.replace("_", " ")}<input type="color" disabled={frozen} value={doc.theme[k]} onChange={(e) => setDoc({ ...doc, theme: { ...doc.theme, [k]: e.target.value.toUpperCase() } })} /></label>))}
        </div>
        {doc.blocks.map((b, i) => (
          <div key={i} className="border rounded p-2 bg-white space-y-1">
            <div className="flex justify-between text-xs"><b>{b.type}</b>
              {!frozen && <span className="flex gap-2"><button aria-label="Move up" onClick={() => move(i, -1)}>↑</button><button aria-label="Move down" onClick={() => move(i, 1)}>↓</button>
                <button className="text-red-600" aria-label="Remove block" onClick={() => setDoc({ ...doc, blocks: doc.blocks.filter((_, j) => j !== i) })}>×</button></span>}
            </div>
            {(FIELDS[b.type] ?? []).map((k) => (k === "text" ?
              <textarea key={k} aria-label={k} className={input} rows={2} disabled={frozen} value={String(b[k] ?? "")} onChange={(e) => set(i, k, e.target.value)} /> :
              <input key={k} aria-label={k} className={input} placeholder={k} disabled={frozen} value={String(b[k] ?? "")} onChange={(e) => set(i, k, k === "height" ? +e.target.value : e.target.value)} />))}
            {b.type !== "footer" && <label className="flex items-center gap-2 text-xs text-gray-600">Show only to
              <select aria-label="Show block only to lifecycle stage" className="border rounded px-1 py-0.5" disabled={frozen}
                value={((b.audience as { lifecycle?: string[] } | undefined)?.lifecycle ?? [])[0] ?? ""}
                onChange={(e) => set(i, "audience", e.target.value ? { lifecycle: [e.target.value] } : undefined)}>
                <option value="">everyone</option>{LIFECYCLE.map((s) => <option key={s} value={s}>{s.toLowerCase()}</option>)}</select></label>}
          </div>))}
        {!frozen && <select aria-label="Add block" className="border rounded px-2 py-1 text-xs" value="" onChange={(e) => { if (e.target.value) setDoc({ ...doc, blocks: [...doc.blocks, { ...NEW[e.target.value] }] }); }}>
          <option value="">+ Add block…</option>{Object.keys(NEW).map((t) => <option key={t}>{t}</option>)}</select>}
        <div className="flex flex-wrap gap-2">
          {!frozen && <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={save}>Save draft</button>}
          {cur?.status === "DRAFT" && <button className="border rounded px-3 py-1 text-xs" onClick={() => act("publish", "Published; campaigns can use it now.")}>Publish</button>}
          {cur && cur.status !== "DRAFT" && <button className="border rounded px-3 py-1 text-xs" onClick={() => act("new-version", "New draft version.")}>New version</button>}
          {cur && <button className="border rounded px-3 py-1 text-xs" onClick={() => act("test-send", "Test queued to your own address.")}>Send me a test</button>}
        </div>
        {warn.map((w, i) => <p key={i} className="text-xs text-amber-700">⚠ {w}</p>)}
        {msg && <p role="status" className="text-xs">{msg}</p>}
      </section>
      <section className="space-y-1">
        <div className="flex gap-2 text-xs"><button className={width === 600 ? "font-bold" : ""} onClick={() => setWidth(600)}>Desktop</button><button className={width === 375 ? "font-bold" : ""} onClick={() => setWidth(375)}>Phone</button></div>
        <iframe title="E-mail preview" sandbox="" srcDoc={html} style={{ width, height: 640 }} className="border rounded bg-white max-w-full" />
      </section>
    </div>
  );
}
