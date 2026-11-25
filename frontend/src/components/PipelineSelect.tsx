"use client";
// M43.S01.T011: choose a CRM pipeline (each has its own stages); CRM managers can add one.
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

export interface Pipeline { id: string; name: string; is_default: boolean; active_flag: boolean; record_type: string | null }

export function PipelineSelect({ value, onChange, allowCreate = false }: {
  value: string; onChange: (id: string) => void; allowCreate?: boolean;
}) {
  const [items, setItems] = useState<Pipeline[]>([]);
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const load = () => apiClient.get("/api/v1/crm/pipelines").then((r) => {
    setItems(r.data);
    if (!value && r.data.length) onChange((r.data.find((p: Pipeline) => p.is_default) ?? r.data[0]).id);
  }).catch(() => setItems([]));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <label className="text-xs text-gray-600">Pipeline
        <select className="ml-1 border rounded px-2 py-1 text-sm" value={value} onChange={(e) => onChange(e.target.value)}>
          {items.filter((p) => p.active_flag).map((p) => <option key={p.id} value={p.id}>{p.name}{p.is_default ? " (default)" : ""}</option>)}
        </select>
      </label>
      {allowCreate && (
        <form className="flex gap-1" onSubmit={async (e) => {
          e.preventDefault();
          try { const r = await apiClient.post("/api/v1/crm/pipelines", { name }); setName(""); setErr(null); await load(); onChange(r.data.id); }
          catch { setErr("Only CRM managers can add pipelines; names must be unique."); }
        }}>
          <input aria-label="New pipeline name" className="border rounded px-2 py-1 text-xs" placeholder="New pipeline…" value={name} onChange={(e) => setName(e.target.value)} />
          <button className="text-xs border rounded px-2" disabled={!name.trim()}>Add</button>
        </form>
      )}
      {err && <span className="text-xs text-red-600">{err}</span>}
    </div>
  );
}
