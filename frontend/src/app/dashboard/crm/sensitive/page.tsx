"use client";
// M45.S01.T017 sensitive-data classification: which fields are masked for users without data.view_sensitive,
// retention, and an audited reveal for one value.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

type F = { entity: string; field: string; sensitive: boolean; retention_days: number | null };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

export default function SensitivePage() {
  const [pol, setPol] = useState<{ can_view: boolean; fields: F[] } | null>(null);
  const [rev, setRev] = useState({ entity: "customer", record_id: "", field: "tax_id" });
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/sensitive-data/policy").then((r) => setPol(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const set = (f: F, patch: Partial<F>) => apiClient.put("/api/v1/sensitive-data/policy", { entity: f.entity, field: f.field, sensitive: patch.sensitive ?? f.sensitive, retention_days: patch.retention_days === undefined ? f.retention_days : patch.retention_days })
    .then(() => { setMsg("Saved."); load(); }).catch((e) => setMsg(err(e)));
  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">Sensitive data</h2>
      <p className="text-xs text-gray-500">Classified fields are masked in screens, the API and exports for anyone without the &quot;View sensitive data&quot; right. Custom fields use their own &quot;sensitive&quot; flag. Every reveal is audited.{pol ? ` You ${pol.can_view ? "can" : "cannot"} see them.` : ""}</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {pol && <table className="text-xs bg-white border w-full max-w-2xl"><thead><tr className="bg-gray-50 text-left"><th className="p-1">Record</th><th>Field</th><th>Sensitive</th><th>Clear after inactive (days)</th></tr></thead>
        <tbody>{pol.fields.map((f) => <tr key={f.entity + f.field} className="border-t"><td className="p-1">{f.entity}</td><td>{f.field}</td>
          <td><input type="checkbox" aria-label={`${f.entity} ${f.field} sensitive`} checked={f.sensitive} onChange={(e) => set(f, { sensitive: e.target.checked })} /></td>
          <td><input aria-label={`${f.entity} ${f.field} retention`} type="number" min={30} className="border rounded px-1 w-24" defaultValue={f.retention_days ?? ""} onBlur={(e) => set(f, { retention_days: e.target.value ? +e.target.value : null })} /></td></tr>)}</tbody></table>}
      <section className="border rounded p-3 bg-white space-y-2 max-w-2xl"><h3 className="font-semibold">Reveal one value</h3>
        <div className="flex flex-wrap gap-2 text-xs"><select aria-label="Record type" className="border rounded px-1" value={rev.entity} onChange={(e) => setRev({ ...rev, entity: e.target.value })}><option>customer</option><option>contact</option></select>
          <input aria-label="Record id" className="border rounded px-1 w-72" placeholder="record id" value={rev.record_id} onChange={(e) => setRev({ ...rev, record_id: e.target.value })} />
          <input aria-label="Field" className="border rounded px-1 w-28" value={rev.field} onChange={(e) => setRev({ ...rev, field: e.target.value })} />
          <button className="border rounded px-2" onClick={() => apiClient.post("/api/v1/sensitive-data/reveal", rev).then((r) => setMsg(`Value: ${r.data.value ?? "(empty)"} (this reveal was logged)`)).catch((e) => setMsg(err(e)))}>Reveal</button></div></section>
    </div>
  );
}
