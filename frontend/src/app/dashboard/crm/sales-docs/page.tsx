"use client";
// M45.S01.T013 sales document library: approved catalogues/proposals, share links with expiry, views and downloads.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Doc = { id: string; title: string; version: number; status: string; file_name: string | null; scan: string; links: number };
type Link = { id: string; label: string | null; pin_version: boolean; expires_at: string; revoked: boolean; views: number; downloads: number; last_activity: string | null };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : tx("Something went wrong."); };

export default function SalesDocsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [cur, setCur] = useState<Doc | null>(null);
  const [links, setLinks] = useState<Link[]>([]);
  const [form, setForm] = useState({ days: 14, label: "", pin_version: false });
  const [url, setUrl] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/sales-docs").then((r) => setDocs(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const open = (d: Doc) => { setCur(d); setUrl(null); apiClient.get(`/api/v1/sales-docs/${d.id}/links`).then((r) => setLinks(r.data)).catch(() => setLinks([])); };
  const share = () => cur && apiClient.post(`/api/v1/sales-docs/${cur.id}/share`, { ...form, label: form.label || null }).then((r) => { setUrl(r.data.url); open(cur); load(); }).catch((e) => setMsg(err(e)));
  const revoke = (id: string) => apiClient.post(`/api/v1/sales-docs/links/${id}/revoke`).then(() => cur && open(cur)).catch((e) => setMsg(err(e)));
  return (
    <div className="p-4 space-y-3 text-sm">
      <h2 className="text-lg font-semibold">{tx("Sales documents")}</h2>
      <p className="text-xs text-gray-500">{tx("Upload and approve documents in Documents with the category \"Sales document\". Only approved files that passed the malware scan can be downloaded by customers.")}</p>
      {msg && <p role="status" className="text-xs text-red-600">{msg}</p>}
      <ul className="divide-y bg-white border rounded">{docs.length === 0 ? <li className="p-2 text-xs text-gray-500">{tx("No sales documents yet.")}</li> : docs.map((d) =>
        <li key={d.id} className={`p-2 text-xs flex flex-wrap justify-between gap-2 cursor-pointer ${cur?.id === d.id ? "bg-indigo-50" : ""}`} onClick={() => open(d)}>
          <span><b>{d.title}</b> {tx("v")}{d.version} · {d.status.toLowerCase()} · {d.file_name ?? tx("no file")}</span><span>{tx("scan")} {d.scan.toLowerCase().replace("_", " ")} · {d.links} {tx("links")}</span></li>)}</ul>
      {cur && <section className="border rounded p-3 bg-white space-y-2">
        <h3 className="font-semibold">{cur.title}</h3>
        <div className="flex flex-wrap gap-2 items-end text-xs">
          <label>{tx("Days")}<input aria-label={tx("Days valid")} type="number" min={1} max={90} className="border rounded px-1 block w-16" value={form.days} onChange={(e) => setForm({ ...form, days: +e.target.value })} /></label>
          <label>{tx("For")}<input aria-label={tx("Shared with")} className="border rounded px-1 block" placeholder={tx("e.g. Duka Moja buyer")} value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} /></label>
          <label className="flex items-center gap-1"><input type="checkbox" checked={form.pin_version} onChange={(e) => setForm({ ...form, pin_version: e.target.checked })} />{tx("Keep this version (otherwise always the newest approved)")}</label>
          <button className="bg-indigo-600 text-white rounded px-3 py-1" onClick={share}>{tx("Create link")}</button></div>
        {url && <p className="text-xs break-all bg-amber-50 border rounded p-2">{tx("Send this link (shown once):")} <b>{url}</b></p>}
        <ul className="text-xs divide-y">{links.map((l) => <li key={l.id} className="py-1 flex flex-wrap justify-between gap-2">
          <span>{l.label ?? tx("link")} · {l.views} {tx("views ·")} {l.downloads} {tx("downloads")}{l.last_activity ? tx(" · last {date}", { date: new Date(l.last_activity).toLocaleString() }) : ""} · {l.revoked ? tx("withdrawn") : tx("until {date}", { date: new Date(l.expires_at).toLocaleDateString() })}{l.pin_version ? tx(" · pinned") : ""}</span>
          {!l.revoked && <button className="text-red-600 underline" onClick={() => revoke(l.id)}>{tx("Withdraw")}</button>}</li>)}</ul>
      </section>}
    </div>
  );
}
