"use client";
// M45.S01.T017 sensitive-data classification: which fields are masked for users without data.view_sensitive,
// retention, and an audited reveal for one value.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type F = { entity: string; field: string; sensitive: boolean; retention_days: number | null };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : "Something went wrong."; };

// M47.S01.T010 field-level permissions: role → field → hidden / read-only (superusers and roles.manage are exempt)
type Rule = { id: string; entity: string; role_name: string; field_key: string; access: string };
type FP = { rules: Rule[]; roles: string[]; entities: { entity: string; fields: string[] }[] };

function FieldPermissions() {
  const [fp, setFp] = useState<FP | null>(null);
  const [f, setF] = useState({ entity: "contact", role_name: "", field_key: "", access: "HIDDEN" });
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/platform-depth/field-permissions").then((r) => setFp(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const fields = fp?.entities.find((e) => e.entity === f.entity)?.fields ?? [];
  return (
    <section className="border rounded p-3 bg-white space-y-2 max-w-2xl"><h3 className="font-semibold">{tx("Field permissions by role")}</h3>
      <p className="text-xs text-gray-500">{tx("Hidden fields are removed from screens and the API for that role; read-only fields are shown but cannot be changed. For contacts any contact property key can be used too. Several roles: the strictest rule wins.")}</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {fp && <form className="flex flex-wrap gap-2 text-xs" onSubmit={(e) => { e.preventDefault(); apiClient.put("/api/v1/platform-depth/field-permissions", f).then(() => { setMsg(tx("Saved.")); load(); }).catch((x) => setMsg(err(x))); }}>
        <select aria-label={tx("Record type")} className="border rounded px-1" value={f.entity} onChange={(e) => setF({ ...f, entity: e.target.value, field_key: "" })}>{fp.entities.map((e) => <option key={e.entity}>{e.entity}</option>)}</select>
        <select aria-label={tx("Role")} className="border rounded px-1" required value={f.role_name} onChange={(e) => setF({ ...f, role_name: e.target.value })}><option value="">{tx("role…")}</option>{fp.roles.map((r) => <option key={r}>{r}</option>)}</select>
        <input aria-label={tx("Field key")} list="fp-fields" className="border rounded px-1 w-32" required placeholder={tx("field")} value={f.field_key} onChange={(e) => setF({ ...f, field_key: e.target.value })} />
        <datalist id="fp-fields">{fields.map((k) => <option key={k} value={k} />)}</datalist>
        <select aria-label={tx("Access")} className="border rounded px-1" value={f.access} onChange={(e) => setF({ ...f, access: e.target.value })}><option value="HIDDEN">{tx("Hidden")}</option><option value="READ_ONLY">{tx("Read-only")}</option></select>
        <button className="border rounded px-2">{tx("Save rule")}</button></form>}
      {fp && <table className="text-xs w-full"><tbody>{fp.rules.map((r) => <tr key={r.id} className="border-t"><td className="p-1">{r.entity}</td><td>{r.role_name}</td><td>{r.field_key}</td><td>{r.access}</td>
        <td><button className="underline text-red-600" onClick={() => apiClient.delete(`/api/v1/platform-depth/field-permissions/${r.id}`).then(load).catch((x) => setMsg(err(x)))}>{tx("Remove")}</button></td></tr>)}</tbody></table>}
    </section>
  );
}

export default function SensitivePage() {
  const [pol, setPol] = useState<{ can_view: boolean; fields: F[] } | null>(null);
  const [rev, setRev] = useState({ entity: "customer", record_id: "", field: "tax_id" });
  const [msg, setMsg] = useState<string | null>(null);
  const load = useCallback(() => apiClient.get("/api/v1/sensitive-data/policy").then((r) => setPol(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { load(); }, [load]);
  const set = (f: F, patch: Partial<F>) => apiClient.put("/api/v1/sensitive-data/policy", { entity: f.entity, field: f.field, sensitive: patch.sensitive ?? f.sensitive, retention_days: patch.retention_days === undefined ? f.retention_days : patch.retention_days })
    .then(() => { setMsg(tx("Saved.")); load(); }).catch((e) => setMsg(err(e)));
  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">{tx("Sensitive data")}</h2>
      <p className="text-xs text-gray-500">{tx("Classified fields are masked in screens, the API and exports for anyone without the \"View sensitive data\" right. Custom fields use their own \"sensitive\" flag. Every reveal is audited.")}{pol ? ` You ${pol.can_view ? "can" : "cannot"} see them.` : ""}</p>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      {pol && <table className="text-xs bg-white border w-full max-w-2xl"><thead><tr className="bg-gray-50 text-left"><th className="p-1">{tx("Record")}</th><th>{tx("Field")}</th><th>{tx("Sensitive")}</th><th>{tx("Clear after inactive (days)")}</th></tr></thead>
        <tbody>{pol.fields.map((f) => <tr key={f.entity + f.field} className="border-t"><td className="p-1">{f.entity}</td><td>{f.field}</td>
          <td><input type="checkbox" aria-label={tx("{entity} {field} sensitive", { entity: f.entity, field: f.field })} checked={f.sensitive} onChange={(e) => set(f, { sensitive: e.target.checked })} /></td>
          <td><input aria-label={tx("{entity} {field} retention", { entity: f.entity, field: f.field })} type="number" min={30} className="border rounded px-1 w-24" defaultValue={f.retention_days ?? ""} onBlur={(e) => set(f, { retention_days: e.target.value ? +e.target.value : null })} /></td></tr>)}</tbody></table>}
      <section className="border rounded p-3 bg-white space-y-2 max-w-2xl"><h3 className="font-semibold">{tx("Reveal one value")}</h3>
        <div className="flex flex-wrap gap-2 text-xs"><select aria-label={tx("Record type")} className="border rounded px-1" value={rev.entity} onChange={(e) => setRev({ ...rev, entity: e.target.value })}><option>{tx("customer")}</option><option>{tx("contact")}</option></select>
          <input aria-label={tx("Record id")} className="border rounded px-1 w-72" placeholder={tx("record id")} value={rev.record_id} onChange={(e) => setRev({ ...rev, record_id: e.target.value })} />
          <input aria-label={tx("Field")} className="border rounded px-1 w-28" value={rev.field} onChange={(e) => setRev({ ...rev, field: e.target.value })} />
          <button className="border rounded px-2" onClick={() => apiClient.post("/api/v1/sensitive-data/reveal", rev).then((r) => setMsg(`Value: ${r.data.value ?? "(empty)"} (this reveal was logged)`)).catch((e) => setMsg(err(e)))}>{tx("Reveal")}</button></div></section>
      <FieldPermissions />
    </div>
  );
}
