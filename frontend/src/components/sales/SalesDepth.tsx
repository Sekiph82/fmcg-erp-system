"use client";
// M47.S01.T009 sales depth controls for the workspace: task calendar sync, 1-to-1 video messages, trained deal-win model.
import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : tx("Something went wrong."); };

export function TaskCalendarSync() {
  const [msg, setMsg] = useState<string | null>(null);
  const run = () => apiClient.post("/api/v1/crm-workspace/tasks/calendar-sync").then((r) => {
    const { status, detail, ...counts } = r.data;
    setMsg(status === "SYNCED" ? tx("Calendar updated: {counts}.", { counts: Object.entries(counts).map(([k, v]) => `${v} ${String(k).toLowerCase()}`).join(", ") || "no open tasks with a due time" })
      : status === "NOT_CONFIGURED" ? tx("Not configured: {detail}", { detail }) : tx("Pending: {detail}", { detail }));
  }).catch((e) => setMsg(err(e)));
  return (
    <div className="border rounded bg-white p-2 text-xs space-y-1">
      <div className="flex items-center gap-2"><b>{tx("Tasks in my calendar")}</b><button className="border rounded px-2" onClick={run}>{tx("Sync now")}</button></div>
      <p className="text-gray-500">{tx("Open tasks with a due time go to your connected Google/Outlook calendar (also every 5 minutes); done or deleted tasks are removed.")}</p>
      {msg && <p role="status">{msg}</p>}
    </div>
  );
}

type Video = { id: string; title: string; contact_email: string; expires_at: string; revoked: boolean; views: number };

export function VideoMessages({ recordId }: { recordId?: string | null }) {
  const [rows, setRows] = useState<Video[]>([]);
  const [form, setForm] = useState({ title: "", contact_email: "", contact_name: "", customer_id: "", days: 14 });
  const [file, setFile] = useState<Blob | null>(null);
  const [recording, setRecording] = useState(false);
  const [link, setLink] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const load = useCallback(() => { apiClient.get("/api/v1/sales-depth/videos").then((r) => setRows(r.data)).catch(() => setRows([])); }, []);
  useEffect(() => { load(); }, [load]);
  const record = async () => {
    if (recording) { rec.current?.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      const chunks: Blob[] = [];
      const r = new MediaRecorder(stream, { mimeType: "video/webm" });
      r.ondataavailable = (e) => chunks.push(e.data);
      r.onstop = () => { stream.getTracks().forEach((t) => t.stop()); setFile(new Blob(chunks, { type: "video/webm" })); setRecording(false); };
      rec.current = r;
      r.start();
      setRecording(true);
    } catch { setMsg(tx("The camera is not available in this browser; upload a file instead.")); }
  };
  const send = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { setMsg(tx("Record or choose a video first.")); return; }
    const f = new FormData();
    f.append("file", file, file instanceof File ? file.name : "message.webm");
    Object.entries(form).forEach(([k, v]) => { if (v !== "") f.append(k, String(v)); });
    if (recordId) f.append("crm_record_id", recordId);
    apiClient.post("/api/v1/sales-depth/videos", f).then((r) => { setLink(r.data.url); setMsg(tx("Link created. Copy it now; it is shown once.")); load(); }).catch((x) => setMsg(err(x)));
  };
  return (
    <div className="border rounded bg-white p-2 text-xs space-y-1">
      <b>{tx("Video message")}</b>
      <form className="space-y-1" onSubmit={send}>
        <input required className="border rounded px-2 py-1 w-full" placeholder={tx("Title")} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <input required type="email" className="border rounded px-2 py-1 w-full" placeholder={tx("Contact e-mail")} value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
        <input className="border rounded px-2 py-1 w-full" placeholder={tx("Contact name (optional)")} value={form.contact_name} onChange={(e) => setForm({ ...form, contact_name: e.target.value })} />
        <input className="border rounded px-2 py-1 w-full" placeholder={tx("Customer id (for the timeline, optional)")} value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} />
        <label className="flex gap-1 items-center">{tx("Valid for")} <input type="number" min={1} max={60} className="border rounded w-14 px-1" value={form.days} onChange={(e) => setForm({ ...form, days: Number(e.target.value) })} /> {tx("days")}</label>
        <div className="flex gap-2 items-center">
          <button type="button" className="border rounded px-2" onClick={record}>{recording ? tx("Stop recording") : tx("Record")}</button>
          <input type="file" accept="video/mp4,video/webm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </div>
        {file && <p className="text-gray-500">{tx("Video ready (")}{Math.round(file.size / 1024)} {tx("KB).")}</p>}
        <button className="border rounded px-2 py-1">{tx("Create link")}</button>
      </form>
      {msg && <p role="status">{msg}</p>}
      {link && <input readOnly className="border rounded px-2 py-1 w-full" value={link} onFocus={(e) => e.target.select()} />}
      <ul className="divide-y">{rows.map((v) => (
        <li key={v.id} className="py-1 flex justify-between gap-2"><span>{v.title} → {v.contact_email} · {v.views} {tx("view(s)")}{v.revoked ? tx(" · withdrawn") : tx(" · until {date}", { date: new Date(v.expires_at).toLocaleDateString() })}</span>
          {!v.revoked && <button className="text-red-600" onClick={() => apiClient.post(`/api/v1/sales-depth/videos/${v.id}/revoke`).then(load).catch((x) => setMsg(err(x)))}>{tx("Withdraw")}</button>}</li>))}</ul>
    </div>
  );
}

