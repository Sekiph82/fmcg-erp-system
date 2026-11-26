"use client";
// M47.S01.T010 configurable ticket pipelines: board per pipeline, move a ticket to a stage (sets the mapped status,
// pauses the SLA on "waiting" stages), and a small form to add a pipeline (service administrators).
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type Stage = { id: string; name: string; status: string; pauses_sla: boolean; tickets?: { id: string; ticket_no: string; priority: string }[] };
type Pipeline = { id: string; name: string; is_default: boolean; stages: Stage[] };
const STATUSES = ["OPEN", "IN_PROGRESS", "ESCALATED", "RESOLVED", "CLOSED"];
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Request failed."; };

export default function HelpdeskPipelinesPage() {
  const [list, setList] = useState<Pipeline[]>([]);
  const [sel, setSel] = useState<string>("");
  const [board, setBoard] = useState<Pipeline | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [stages, setStages] = useState<Stage[]>([{ id: "1", name: "New", status: "OPEN", pauses_sla: false }]);
  const loadBoard = useCallback((id: string) => id && apiClient.get(`/api/v1/helpdesk/pipelines/${id}/board`).then((r) => setBoard(r.data)).catch((e) => setMsg(err(e))), []);
  const load = useCallback(() => apiClient.get("/api/v1/helpdesk/pipelines").then((r) => {
    setList(r.data);
    const id = sel || r.data[0]?.id || "";
    setSel(id);
    loadBoard(id);
  }).catch((e) => setMsg(err(e))), [sel, loadBoard]);
  useEffect(() => { load(); }, [load]);
  const move = (ticketId: string, stageId: string) => apiClient.post(`/api/v1/helpdesk/${ticketId}/stage`, { stage_id: stageId })
    .then((r) => { setMsg(`Moved to ${r.data.stage} (${r.data.status}${r.data.sla_paused ? ", SLA paused" : ""}).`); loadBoard(sel); }).catch((e) => setMsg(err(e)));
  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">{tx("Ticket pipelines")}</h2>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      <select aria-label={tx("Pipeline")} className="border rounded px-2 py-1 text-xs" value={sel} onChange={(e) => { setSel(e.target.value); loadBoard(e.target.value); }}>
        {list.map((p) => <option key={p.id} value={p.id}>{p.name}{p.is_default ? tx(" (default)") : ""}</option>)}</select>
      {board && <div className="flex gap-3 overflow-x-auto">{board.stages.map((s) => (
        <div key={s.id} className="border rounded bg-white p-2 min-w-[180px]">
          <div className="font-medium text-xs">{s.name} <span className="text-gray-500">· {s.status}{s.pauses_sla ? tx(" · SLA paused") : ""}</span></div>
          <ul className="mt-2 space-y-1">{(s.tickets ?? []).map((t) => (
            <li key={t.id} className="border rounded p-1 text-xs flex items-center justify-between gap-1">
              <span>{t.ticket_no} · {t.priority}</span>
              <select aria-label={tx("Move {ticket_no}", { ticket_no: t.ticket_no })} className="border rounded text-xs" value={s.id} onChange={(e) => move(t.id, e.target.value)}>
                {board.stages.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</select>
            </li>))}</ul>
        </div>))}</div>}
      <form className="border rounded p-3 bg-white space-y-2 max-w-2xl" onSubmit={(e) => {
        e.preventDefault();
        apiClient.post("/api/v1/helpdesk/pipelines", { name, stages: stages.map(({ name: n, status, pauses_sla }) => ({ name: n, status, pauses_sla })) })
          .then(() => { setMsg(tx("Pipeline added.")); setName(""); load(); }).catch((x) => setMsg(err(x)));
      }}>
        <h3 className="font-semibold">{tx("Add a pipeline")}</h3>
        <input aria-label={tx("Pipeline name")} className="border rounded px-2 py-1 text-xs" required maxLength={100} placeholder={tx("e.g. Returns")} value={name} onChange={(e) => setName(e.target.value)} />
        {stages.map((s, i) => (
          <div key={s.id} className="flex gap-2 text-xs">
            <input aria-label={`Stage ${i + 1} name`} className="border rounded px-1" required maxLength={100} value={s.name} onChange={(e) => setStages(stages.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
            <select aria-label={`Stage ${i + 1} status`} className="border rounded px-1" value={s.status} onChange={(e) => setStages(stages.map((x, j) => j === i ? { ...x, status: e.target.value } : x))}>{STATUSES.map((st) => <option key={st}>{st}</option>)}</select>
            <label className="flex items-center gap-1"><input type="checkbox" checked={s.pauses_sla} onChange={(e) => setStages(stages.map((x, j) => j === i ? { ...x, pauses_sla: e.target.checked } : x))} />{tx("pauses SLA")}</label>
          </div>))}
        <div className="flex gap-2 text-xs">
          <button type="button" className="border rounded px-2" onClick={() => setStages([...stages, { id: String(Date.now()), name: "", status: "IN_PROGRESS", pauses_sla: false }])}>{tx("Add stage")}</button>
          <button className="border rounded px-2 bg-indigo-600 text-white">{tx("Save pipeline")}</button></div>
      </form>
    </div>
  );
}
