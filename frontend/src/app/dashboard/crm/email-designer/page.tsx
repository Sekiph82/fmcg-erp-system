"use client";
// M44.S01.T001 visual e-mail designer: blocks, theme, live desktop/phone preview, accessibility warnings, versions.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { SendApprovalsPanel } from "@/components/SendApprovalsPanel";
import { sendApprovalsApi, type SendPolicy } from "@/lib/send_approvals";
import { tx, lx } from "@/lib/i18n/core";

type Block = { type: string; [k: string]: unknown };
interface Doc { theme: { brand_color: string; text_color: string; background: string; font: string }; blocks: Block[] }
interface Design { id: string; family_id: string; version: number; name: string; preheader: string | null; document: Doc; status: string; warnings: string[] }

const LIFECYCLE = ["SUBSCRIBER", "LEAD", "MQL", "SQL", "OPPORTUNITY", "CUSTOMER", "EVANGELIST"];  // smart content (M44.S01.T012)
const NEW: Record<string, Block> = lx(() => ({
  heading: { type: "heading", text: tx("Hello {first_name|there}"), level: 1 },
  text: { type: "text", text: tx("Write your message. **Bold** works.") },
  image: { type: "image", url: "https://", alt: "" },
  button: { type: "button", label: tx("Order now"), href: "https://" },
  product: { type: "product", name: "POVU Synthetic 500 ml", size: "24 × 500 ml", price: "KES —" },
  divider: { type: "divider" },
  spacer: { type: "spacer", height: 16 },
  footer: { type: "footer", text: tx("POVU (synthetic sender address)") },
}));
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
  const [assets, setAssets] = useState<{ id: string; title: string; url: string }[]>([]);  // M45.S01.T024 asset library
  const load = useCallback(() => { apiClient.get("/api/v1/email-designs").then((r) => setList(r.data)).catch(() => setList([])); }, []);
  useEffect(() => { load(); apiClient.get("/api/v1/marketing-assets").then((r) => setAssets(r.data)).catch(() => setAssets([])); }, [load]);
  useEffect(() => {
    const t = setTimeout(() => {
      apiClient.post("/api/v1/email-designs/preview", { name, preheader: pre, document: doc }, { responseType: "text" })
        .then((r) => { setHtml(r.data); setMsg(null); }).catch((e) => setMsg(err(e)));
    }, 400);
    return () => clearTimeout(t);
  }, [doc, name, pre]);
  const frozen = cur ? cur.status !== "DRAFT" : false;
  const set = (i: number, k: string, v: unknown) => setDoc({ ...doc, blocks: doc.blocks.map((b, j) => (j === i ? { ...b, [k]: v } : b)) });
  const [dragFrom, setDragFrom] = useState<number | null>(null);   // M47.S01.T011 drag-and-drop (buttons stay for keyboard users)
  const moveTo = (from: number, to: number) => { if (from === to) return; const b = [...doc.blocks]; const [x] = b.splice(from, 1); b.splice(to, 0, x); setDoc({ ...doc, blocks: b }); };
  const move = (i: number, d: number) => { const b = [...doc.blocks]; const j = i + d; if (j < 0 || j >= b.length) return; [b[i], b[j]] = [b[j], b[i]]; setDoc({ ...doc, blocks: b }); };
  const open = (d: Design) => { setCur(d); setName(d.name); setPre(d.preheader ?? ""); setDoc(d.document); setWarn([]); };
  const save = async () => {
    try {
      const r = cur ? await apiClient.put(`/api/v1/email-designs/${cur.id}`, { name, preheader: pre, document: doc })
        : await apiClient.post("/api/v1/email-designs", { name, preheader: pre, document: doc });
      setCur(r.data); setWarn(r.data.warnings ?? []); setMsg(tx("Saved.")); load();
    } catch (e) { setMsg(err(e)); }
  };
  const act = async (path: string, ok: string) => { if (!cur) return; try { const r = await apiClient.post(`/api/v1/email-designs/${cur.id}/${path}`); if (r.data?.id) open(r.data); setMsg(r.data?.reason ? tx("Not sent: {reason}", { reason: r.data.reason }) : ok); load(); } catch (e) { setMsg(err(e)); } };
  const input = "border rounded px-2 py-1 text-xs w-full";

  return (
    <div className="p-4 grid xl:grid-cols-[220px_1fr_auto] gap-4 text-sm">
      <aside className="space-y-1">
        <button className="text-xs text-indigo-600 underline" onClick={() => { setCur(null); setName("New design"); setPre(""); setDoc(BLANK); }}>{tx("+ New design")}</button>
        {list.map((d) => <button key={d.id} onClick={() => open(d)} className={`block w-full text-left text-xs border rounded px-2 py-1 ${cur?.id === d.id ? "bg-indigo-50" : "bg-white"}`}>{d.name} {tx("· v")}{d.version} · {d.status.toLowerCase()}</button>)}
      </aside>
      <section className="space-y-2">
        <div className="flex flex-wrap gap-2 items-center">
          <input aria-label={tx("Design name")} className="border rounded px-2 py-1" value={name} disabled={frozen} onChange={(e) => setName(e.target.value)} />
          <input aria-label={tx("Preheader")} className="border rounded px-2 py-1 flex-1" placeholder={tx("Preheader (inbox preview text)")} value={pre} disabled={frozen} onChange={(e) => setPre(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-3 text-xs items-center">
          {(["brand_color", "text_color", "background"] as const).map((k) => (
            <label key={k} className="flex items-center gap-1">{k.replace("_", " ")}<input type="color" disabled={frozen} value={doc.theme[k]} onChange={(e) => setDoc({ ...doc, theme: { ...doc.theme, [k]: e.target.value.toUpperCase() } })} /></label>))}
        </div>
        {doc.blocks.map((b, i) => (
          <div key={i} className={`border rounded p-2 bg-white space-y-1 ${dragFrom === i ? "opacity-50" : ""}`} draggable={!frozen}
            onDragStart={() => setDragFrom(i)} onDragOver={(e) => e.preventDefault()} onDragEnd={() => setDragFrom(null)}
            onDrop={(e) => { e.preventDefault(); if (dragFrom !== null) moveTo(dragFrom, i); setDragFrom(null); }}>
            <div className="flex justify-between text-xs"><b className={frozen ? "" : "cursor-move"} title={frozen ? undefined : tx("Drag to reorder")}>⠿ {b.type}</b>
              {!frozen && <span className="flex gap-2"><button aria-label={tx("Move up")} onClick={() => move(i, -1)}>↑</button><button aria-label={tx("Move down")} onClick={() => move(i, 1)}>↓</button>
                <button className="text-red-600" aria-label={tx("Remove block")} onClick={() => setDoc({ ...doc, blocks: doc.blocks.filter((_, j) => j !== i) })}>×</button></span>}
            </div>
            {(FIELDS[b.type] ?? []).map((k) => (k === "text" ?
              <textarea key={k} aria-label={k} className={input} rows={2} disabled={frozen} value={String(b[k] ?? "")} onChange={(e) => set(i, k, e.target.value)} /> :
              <input key={k} aria-label={k} className={input} placeholder={k} disabled={frozen} value={String(b[k] ?? "")} onChange={(e) => set(i, k, k === "height" ? +e.target.value : e.target.value)} />))}
            {b.type === "image" && !frozen && assets.length > 0 && <select aria-label={tx("Pick image from asset library")} className={input} value=""
              onChange={(e) => { const a = assets.find((x) => x.id === e.target.value); if (a) setDoc({ ...doc, blocks: doc.blocks.map((x, j) => (j === i ? { ...x, url: a.url, alt: x.alt || a.title } : x)) }); }}>
              <option value="">{tx("Pick from asset library…")}</option>{assets.map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}</select>}
            {b.type !== "footer" && <label className="flex items-center gap-2 text-xs text-gray-600">{tx("Show only to")}
              <select aria-label={tx("Show block only to lifecycle stage")} className="border rounded px-1 py-0.5" disabled={frozen}
                value={((b.audience as { lifecycle?: string[] } | undefined)?.lifecycle ?? [])[0] ?? ""}
                onChange={(e) => set(i, "audience", { ...((b.audience as object) ?? {}), lifecycle: e.target.value ? [e.target.value] : undefined })}>
                <option value="">{tx("everyone")}</option>{LIFECYCLE.map((s) => <option key={s} value={s}>{s.toLowerCase()}</option>)}</select>
              <select aria-label={tx("Show block only to language")} className="border rounded px-1 py-0.5" disabled={frozen}
                value={((b.audience as { language?: string[] } | undefined)?.language ?? [])[0] ?? ""}
                onChange={(e) => set(i, "audience", { ...((b.audience as object) ?? {}), language: e.target.value ? [e.target.value] : undefined })}>
                <option value="">{tx("any language")}</option><option value="en">{tx("English")}</option><option value="sw">{tx("Swahili")}</option></select></label>}
          </div>))}
        {!frozen && <select aria-label={tx("Add block")} className="border rounded px-2 py-1 text-xs" value="" onChange={(e) => { if (e.target.value) setDoc({ ...doc, blocks: [...doc.blocks, { ...NEW[e.target.value] }] }); }}>
          <option value="">{tx("+ Add block…")}</option>{Object.keys(NEW).map((t) => <option key={t}>{t}</option>)}</select>}
        <div className="flex flex-wrap gap-2">
          {!frozen && <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={save}>{tx("Save draft")}</button>}
          {cur?.status === "DRAFT" && <button className="border rounded px-3 py-1 text-xs" onClick={() => act("publish", "Published; campaigns can use it now.")}>{tx("Publish")}</button>}
          {cur && cur.status !== "DRAFT" && <button className="border rounded px-3 py-1 text-xs" onClick={() => act("new-version", "New draft version.")}>{tx("New version")}</button>}
          {cur && <button className="border rounded px-3 py-1 text-xs" onClick={() => act("test-send", "Test queued to your own address.")}>{tx("Send me a test")}</button>}
        </div>
        {cur?.status === "PUBLISHED" && <SingleSend design={cur} />}
        {warn.map((w, i) => <p key={i} className="text-xs text-amber-700">⚠ {w}</p>)}
        {msg && <p role="status" className="text-xs">{msg}</p>}
      </section>
      <section className="space-y-1">
        <div className="flex gap-2 text-xs"><button className={width === 600 ? "font-bold" : ""} onClick={() => setWidth(600)}>{tx("Desktop")}</button><button className={width === 375 ? "font-bold" : ""} onClick={() => setWidth(375)}>{tx("Phone")}</button></div>
        <iframe title={tx("E-mail preview")} sandbox="" srcDoc={html} style={{ width, height: 640 }} className="border rounded bg-white max-w-full" />
      </section>
    </div>
  );
}

// M48.S01.T023 single send of a published design: marketing consent applies; daily cap and, when switched on, approval
// of this exact send by a second editor.
function SingleSend({ design }: { design: Design }) {
  const [f, setF] = useState({ to_email: "", subject: "", contact_name: "", company_name: "", track_engagement: false });
  const [approvalId, setApprovalId] = useState<string | null>(null);
  const [policy, setPolicy] = useState<SendPolicy | null>(null);
  const [key, setKey] = useState(0);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const values: Record<string, string> = {};
  if (f.contact_name) { values.contact_name = f.contact_name; values.first_name = f.contact_name.split(" ")[0]; }
  if (f.company_name) values.company_name = f.company_name;
  const body = { to_email: f.to_email.trim(), subject: f.subject, values, track_engagement: f.track_engagement };
  const contentReason = !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(body.to_email) ? "Enter the recipient's e-mail address."
    : !f.subject.trim() ? "Enter a subject." : /[\r\n]/.test(f.subject) ? "The subject must be one line." : null;
  const capReason = policy && policy.used_today >= policy.daily_cap ? `Daily limit reached (${policy.used_today} of ${policy.daily_cap} direct marketing sends today).` : null;
  const approvalReason = policy?.approval_required && !approvalId ? "Approval required: request it, have a second editor approve, then pick the approval below." : null;
  const sendReason = contentReason ?? capReason ?? approvalReason;
  const change = (k: keyof typeof f, v: string | boolean) => { setF({ ...f, [k]: v }); setApprovalId(null); };
  const send = async () => {
    try {
      const r = await apiClient.post<{ status: string; reason: string | null }>(`/api/v1/email-designs/${design.id}/send`, { ...body, approval_id: approvalId });
      setMsg({ ok: r.data.status !== "SUPPRESSED", text: r.data.status === "SUPPRESSED" ? `Not sent: ${r.data.reason ?? "suppressed"}` : `Queued (${r.data.status.toLowerCase()}).` });
    } catch (e) { setMsg({ ok: false, text: err(e) }); }
    setApprovalId(null); setKey((k) => k + 1);
  };
  const request = async () => {
    try { await sendApprovalsApi.requestDesign(design.id, body); setMsg({ ok: true, text: tx("Approval requested; another editor must approve it.") }); }
    catch (e) { setMsg({ ok: false, text: err(e) }); }
    setKey((k) => k + 1);
  };
  const box = "border rounded px-2 py-1 text-xs";
  return (
    <div className="border rounded p-2 space-y-2 bg-white">
      <p className="font-medium text-xs">{tx("Send this design to one contact (marketing mail: consent and suppression apply)")}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <input aria-label={tx("Recipient e-mail")} placeholder={tx("Recipient e-mail")} className={box} value={f.to_email} onChange={(e) => change("to_email", e.target.value)} />
        <input aria-label={tx("Send subject")} placeholder={tx("Subject")} className={box} value={f.subject} onChange={(e) => change("subject", e.target.value)} />
        <input aria-label={tx("Contact name")} placeholder={tx("Contact name (optional)")} className={box} value={f.contact_name} onChange={(e) => change("contact_name", e.target.value)} />
        <input aria-label={tx("Company name")} placeholder={tx("Company name (optional)")} className={box} value={f.company_name} onChange={(e) => change("company_name", e.target.value)} />
      </div>
      <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={f.track_engagement} onChange={(e) => change("track_engagement", e.target.checked)} />{tx("Track opens and clicks")}</label>
      <div className="flex flex-wrap gap-2 items-center">
        <button disabled={!!sendReason} title={sendReason ?? undefined} onClick={send} className="bg-indigo-600 text-white rounded px-3 py-1 text-xs disabled:opacity-50">{approvalId ? tx("Send with approval") : tx("Send")}</button>
        <button disabled={!!contentReason} title={contentReason ?? undefined} onClick={request} className="border rounded px-3 py-1 text-xs disabled:opacity-50">{tx("Request approval")}</button>
        {sendReason && <span className="text-xs text-amber-700">{sendReason}</span>}
      </div>
      {msg && <p role="status" className={`text-xs ${msg.ok ? "text-emerald-700" : "text-red-700"}`}>{msg.text}</p>}
      <SendApprovalsPanel kind="design" targetId={design.id} picked={approvalId} onPick={setApprovalId} refresh={key} onPolicy={setPolicy} />
    </div>
  );
}