type Win = { rule_score: number; trained: { status: string; probability: number | null; label?: string; model_version?: number; metrics?: Record<string, unknown> } };

export function DealWin({ recordId }: { recordId?: string | null }) {
  const [model, setModel] = useState<{ status: string; version?: number; metrics?: Record<string, unknown>; min_per_class?: number } | null>(null);
  const [win, setWin] = useState<Win | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => { apiClient.get("/api/v1/sales-depth/deal-model").then((r) => setModel(r.data)).catch(() => setModel(null)); }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    setWin(null);
    if (recordId) apiClient.get(`/api/v1/sales-depth/records/${recordId}/win`).then((r) => setWin(r.data)).catch(() => setWin(null));
  }, [recordId, model]);
  const train = () => apiClient.post("/api/v1/sales-depth/deal-model/train").then((r) => { setMsg(r.data.trained ? tx("Model v{version} trained.", { version: r.data.version }) : r.data.reason); load(); }).catch((e) => setMsg(err(e)));
  const m = model?.metrics as { auc?: number | null; accuracy?: number; n_train?: number; n_holdout?: number; note?: string } | undefined;
  return (
    <div className="border rounded bg-white p-2 text-xs space-y-1">
      <div className="flex items-center gap-2"><b>{tx("Deal-win model")}</b><button className="border rounded px-2" onClick={train}>{tx("Train")}</button></div>
      {model?.status === "TRAINED" && m ? <p>{tx("v")}{model.version}{tx(": holdout AUC")} {m.auc ?? tx("n/a")}{tx(", accuracy")} {m.accuracy}{tx(", trained on")} {m.n_train}{tx(", tested on")} {m.n_holdout}. <span className="text-gray-500">{m.note}</span></p>
        : <p className="text-gray-500">{tx("Not enough data: needs")} {model?.min_per_class ?? 10} {tx("won and")} {model?.min_per_class ?? 10} {tx("lost deals. Rule score only.")}</p>}
      {msg && <p role="status">{msg}</p>}
      {win && <p>{tx("Selected deal: rule score")} <b>{win.rule_score}</b> {tx("· trained probability")} {win.trained.probability != null
        ? <b>{Math.round(win.trained.probability * 100)}{tx("% (model v")}{win.trained.model_version})</b> : <span className="text-gray-500">{win.trained.label}</span>}</p>}
    </div>
  );
}
