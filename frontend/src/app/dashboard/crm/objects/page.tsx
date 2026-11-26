"use client";
// M45.S01.T015 custom objects: define types (admin), records list/detail, associations, CSV import/export, report.
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { tx } from "@/lib/i18n/core";

type FieldDef = { key: string; label: string; type: string; required: boolean; unique: boolean; options?: string[] };
type OType = { key: string; label: string; label_plural: string; fields: FieldDef[]; display_field: string };
type Rec = { id: string; display: string; data: Record<string, unknown>; associations?: { id: string; target_type: string; target_id: string; label: string }[] };
const err = (e: unknown) => { const d = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail; return typeof d === "string" ? d : tx("Something went wrong."); };
const TYPES = ["text", "number", "date", "bool", "select", "email", "phone"];
const inp = "border rounded px-2 py-1 text-xs";

export default function CustomObjectsPage() {
  const [types, setTypes] = useState<OType[]>([]);
  const [cur, setCur] = useState<OType | null>(null);
  const [recs, setRecs] = useState<Rec[]>([]);
  const [open, setOpen] = useState<Rec | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [def, setDef] = useState({ key: "", label: "", fields: [{ key: "name", label: "Name", type: "text", required: true, unique: false }] as FieldDef[] });
  const [assoc, setAssoc] = useState({ target_type: "customer", target_id: "", label: "related" });
  const [rep, setRep] = useState<{ value: string | null; count: number; sum?: number }[] | null>(null);
  const [csvText, setCsvText] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const loadTypes = useCallback(() => apiClient.get("/api/v1/custom-objects/types").then((r) => setTypes(r.data)).catch((e) => setMsg(err(e))), []);
  useEffect(() => { loadTypes(); }, [loadTypes]);
  const loadRecs = useCallback((t: OType) => apiClient.get(`/api/v1/custom-objects/${t.key}/records`).then((r) => { setCur(r.data.type); setRecs(r.data.records); }).catch((e) => setMsg(err(e))), []);
  const act = (p: Promise<unknown>, ok: string, after?: () => void) => p.then(() => { setMsg(ok); after?.(); }).catch((e) => setMsg(err(e)));
  const openRec = (r: Rec) => apiClient.get(`/api/v1/custom-objects/${cur!.key}/records/${r.id}`).then((x) => { setOpen(x.data); setForm(Object.fromEntries(cur!.fields.map((f) => [f.key, x.data.data[f.key] == null ? "" : String(x.data.data[f.key])]))); });
  const save = () => {
    const data = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v === "" ? null : v]));
    act(open ? apiClient.put(`/api/v1/custom-objects/${cur!.key}/records/${open.id}`, { data }) : apiClient.post(`/api/v1/custom-objects/${cur!.key}/records`, { data }),
      "Saved.", () => { setOpen(null); setForm({}); loadRecs(cur!); });
  };
  const setField = (i: number, p: Partial<FieldDef>) => setDef({ ...def, fields: def.fields.map((f, j) => (j === i ? { ...f, ...p } : f)) });

  return (
    <div className="p-4 space-y-4 text-sm">
      <h2 className="text-lg font-semibold">{tx("Custom objects")}</h2>
      {msg && <p role="status" className="text-xs">{msg}</p>}
      <div className="flex flex-wrap gap-2">{types.map((t) => <button key={t.key} className={`border rounded px-2 py-1 text-xs ${cur?.key === t.key ? "bg-indigo-50" : "bg-white"}`} onClick={() => { setOpen(null); setRep(null); loadRecs(t); }}>{t.label_plural}</button>)}</div>
      <details className="border rounded p-3 bg-white"><summary className="cursor-pointer font-semibold">{tx("Define a new object type (CRM administrators)")}</summary>
        <div className="space-y-2 mt-2">
          <div className="flex flex-wrap gap-2"><input aria-label={tx("Type key")} className={inp} placeholder={tx("key (e.g. freezer)")} value={def.key} onChange={(e) => setDef({ ...def, key: e.target.value })} />
            <input aria-label={tx("Type label")} className={inp} placeholder={tx("Label (e.g. Freezer)")} value={def.label} onChange={(e) => setDef({ ...def, label: e.target.value })} /></div>
          {def.fields.map((f, i) => <div key={i} className="flex flex-wrap gap-2 items-center text-xs">
            <input aria-label={tx("Field key")} className={inp} value={f.key} onChange={(e) => setField(i, { key: e.target.value })} />
            <input aria-label={tx("Field label")} className={inp} value={f.label} onChange={(e) => setField(i, { label: e.target.value })} />
            <select aria-label={tx("Field type")} className={inp} value={f.type} onChange={(e) => setField(i, { type: e.target.value })}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select>
            {f.type === "select" && <input aria-label={tx("Options")} className={inp} placeholder={tx("options, comma separated")} value={(f.options ?? []).join(",")} onChange={(e) => setField(i, { options: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} />}
            <label><input type="checkbox" checked={f.required} onChange={(e) => setField(i, { required: e.target.checked })} /> {tx("required")}</label>
            <label><input type="checkbox" checked={f.unique} onChange={(e) => setField(i, { unique: e.target.checked })} /> {tx("unique")}</label></div>)}
          <div className="flex gap-2"><button className="border rounded px-2 text-xs" onClick={() => setDef({ ...def, fields: [...def.fields, { key: "", label: "", type: "text", required: false, unique: false }] })}>{tx("+ Field")}</button>
            <button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={() => act(apiClient.post("/api/v1/custom-objects/types", { ...def, label_plural: def.label + "s" }), tx("Object type created."), loadTypes)}>{tx("Create type")}</button></div>
        </div></details>
      {cur && <section className="space-y-2">
        <div className="flex flex-wrap gap-2 items-center"><h3 className="font-semibold">{cur.label_plural}</h3>
          <button className="border rounded px-2 text-xs" onClick={() => { setOpen(null); setForm({}); }}>{tx("+ New")} {cur.label}</button>
          <a className="underline text-xs" href={`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/v1/custom-objects/${cur.key}/export.csv`}>{tx("Export CSV")}</a>
          <select aria-label={tx("Report by field")} className={inp} defaultValue="" onChange={(e) => e.target.value && apiClient.get(`/api/v1/custom-objects/${cur.key}/report`, { params: { group_by: e.target.value } }).then((r) => setRep(r.data)).catch((x) => setMsg(err(x)))}>
            <option value="">{tx("Report: count by…")}</option>{cur.fields.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}</select></div>
        {rep && <ul className="text-xs border rounded p-2 bg-white">{rep.map((r, i) => <li key={i}>{r.value ?? tx("(empty)")}: {r.count}</li>)}</ul>}
        <div className="overflow-x-auto"><table className="text-xs bg-white border w-full"><thead><tr className="bg-gray-50 text-left">{cur.fields.slice(0, 5).map((f) => <th key={f.key} className="p-1">{f.label}</th>)}</tr></thead>
          <tbody>{recs.map((r) => <tr key={r.id} className="border-t cursor-pointer hover:bg-gray-50" onClick={() => openRec(r)}>{cur.fields.slice(0, 5).map((f) => <td key={f.key} className="p-1">{String(r.data[f.key] ?? "")}</td>)}</tr>)}</tbody></table></div>
        <div className="border rounded p-3 bg-white space-y-2"><h4 className="font-semibold text-xs">{open ? tx("Edit {display}", { display: open.display }) : tx("New {label}", { label: cur.label })}</h4>
          <div className="grid sm:grid-cols-2 gap-2">{cur.fields.map((f) => <label key={f.key} className="text-xs">{f.label}{f.required ? " *" : ""}
            {f.type === "select" ? <select aria-label={f.label} className={`${inp} w-full`} value={form[f.key] ?? ""} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}><option value=""></option>{(f.options ?? []).map((o) => <option key={o}>{o}</option>)}</select>
              : <input aria-label={f.label} type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"} className={`${inp} w-full`} value={form[f.key] ?? ""} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />}</label>)}</div>
          <div className="flex gap-2"><button className="bg-indigo-600 text-white rounded px-3 py-1 text-xs" onClick={save}>{tx("Save")}</button>
            {open && <button className="text-red-600 underline text-xs" onClick={() => act(apiClient.delete(`/api/v1/custom-objects/${cur.key}/records/${open.id}`), "Deleted.", () => { setOpen(null); loadRecs(cur); })}>{tx("Delete")}</button>}</div>
          {open && <div className="text-xs space-y-1"><b>{tx("Associations")}</b>
            <ul>{(open.associations ?? []).map((a) => <li key={a.id}>{a.target_type} {a.target_id} ({a.label}) <button className="underline" onClick={() => act(apiClient.delete(`/api/v1/custom-objects/${cur.key}/records/${open.id}/associations/${a.id}`), "Removed.", () => openRec(open))}>{tx("remove")}</button></li>)}</ul>
            <div className="flex flex-wrap gap-2"><select aria-label={tx("Associate with")} className={inp} value={assoc.target_type} onChange={(e) => setAssoc({ ...assoc, target_type: e.target.value })}>{[["customer", tx("customer")], ["crm_record", "crm_record"], ["product", tx("product")], ["sales_order", "sales_order"], ["co_record", "co_record"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
              <input aria-label={tx("Target id")} className={inp} placeholder={tx("record id")} value={assoc.target_id} onChange={(e) => setAssoc({ ...assoc, target_id: e.target.value })} />
              <input aria-label={tx("Association label")} className={inp} value={assoc.label} onChange={(e) => setAssoc({ ...assoc, label: e.target.value })} />
              <button className="border rounded px-2" onClick={() => act(apiClient.post(`/api/v1/custom-objects/${cur.key}/records/${open.id}/associations`, assoc), "Associated.", () => openRec(open))}>{tx("Add")}</button></div></div>}
        </div>
        <details className="text-xs"><summary className="cursor-pointer">{tx("Import CSV")}</summary>
          <textarea aria-label={tx("CSV to import")} className={`${inp} w-full font-mono`} rows={4} placeholder={cur.fields.map((f) => f.key).join(",")} value={csvText} onChange={(e) => setCsvText(e.target.value)} />
          <button className="border rounded px-2 py-1" onClick={() => apiClient.post(`/api/v1/custom-objects/${cur.key}/import`, { csv: csvText }).then((r) => { setMsg(tx("Imported {created}; {length} rows refused.", { created: r.data.created, length: r.data.errors.length })); loadRecs(cur); }).catch((e) => setMsg(err(e)))}>{tx("Import")}</button></details>
      </section>}
    </div>
  );
}
