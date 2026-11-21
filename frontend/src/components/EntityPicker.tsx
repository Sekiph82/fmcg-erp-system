"use client";
// Searchable record picker (M40.S02.T001): replaces "paste the UUID" inputs so screens link records the way the
// workflow does — choose a customer, product, lot … by name/code, the form still receives the id.
import { useEffect, useId, useRef, useState } from "react";
import { apiClient } from "@/lib/api";
import { BarcodeScanButton } from "@/components/BarcodeScanButton";

type Row = Record<string, unknown>;
interface Kind { url: string; label: (r: Row) => string; sub?: (r: Row) => string }

const LOOKUP = ["purchase_order", "goods_receipt", "shipment", "qc_inspection", "asset", "campaign", "promotion", "influencer",
  "delivery_trip", "work_center", "machine", "flow_txn", "candidate", "requisition", "sales_rep", "production_plan", "mrp_run",
  "location", "contract", "crm_record", "expense", "bom", "mpesa_transaction", "cash_transaction", "payroll_period",
  "count_task", "operator", "work_order", "purchase_invoice", "segment", "gl_account", "utility_asset", "lot", "spare_part", "product", "material", "warehouse", "supplier", "production_order", "recipe"] as const;
type LookupKind = (typeof LOOKUP)[number];
function lookupKinds(): Record<LookupKind, Kind> {
  return Object.fromEntries(LOOKUP.map((k) => [k, { url: `/api/v1/lookup/${k}`, label: (r: Row) => s(r.label), sub: (r: Row) => s(r.sub) }])) as Record<LookupKind, Kind>;
}
const s = (v: unknown) => (v === null || v === undefined ? "" : String(v));
export const ENTITY_KINDS = {
  customer: { url: "/api/v1/sales/customers", label: (r) => s(r.name), sub: (r) => s(r.code) },
  distributor: { url: "/api/v1/distributors", label: (r) => s(r.name ?? r.distributor_name), sub: (r) => s(r.code ?? r.distributor_code) },
  user: { url: "/api/v1/users", label: (r) => s(r.full_name || r.username), sub: (r) => s(r.email) },
  employee: { url: "/api/v1/hr/employees", label: (r) => s(r.full_name), sub: (r) => s(r.employee_code) },
  invoice: { url: "/api/v1/sales/invoices", label: (r) => s(r.invoice_no), sub: (r) => `${s(r.customer_name)} · ${s(r.status)}` },
  sales_order: { url: "/api/v1/sales/orders", label: (r) => s(r.order_no), sub: (r) => `${s(r.customer_name)} · ${s(r.status)}` },
  // generic lookup (id + label only, module view right checked on the server)
  ...lookupKinds(),
} satisfies Record<string, Kind>;
export type EntityKind = keyof typeof ENTITY_KINDS;

const rowsOf = (d: unknown): Row[] => (Array.isArray(d) ? d : ((d as { items?: Row[] })?.items ?? [])) as Row[];

export function EntityPicker({ kind, value, onChange, placeholder, required, label, className, params, scan }: {
  kind: EntityKind; value: string; onChange: (id: string) => void; placeholder?: string; required?: boolean;
  label?: string; className?: string; params?: Record<string, string>;
  /** show a camera scan button; hardware scanners (code + Enter) work on every picker */
  scan?: boolean;
}) {
  const cfg: Kind = ENTITY_KINDS[kind];
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [open, setOpen] = useState(false);
  const [chosen, setChosen] = useState<string>("");
  const [chosenFor, setChosenFor] = useState<string>("");   // the id the shown label belongs to
  const listId = useId();
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {  // show the name of an id set from outside (edit forms, prefilled links)
    if (!value) { setChosen(""); setChosenFor(""); return; }
    if (chosenFor === value) return;
    apiClient.get(`${cfg.url}/${value}`).then((r) => { setChosen(cfg.label(r.data as Row) || value.slice(0, 8)); setChosenFor(value); })
      .catch(() => { setChosen(value.slice(0, 8)); setChosenFor(value); });
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      // module list routes are declared with a trailing slash (no redirect across origins); lookup routes are not
      apiClient.get(cfg.url.includes("/lookup/") ? cfg.url : `${cfg.url}/`, { params: { search: q || undefined, limit: 20, ...params } })
        .then((r) => setRows(rowsOf(r.data))).catch(() => setRows([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q, open, cfg.url, params]);

  useEffect(() => {
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const pendingScan = useRef<string | null>(null);
  const pick = (r: Row) => { onChange(s(r.id)); setChosen(cfg.label(r)); setChosenFor(s(r.id)); setOpen(false); };
  const exact = (rows: Row[], code: string) => {
    const c = code.trim().toLowerCase();
    const hits = rows.filter((r) => [cfg.label(r), ...(cfg.sub?.(r) ?? "").split(" · ")].some((v) => v.trim().toLowerCase() === c));
    return hits.length === 1 ? hits[0] : rows.length === 1 ? rows[0] : null;
  };
  useEffect(() => {  // a scanned code: choose it as soon as the search for it returns
    if (pendingScan.current === null || pendingScan.current !== q) return;
    const hit = exact(rows, q);
    if (hit) { pendingScan.current = null; pick(hit); }
  }, [rows]); // eslint-disable-line react-hooks/exhaustive-deps
  const needle = q.trim().toLowerCase();
  const shown = rows.filter((r) => !needle || `${cfg.label(r)} ${cfg.sub?.(r) ?? ""}`.toLowerCase().includes(needle)).slice(0, 20);
  return (
    <div ref={box} className={`relative ${className ?? ""}`}>
      <input role="combobox" aria-expanded={open} aria-controls={listId} aria-label={label ?? placeholder ?? kind}
        required={required && !value} value={open ? q : chosen} placeholder={placeholder ?? `Search ${kind.replace("_", " ")}…`}
        onFocus={() => { setOpen(true); setQ(""); }} onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onKeyDown={(e) => { if (e.key === "Enter" && open) { e.preventDefault(); const hit = exact(shown, q); if (hit) pick(hit); else pendingScan.current = q; } }}
        className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none" />
      {scan && (
        <div className="absolute right-7 top-1/2 -translate-y-1/2">
          <BarcodeScanButton label="Scan" onScan={(code) => { pendingScan.current = code.trim(); setOpen(true); setQ(code.trim()); }} />
        </div>
      )}
      {value && !open && (
        <button type="button" aria-label="Clear" onClick={() => { onChange(""); setChosen(""); }}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-sm">×</button>
      )}
      {open && (
        <ul id={listId} role="listbox" className="absolute z-50 mt-1 w-full max-h-60 overflow-auto rounded border bg-white shadow-lg text-sm">
          {shown.length === 0 ? <li className="px-3 py-2 text-gray-400">No matches</li> : shown.map((r) => (
            <li key={s(r.id)} role="option" aria-selected={s(r.id) === value}
              onMouseDown={(e) => { e.preventDefault(); pick(r); }}
              className="px-3 py-2 cursor-pointer hover:bg-blue-50">
              <span className="block text-gray-900">{cfg.label(r) || s(r.id).slice(0, 8)}</span>
              {cfg.sub?.(r) && <span className="block text-xs text-gray-500">{cfg.sub(r)}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Picker kind for an "entity type" value used by generic link forms (documents, custom fields, barcodes). */
export function kindFor(entityType: string): EntityKind | null {
  const t = entityType.toLowerCase().replace(/^mkt_/, "");
  const alias: Record<string, EntityKind> = { location: "location", qc_inspection: "qc_inspection", goods_receipt: "goods_receipt" };
  if (t in alias) return alias[t];
  return t in ENTITY_KINDS ? (t as EntityKind) : null;
}
