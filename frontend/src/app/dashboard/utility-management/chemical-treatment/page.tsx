"use client";

/**
 * Chemical Water Treatment Dashboard
 * ─────────────────────────────────────────────────────────────────────────────
 * Sections:
 *   1. Tab bar (Dosing Records | Chemical Catalog)
 *   2. Scope filters
 *   3. KPI strip
 *   4. Records table with CRUD + export
 *   5. Chemical master CRUD (second tab)
 */

import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  chemTreatmentApi,
  downloadChemicalTreatmentCsv,
  CHEMICAL_CATEGORY_LABELS,
  CHEMICAL_CATEGORY_COLORS,
  CHEMICAL_CATEGORY_BG,
  TREATMENT_TYPE_LABELS,
  type TreatmentRecord,
  type TreatmentRecordCreate,
  type TreatmentRecordUpdate,
  type WaterTreatmentChemical,
  type WaterTreatmentChemicalCreate,
  type WaterTreatmentChemicalUpdate,
  type ChemTreatmentFilters,
  type ChemicalCategory,
  type TreatmentType,
} from "@/lib/chemicalTreatment";

// ── Palette ────────────────────────────────────────────────────────────────────
const TEAL    = "#2dd4bf";
const ORANGE  = "#fb923c";
const AMBER   = "#fbbf24";
const RED     = "#f87171";
const GREEN   = "#4ade80";
const BLUE    = "#60a5fa";

// ── Helpers ────────────────────────────────────────────────────────────────────
const n = (v: number | string | null | undefined, dp = 2) =>
  v != null ? parseFloat(String(v)).toLocaleString(undefined, { maximumFractionDigits: dp }) : "—";

const fmtDate = (d: string | null | undefined) => {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString(); } catch { return d; }
};

const ALL_CATEGORIES: ChemicalCategory[] = [
  "BOILER_TREATMENT", "OXYGEN_SCAVENGER", "ANTISCALANT", "CORROSION_INHIBITOR",
  "BIOCIDE", "COAGULANT", "FLOCCULANT", "PH_ADJUSTER", "NEUTRALIZER",
  "DEFOAMER", "CHLORINE", "DECHLORINATION", "BIO_NUTRIENT", "OTHER",
];

const ALL_TREATMENT_TYPES: TreatmentType[] = [
  "COAGULATION", "FLOCCULATION", "DISINFECTION", "SOFTENING",
  "REVERSE_OSMOSIS", "BIOLOGICAL", "PH_ADJUSTMENT", "DECHLORINATION",
  "FILTRATION", "OTHER",
];

// ── KPI Card ───────────────────────────────────────────────────────────────────
function KPICard({
  label, value, sub, accent = "border-slate-700", flag, flagMsg,
}: {
  label: string; value: React.ReactNode; sub?: React.ReactNode;
  accent?: string; flag?: boolean; flagMsg?: string;
}) {
  return (
    <div className={`bg-slate-800 border rounded-lg p-4 flex flex-col gap-1 ${flag ? "border-red-500/60" : accent}`}>
      <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
      <span className="text-xl font-semibold text-white">{value}</span>
      {sub && <span className="text-xs text-slate-400">{sub}</span>}
      {flag && flagMsg && <span className="text-xs text-red-400 font-medium">{flagMsg}</span>}
    </div>
  );
}

// ── Category Badge ─────────────────────────────────────────────────────────────
function CategoryBadge({ category }: { category: ChemicalCategory | null | undefined }) {
  if (!category) return <span className="text-slate-500 text-xs">—</span>;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${CHEMICAL_CATEGORY_BG[category]} ${CHEMICAL_CATEGORY_COLORS[category]}`}>
      {CHEMICAL_CATEGORY_LABELS[category]}
    </span>
  );
}

// ── Anomaly Flags ──────────────────────────────────────────────────────────────
function AnomalyBadge({ rec }: { rec: TreatmentRecord }) {
  if (rec.overdose_flag)  return <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-500/10 border border-red-500/20 text-red-400">Overdose</span>;
  if (rec.underdose_flag) return <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 border border-amber-500/20 text-amber-400">Underdose</span>;
  if (rec.is_anomaly)     return <span className="px-2 py-0.5 rounded text-xs font-medium bg-orange-500/10 border border-orange-500/20 text-orange-400">Anomaly</span>;
  return <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">OK</span>;
}

// ── Record Form (Create / Edit) ────────────────────────────────────────────────
function RecordForm({
  initial, assets, chemicals, onSave, onClose, busy,
}: {
  initial?: TreatmentRecord | null;
  assets:   { id: string; name: string; asset_no: string }[];
  chemicals: { id: string; chemical_code: string; chemical_name: string; chemical_category: ChemicalCategory; stock_uom: string; dosing_uom: string }[];
  onSave:   (d: TreatmentRecordCreate | TreatmentRecordUpdate) => void;
  onClose:  () => void;
  busy:     boolean;
}) {
  const [f, setF] = useState<Partial<TreatmentRecordCreate>>({
    record_datetime:    initial?.record_datetime ?? new Date().toISOString().slice(0, 16),
    asset_id:           initial?.asset_id ?? "",
    treatment_type:     (initial?.treatment_type as TreatmentType) ?? "OTHER",
    chemical_id:        initial?.chemical_id ?? "",
    chemical_name:      initial?.chemical_name ?? "",
    chemical_category:  initial?.chemical_category ?? undefined,
    treatment_area:     initial?.treatment_area ?? "",
    dosing_point:       initial?.dosing_point ?? "",
    batch_lot_no:       initial?.batch_lot_no ?? "",
    unit_cost:          initial?.unit_cost ?? undefined,
    stock_uom:          initial?.stock_uom ?? "",
    dosing_uom:         initial?.dosing_uom ?? "",
    opening_stock:      initial?.opening_stock ?? undefined,
    received_qty:       initial?.received_qty ?? 0,
    consumed_qty:       initial?.consumed_qty ?? 0,
    closing_stock:      initial?.closing_stock ?? undefined,
    quantity_dosed:     initial?.quantity_dosed ?? 0,
    unit:               initial?.unit ?? "",
    target_dose_ppm:    initial?.target_dose_ppm ?? undefined,
    actual_dose_ppm:    initial?.actual_dose_ppm ?? undefined,
    water_volume_m3:    initial?.water_volume_m3 ?? undefined,
    manual_or_auto_dose: initial?.manual_or_auto_dose ?? "MANUAL",
    water_treated_m3:   initial?.water_treated_m3 ?? undefined,
    steam_produced_ton: initial?.steam_produced_ton ?? undefined,
    feed_ph:            initial?.feed_ph ?? undefined,
    product_ph:         initial?.product_ph ?? undefined,
    residual_chlorine_ppm: initial?.residual_chlorine_ppm ?? undefined,
    tds_feed_ppm:       initial?.tds_feed_ppm ?? undefined,
    tds_product_ppm:    initial?.tds_product_ppm ?? undefined,
    shift_ref:          initial?.shift_ref ?? "",
    notes:              initial?.notes ?? "",
  });

  const set = (k: keyof typeof f, v: unknown) => setF(p => ({ ...p, [k]: v }));

  const onChemSelect = (chemId: string) => {
    const c = chemicals.find(x => x.id === chemId);
    if (c) {
      set("chemical_id",       c.id);
      set("chemical_name",     c.chemical_name);
      set("chemical_category", c.chemical_category);
      set("stock_uom",         c.stock_uom);
      set("dosing_uom",        c.dosing_uom);
      set("unit",              c.dosing_uom);
    } else {
      set("chemical_id", chemId);
    }
  };

  const inp = "bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-sm text-white w-full focus:outline-none focus:border-teal-500";
  const lbl = "text-xs text-slate-400";
  const row = "flex flex-col gap-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-3xl p-6 space-y-4 overflow-y-auto max-h-[90vh]">
        <h3 className="text-white font-semibold text-lg">{initial ? "Edit" : "New"} Treatment Record</h3>

        <div className="grid grid-cols-2 gap-3">
          {/* Basic */}
          <div className={row}>
            <label className={lbl}>Asset *</label>
            <select className={inp} value={f.asset_id} onChange={e => set("asset_id", e.target.value)}>
              <option value="">— select —</option>
              {assets.map(a => <option key={a.id} value={a.id}>{a.name} ({a.asset_no})</option>)}
            </select>
          </div>
          <div className={row}>
            <label className={lbl}>Date / Time *</label>
            <input className={inp} type="datetime-local" value={f.record_datetime?.slice(0, 16)} onChange={e => set("record_datetime", e.target.value)} />
          </div>
          <div className={row}>
            <label className={lbl}>Treatment Type *</label>
            <select className={inp} value={f.treatment_type} onChange={e => set("treatment_type", e.target.value as TreatmentType)}>
              {ALL_TREATMENT_TYPES.map(t => <option key={t} value={t}>{TREATMENT_TYPE_LABELS[t]}</option>)}
            </select>
          </div>
          <div className={row}>
            <label className={lbl}>Dosing Mode</label>
            <select className={inp} value={f.manual_or_auto_dose} onChange={e => set("manual_or_auto_dose", e.target.value)}>
              <option value="MANUAL">Manual</option>
              <option value="AUTO">Automatic</option>
            </select>
          </div>

          {/* Chemical */}
          <div className={row}>
            <label className={lbl}>Chemical (master)</label>
            <select className={inp} value={f.chemical_id ?? ""} onChange={e => onChemSelect(e.target.value)}>
              <option value="">— select or type below —</option>
              {chemicals.map(c => <option key={c.id} value={c.id}>{c.chemical_code} — {c.chemical_name}</option>)}
            </select>
          </div>
          <div className={row}>
            <label className={lbl}>Chemical Name *</label>
            <input className={inp} value={f.chemical_name} onChange={e => set("chemical_name", e.target.value)} placeholder="e.g. Sodium Hypochlorite" />
          </div>
          <div className={row}>
            <label className={lbl}>Category</label>
            <select className={inp} value={f.chemical_category ?? ""} onChange={e => set("chemical_category", e.target.value as ChemicalCategory)}>
              <option value="">— select —</option>
              {ALL_CATEGORIES.map(c => <option key={c} value={c}>{CHEMICAL_CATEGORY_LABELS[c]}</option>)}
            </select>
          </div>
          <div className={row}>
            <label className={lbl}>Batch / Lot No</label>
            <input className={inp} value={f.batch_lot_no} onChange={e => set("batch_lot_no", e.target.value)} />
          </div>

          {/* Location */}
          <div className={row}>
            <label className={lbl}>Treatment Area</label>
            <input className={inp} value={f.treatment_area} onChange={e => set("treatment_area", e.target.value)} placeholder="e.g. Boiler Feed, Cooling Tower" />
          </div>
          <div className={row}>
            <label className={lbl}>Dosing Point</label>
            <input className={inp} value={f.dosing_point} onChange={e => set("dosing_point", e.target.value)} placeholder="e.g. Pump Skid A" />
          </div>

          {/* Stock */}
          <div className={row}>
            <label className={lbl}>Stock UOM</label>
            <input className={inp} value={f.stock_uom} onChange={e => set("stock_uom", e.target.value)} placeholder="kg / L / drum" />
          </div>
          <div className={row}>
            <label className={lbl}>Dosing UOM</label>
            <input className={inp} value={f.dosing_uom} onChange={e => set("dosing_uom", e.target.value)} placeholder="ml / g / ppm" />
          </div>
          <div className={row}>
            <label className={lbl}>Opening Stock</label>
            <input className={inp} type="number" step="any" value={f.opening_stock ?? ""} onChange={e => set("opening_stock", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Received Qty</label>
            <input className={inp} type="number" step="any" value={f.received_qty ?? 0} onChange={e => set("received_qty", +e.target.value)} />
          </div>
          <div className={row}>
            <label className={lbl}>Consumed Qty</label>
            <input className={inp} type="number" step="any" value={f.consumed_qty ?? 0} onChange={e => set("consumed_qty", +e.target.value)} />
          </div>
          <div className={row}>
            <label className={lbl}>Closing Stock</label>
            <input className={inp} type="number" step="any" value={f.closing_stock ?? ""} onChange={e => set("closing_stock", e.target.value ? +e.target.value : undefined)} />
          </div>

          {/* Dosing */}
          <div className={row}>
            <label className={lbl}>Quantity Dosed *</label>
            <input className={inp} type="number" step="any" value={f.quantity_dosed ?? 0} onChange={e => set("quantity_dosed", +e.target.value)} />
          </div>
          <div className={row}>
            <label className={lbl}>Dosing Unit *</label>
            <input className={inp} value={f.unit} onChange={e => set("unit", e.target.value)} placeholder="kg, L, g" />
          </div>
          <div className={row}>
            <label className={lbl}>Unit Cost</label>
            <input className={inp} type="number" step="any" value={f.unit_cost ?? ""} onChange={e => set("unit_cost", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Water Volume (m³)</label>
            <input className={inp} type="number" step="any" value={f.water_volume_m3 ?? ""} onChange={e => set("water_volume_m3", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Target Dose (ppm)</label>
            <input className={inp} type="number" step="any" value={f.target_dose_ppm ?? ""} onChange={e => set("target_dose_ppm", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Actual Dose (ppm)</label>
            <input className={inp} type="number" step="any" value={f.actual_dose_ppm ?? ""} onChange={e => set("actual_dose_ppm", e.target.value ? +e.target.value : undefined)} />
          </div>

          {/* KPI denominators */}
          <div className={row}>
            <label className={lbl}>Water Treated (m³ period)</label>
            <input className={inp} type="number" step="any" value={f.water_treated_m3 ?? ""} onChange={e => set("water_treated_m3", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Steam Produced (ton period)</label>
            <input className={inp} type="number" step="any" value={f.steam_produced_ton ?? ""} onChange={e => set("steam_produced_ton", e.target.value ? +e.target.value : undefined)} />
          </div>

          {/* Water quality */}
          <div className={row}>
            <label className={lbl}>Feed pH</label>
            <input className={inp} type="number" step="0.01" value={f.feed_ph ?? ""} onChange={e => set("feed_ph", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Product pH</label>
            <input className={inp} type="number" step="0.01" value={f.product_ph ?? ""} onChange={e => set("product_ph", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Residual Chlorine (ppm)</label>
            <input className={inp} type="number" step="any" value={f.residual_chlorine_ppm ?? ""} onChange={e => set("residual_chlorine_ppm", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>TDS Feed (ppm)</label>
            <input className={inp} type="number" step="any" value={f.tds_feed_ppm ?? ""} onChange={e => set("tds_feed_ppm", e.target.value ? +e.target.value : undefined)} />
          </div>

          {/* Meta */}
          <div className={row}>
            <label className={lbl}>Shift Ref</label>
            <input className={inp} value={f.shift_ref} onChange={e => set("shift_ref", e.target.value)} />
          </div>
          <div className={`${row} col-span-2`}>
            <label className={lbl}>Notes</label>
            <textarea className={`${inp} h-16 resize-none`} value={f.notes} onChange={e => set("notes", e.target.value)} />
          </div>
        </div>

        <div className="flex gap-2 pt-2">
          <button
            disabled={busy || !f.asset_id || !f.chemical_name || !f.quantity_dosed || !f.unit}
            onClick={() => onSave(f as TreatmentRecordCreate)}
            className="px-4 py-1.5 text-sm bg-teal-600 hover:bg-teal-500 text-white rounded disabled:opacity-40"
          >
            {busy ? "Saving…" : "Save"}
          </button>
          <button onClick={onClose} className="px-3 py-1.5 text-sm text-slate-400 hover:text-white">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Chemical Master Form ───────────────────────────────────────────────────────
function ChemicalForm({
  initial, onSave, onClose, busy,
}: {
  initial?: WaterTreatmentChemical | null;
  onSave:   (d: WaterTreatmentChemicalCreate | WaterTreatmentChemicalUpdate) => void;
  onClose:  () => void;
  busy:     boolean;
}) {
  const [f, setF] = useState<Partial<WaterTreatmentChemicalCreate>>({
    chemical_code:     initial?.chemical_code ?? "",
    chemical_name:     initial?.chemical_name ?? "",
    chemical_category: (initial?.chemical_category as ChemicalCategory) ?? "OTHER",
    description:       initial?.description ?? "",
    stock_uom:         initial?.stock_uom ?? "",
    dosing_uom:        initial?.dosing_uom ?? "",
    unit_cost:         initial?.unit_cost ?? undefined,
    target_dose_min:   initial?.target_dose_min ?? undefined,
    target_dose_max:   initial?.target_dose_max ?? undefined,
    low_stock_threshold: initial?.low_stock_threshold ?? undefined,
    is_active:         initial?.is_active ?? true,
    notes:             initial?.notes ?? "",
  });
  const set = (k: keyof typeof f, v: unknown) => setF(p => ({ ...p, [k]: v }));
  const inp = "bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-sm text-white w-full focus:outline-none focus:border-teal-500";
  const lbl = "text-xs text-slate-400";
  const row = "flex flex-col gap-1";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-lg p-6 space-y-4 overflow-y-auto max-h-[90vh]">
        <h3 className="text-white font-semibold text-lg">{initial ? "Edit" : "New"} Chemical</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className={row}>
            <label className={lbl}>Code *</label>
            <input className={inp} value={f.chemical_code} onChange={e => set("chemical_code", e.target.value)} placeholder="CHM-CLOR-001" />
          </div>
          <div className={row}>
            <label className={lbl}>Name *</label>
            <input className={inp} value={f.chemical_name} onChange={e => set("chemical_name", e.target.value)} />
          </div>
          <div className={`${row} col-span-2`}>
            <label className={lbl}>Category *</label>
            <select className={inp} value={f.chemical_category} onChange={e => set("chemical_category", e.target.value as ChemicalCategory)}>
              {ALL_CATEGORIES.map(c => <option key={c} value={c}>{CHEMICAL_CATEGORY_LABELS[c]}</option>)}
            </select>
          </div>
          <div className={row}>
            <label className={lbl}>Stock UOM *</label>
            <input className={inp} value={f.stock_uom} onChange={e => set("stock_uom", e.target.value)} placeholder="kg / L / drum" />
          </div>
          <div className={row}>
            <label className={lbl}>Dosing UOM *</label>
            <input className={inp} value={f.dosing_uom} onChange={e => set("dosing_uom", e.target.value)} placeholder="ml / g / ppm" />
          </div>
          <div className={row}>
            <label className={lbl}>Unit Cost</label>
            <input className={inp} type="number" step="any" value={f.unit_cost ?? ""} onChange={e => set("unit_cost", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Low Stock Threshold</label>
            <input className={inp} type="number" step="any" value={f.low_stock_threshold ?? ""} onChange={e => set("low_stock_threshold", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Min Target Dose</label>
            <input className={inp} type="number" step="any" value={f.target_dose_min ?? ""} onChange={e => set("target_dose_min", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={row}>
            <label className={lbl}>Max Target Dose</label>
            <input className={inp} type="number" step="any" value={f.target_dose_max ?? ""} onChange={e => set("target_dose_max", e.target.value ? +e.target.value : undefined)} />
          </div>
          <div className={`${row} col-span-2`}>
            <label className={lbl}>Description</label>
            <textarea className={`${inp} h-16 resize-none`} value={f.description} onChange={e => set("description", e.target.value)} />
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <input type="checkbox" id="is_active" checked={!!f.is_active} onChange={e => set("is_active", e.target.checked)} />
            <label htmlFor="is_active" className="text-sm text-slate-300">Active</label>
          </div>
        </div>
        <div className="flex gap-2 pt-2">
          <button
            disabled={busy || !f.chemical_code || !f.chemical_name || !f.stock_uom || !f.dosing_uom}
            onClick={() => onSave(f as WaterTreatmentChemicalCreate)}
            className="px-4 py-1.5 text-sm bg-teal-600 hover:bg-teal-500 text-white rounded disabled:opacity-40"
          >
            {busy ? "Saving…" : "Save"}
          </button>
          <button onClick={onClose} className="px-3 py-1.5 text-sm text-slate-400 hover:text-white">Cancel</button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function ChemicalTreatmentPage() {
  const qc = useQueryClient();

  // ── Tabs ─────────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"records" | "catalog">("records");

  // ── Filters ───────────────────────────────────────────────────────────────────
  const [dateFrom,    setDateFrom]   = useState("");
  const [dateTo,      setDateTo]     = useState("");
  const [assetId,     setAssetId]    = useState("");
  const [chemId,      setChemId]     = useState("");
  const [chemCat,     setChemCat]    = useState("");
  const [treatArea,   setTreatArea]  = useState("");
  const [batchLot,    setBatchLot]   = useState("");
  const [isAnomaly,   setIsAnomaly]  = useState<string>("");
  const [overdose,    setOverdose]   = useState<string>("");

  const filters: ChemTreatmentFilters = useMemo(() => ({
    ...(dateFrom    && { date_from: dateFrom }),
    ...(dateTo      && { date_to: dateTo }),
    ...(assetId     && { asset_id: assetId }),
    ...(chemId      && { chemical_id: chemId }),
    ...(chemCat     && { chemical_category: chemCat as ChemicalCategory }),
    ...(treatArea   && { treatment_area: treatArea }),
    ...(batchLot    && { batch_lot_no: batchLot }),
    ...(isAnomaly   && { is_anomaly: isAnomaly === "yes" }),
    ...(overdose    && { overdose_flag: overdose === "yes" }),
  }), [dateFrom, dateTo, assetId, chemId, chemCat, treatArea, batchLot, isAnomaly, overdose]);

  // ── Queries ───────────────────────────────────────────────────────────────────
  const { data: assets = [] } = useQuery({
    queryKey: ["chem-assets"],
    queryFn:  chemTreatmentApi.assets,
  });

  const { data: chemOptions = [] } = useQuery({
    queryKey: ["chem-options"],
    queryFn:  chemTreatmentApi.chemicalOptions,
  });

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["chem-kpis", filters],
    queryFn:  () => chemTreatmentApi.kpis(filters),
  });

  const [recPage, setRecPage] = useState(0);
  const REC_LIMIT = 50;

  const { data: records = [], isLoading: recsLoading } = useQuery({
    queryKey: ["chem-records", filters, recPage],
    queryFn:  () => chemTreatmentApi.records({ ...filters, skip: recPage * REC_LIMIT, limit: REC_LIMIT }),
  });

  const { data: chemicals = [], isLoading: chemsLoading } = useQuery({
    queryKey: ["chem-catalog"],
    queryFn:  () => chemTreatmentApi.chemicals(),
  });

  // ── Record CRUD ───────────────────────────────────────────────────────────────
  const [createRecOpen, setCreateRecOpen] = useState(false);
  const [editRec,       setEditRec]       = useState<TreatmentRecord | null>(null);
  const [deleteRec,     setDeleteRec]     = useState<TreatmentRecord | null>(null);

  const createRecMut = useMutation({
    mutationFn: (d: TreatmentRecordCreate) => chemTreatmentApi.createRecord(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chem-records"] });
      qc.invalidateQueries({ queryKey: ["chem-kpis"] });
      setCreateRecOpen(false);
    },
  });

  const updateRecMut = useMutation({
    mutationFn: ({ id, d }: { id: string; d: TreatmentRecordUpdate }) =>
      chemTreatmentApi.updateRecord(id, d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chem-records"] });
      qc.invalidateQueries({ queryKey: ["chem-kpis"] });
      setEditRec(null);
    },
  });

  const deleteRecMut = useMutation({
    mutationFn: (id: string) => chemTreatmentApi.deleteRecord(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chem-records"] });
      qc.invalidateQueries({ queryKey: ["chem-kpis"] });
      setDeleteRec(null);
    },
  });

  // ── Chemical CRUD ─────────────────────────────────────────────────────────────
  const [createChemOpen, setCreateChemOpen] = useState(false);
  const [editChem,       setEditChem]       = useState<WaterTreatmentChemical | null>(null);
  const [deleteChem,     setDeleteChem]     = useState<WaterTreatmentChemical | null>(null);

  const createChemMut = useMutation({
    mutationFn: (d: WaterTreatmentChemicalCreate) => chemTreatmentApi.createChemical(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chem-catalog"] });
      qc.invalidateQueries({ queryKey: ["chem-options"] });
      setCreateChemOpen(false);
    },
  });

  const updateChemMut = useMutation({
    mutationFn: ({ id, d }: { id: string; d: WaterTreatmentChemicalUpdate }) =>
      chemTreatmentApi.updateChemical(id, d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chem-catalog"] });
      qc.invalidateQueries({ queryKey: ["chem-options"] });
      setEditChem(null);
    },
  });

  const deleteChemMut = useMutation({
    mutationFn: (id: string) => chemTreatmentApi.deleteChemical(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chem-catalog"] });
      qc.invalidateQueries({ queryKey: ["chem-options"] });
      setDeleteChem(null);
    },
  });

  const inp = "bg-slate-900 border border-slate-600 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:border-teal-500";

  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-6 space-y-6">

      {/* ── Title & tab bar ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Chemical Water Treatment</h1>
          <p className="text-sm text-slate-400 mt-0.5">Dosing records, stock movements, lot traceability and KPIs</p>
        </div>
        <div className="flex gap-2">
          {(["records", "catalog"] as const).map(t => (
            <button
              key={t}
              onClick={() => setActiveTab(t)}
              className={`px-4 py-1.5 text-sm rounded font-medium transition-colors ${
                activeTab === t
                  ? "bg-teal-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:text-white"
              }`}
            >
              {t === "records" ? "Dosing Records" : "Chemical Catalog"}
            </button>
          ))}
        </div>
      </div>

      {/* ── RECORDS TAB ──────────────────────────────────────────────────────── */}
      {activeTab === "records" && (
        <>
          {/* Filters */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">From</label>
                <input className={inp} type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setRecPage(0); }} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">To</label>
                <input className={inp} type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setRecPage(0); }} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">Asset</label>
                <select className={inp} value={assetId} onChange={e => { setAssetId(e.target.value); setRecPage(0); }}>
                  <option value="">All assets</option>
                  {assets.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">Chemical</label>
                <select className={inp} value={chemId} onChange={e => { setChemId(e.target.value); setRecPage(0); }}>
                  <option value="">All chemicals</option>
                  {chemOptions.map(c => <option key={c.id} value={c.id}>{c.chemical_name}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">Category</label>
                <select className={inp} value={chemCat} onChange={e => { setChemCat(e.target.value); setRecPage(0); }}>
                  <option value="">All categories</option>
                  {ALL_CATEGORIES.map(c => <option key={c} value={c}>{CHEMICAL_CATEGORY_LABELS[c]}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">Treatment Area</label>
                <input className={inp} value={treatArea} onChange={e => { setTreatArea(e.target.value); setRecPage(0); }} placeholder="Filter area…" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">Batch / Lot</label>
                <input className={inp} value={batchLot} onChange={e => { setBatchLot(e.target.value); setRecPage(0); }} placeholder="Lot no…" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">Anomaly</label>
                <select className={inp} value={isAnomaly} onChange={e => { setIsAnomaly(e.target.value); setRecPage(0); }}>
                  <option value="">All</option>
                  <option value="yes">Anomaly only</option>
                  <option value="no">Normal only</option>
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">Overdose</label>
                <select className={inp} value={overdose} onChange={e => { setOverdose(e.target.value); setRecPage(0); }}>
                  <option value="">All</option>
                  <option value="yes">Overdose only</option>
                </select>
              </div>
              <button
                onClick={() => { setDateFrom(""); setDateTo(""); setAssetId(""); setChemId(""); setChemCat(""); setTreatArea(""); setBatchLot(""); setIsAnomaly(""); setOverdose(""); setRecPage(0); }}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white border border-slate-600 rounded"
              >
                Clear
              </button>
            </div>
          </div>

          {/* KPI Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
            <KPICard
              label="Total Records"
              value={kpisLoading ? "…" : n(kpis?.total_records, 0)}
              accent="border-teal-500/30"
            />
            <KPICard
              label="Qty Dosed"
              value={kpisLoading ? "…" : n(kpis?.total_quantity_dosed)}
              sub="dosing units"
            />
            <KPICard
              label="Consumed"
              value={kpisLoading ? "…" : n(kpis?.total_consumed_qty)}
              sub="stock units"
            />
            <KPICard
              label="Received"
              value={kpisLoading ? "…" : n(kpis?.total_received_qty)}
              sub="stock units"
            />
            <KPICard
              label="Total Cost"
              value={kpisLoading ? "…" : `$${n(kpis?.total_cost)}`}
              accent="border-blue-500/30"
            />
            <KPICard
              label="Chem / m³ Water"
              value={kpisLoading ? "…" : n(kpis?.chemical_per_m3_water, 4)}
              sub="dosing unit / m³"
              accent="border-cyan-500/30"
            />
            <KPICard
              label="Chem / ton Steam"
              value={kpisLoading ? "…" : n(kpis?.chemical_per_ton_steam, 4)}
              sub="dosing unit / ton"
              accent="border-orange-500/30"
            />
            <KPICard
              label="Anomalies"
              value={kpisLoading ? "…" : (kpis?.overdose_count ?? 0) + (kpis?.underdose_count ?? 0) + (kpis?.anomaly_count ?? 0)}
              flag={(kpis?.overdose_count ?? 0) > 0 || (kpis?.underdose_count ?? 0) > 0}
              flagMsg={
                (kpis?.overdose_count ?? 0) > 0
                  ? `${kpis?.overdose_count} overdose(s)`
                  : (kpis?.underdose_count ?? 0) > 0
                    ? `${kpis?.underdose_count} underdose(s)`
                    : undefined
              }
              accent="border-red-500/30"
            />
          </div>

          {/* Low stock alert */}
          {kpis?.low_stock_chemicals && kpis.low_stock_chemicals.length > 0 && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 text-sm text-amber-300">
              <span className="font-medium">Low stock alert:</span>{" "}
              {kpis.low_stock_chemicals.join(", ")}
            </div>
          )}

          {/* Records table */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
              <span className="text-sm font-medium text-white">
                Dosing Records {recsLoading ? "…" : `(${records.length})`}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => downloadChemicalTreatmentCsv(filters)}
                  className="px-3 py-1.5 text-xs border border-slate-600 rounded text-slate-300 hover:text-white"
                >
                  Export CSV
                </button>
                <button
                  onClick={() => setCreateRecOpen(true)}
                  className="px-3 py-1.5 text-xs bg-teal-600 hover:bg-teal-500 text-white rounded font-medium"
                >
                  + Add Record
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="text-xs text-slate-400 uppercase border-b border-slate-700">
                    <th className="px-3 py-2">Record No</th>
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Asset</th>
                    <th className="px-3 py-2">Chemical</th>
                    <th className="px-3 py-2">Category</th>
                    <th className="px-3 py-2">Area</th>
                    <th className="px-3 py-2">Lot No</th>
                    <th className="px-3 py-2">Dosed</th>
                    <th className="px-3 py-2">Consumed</th>
                    <th className="px-3 py-2">Closing Stock</th>
                    <th className="px-3 py-2">Target ppm</th>
                    <th className="px-3 py-2">Actual ppm</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {records.length === 0 && !recsLoading && (
                    <tr><td colSpan={14} className="px-3 py-8 text-center text-slate-500">No records found.</td></tr>
                  )}
                  {records.map(rec => (
                    <tr key={rec.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                      <td className="px-3 py-2 text-slate-300 font-mono text-xs">{rec.record_no}</td>
                      <td className="px-3 py-2 text-slate-300">{rec.date ? fmtDate(rec.date) : fmtDate(rec.record_datetime)}</td>
                      <td className="px-3 py-2 text-slate-300">{rec.asset_name ?? rec.asset_id}</td>
                      <td className="px-3 py-2 text-white">{rec.chemical_name}</td>
                      <td className="px-3 py-2"><CategoryBadge category={rec.chemical_category as ChemicalCategory} /></td>
                      <td className="px-3 py-2 text-slate-400 text-xs">{rec.treatment_area ?? "—"}</td>
                      <td className="px-3 py-2 text-slate-400 text-xs font-mono">{rec.batch_lot_no ?? "—"}</td>
                      <td className="px-3 py-2 text-white">{n(rec.quantity_dosed)} {rec.unit}</td>
                      <td className="px-3 py-2 text-slate-300">{rec.consumed_qty != null ? `${n(rec.consumed_qty)} ${rec.stock_uom ?? ""}` : "—"}</td>
                      <td className="px-3 py-2 text-slate-300">{rec.closing_stock != null ? `${n(rec.closing_stock)} ${rec.stock_uom ?? ""}` : "—"}</td>
                      <td className="px-3 py-2 text-slate-400">{rec.target_dose_ppm != null ? n(rec.target_dose_ppm) : "—"}</td>
                      <td className="px-3 py-2 text-slate-400">{rec.actual_dose_ppm != null ? n(rec.actual_dose_ppm) : "—"}</td>
                      <td className="px-3 py-2"><AnomalyBadge rec={rec} /></td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2">
                          <button onClick={() => setEditRec(rec)} className="text-xs text-teal-400 hover:text-teal-300">Edit</button>
                          <button onClick={() => setDeleteRec(rec)} className="text-xs text-red-400 hover:text-red-300">Del</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center gap-3 px-4 py-3 border-t border-slate-700">
              <button disabled={recPage === 0} onClick={() => setRecPage(p => p - 1)} className="text-xs text-slate-400 hover:text-white disabled:opacity-40">← Prev</button>
              <span className="text-xs text-slate-400">Page {recPage + 1}</span>
              <button disabled={records.length < REC_LIMIT} onClick={() => setRecPage(p => p + 1)} className="text-xs text-slate-400 hover:text-white disabled:opacity-40">Next →</button>
            </div>
          </div>
        </>
      )}

      {/* ── CATALOG TAB ──────────────────────────────────────────────────────── */}
      {activeTab === "catalog" && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
            <span className="text-sm font-medium text-white">
              Chemical Catalog {chemsLoading ? "…" : `(${chemicals.length})`}
            </span>
            <button
              onClick={() => setCreateChemOpen(true)}
              className="px-3 py-1.5 text-xs bg-teal-600 hover:bg-teal-500 text-white rounded font-medium"
            >
              + New Chemical
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="text-xs text-slate-400 uppercase border-b border-slate-700">
                  <th className="px-3 py-2">Code</th>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Supplier</th>
                  <th className="px-3 py-2">Stock UOM</th>
                  <th className="px-3 py-2">Dosing UOM</th>
                  <th className="px-3 py-2">Unit Cost</th>
                  <th className="px-3 py-2">Target Dose</th>
                  <th className="px-3 py-2">Low Stock</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {chemicals.length === 0 && !chemsLoading && (
                  <tr><td colSpan={11} className="px-3 py-8 text-center text-slate-500">No chemicals configured.</td></tr>
                )}
                {chemicals.map(chem => (
                  <tr key={chem.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="px-3 py-2 font-mono text-xs text-slate-300">{chem.chemical_code}</td>
                    <td className="px-3 py-2 text-white">{chem.chemical_name}</td>
                    <td className="px-3 py-2"><CategoryBadge category={chem.chemical_category as ChemicalCategory} /></td>
                    <td className="px-3 py-2 text-slate-400 text-xs">{chem.supplier_name ?? "—"}</td>
                    <td className="px-3 py-2 text-slate-300">{chem.stock_uom}</td>
                    <td className="px-3 py-2 text-slate-300">{chem.dosing_uom}</td>
                    <td className="px-3 py-2 text-slate-300">{chem.unit_cost != null ? `$${n(chem.unit_cost, 4)}` : "—"}</td>
                    <td className="px-3 py-2 text-slate-400 text-xs">
                      {chem.target_dose_min != null || chem.target_dose_max != null
                        ? `${chem.target_dose_min ?? "—"} – ${chem.target_dose_max ?? "—"}`
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-slate-400 text-xs">{chem.low_stock_threshold != null ? n(chem.low_stock_threshold) : "—"}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${chem.is_active ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-slate-500/10 border-slate-500/20 text-slate-400"}`}>
                        {chem.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button onClick={() => setEditChem(chem)} className="text-xs text-teal-400 hover:text-teal-300">Edit</button>
                        <button onClick={() => setDeleteChem(chem)} className="text-xs text-red-400 hover:text-red-300">Del</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Modals ────────────────────────────────────────────────────────────── */}

      {/* Create record */}
      {createRecOpen && (
        <RecordForm
          assets={assets}
          chemicals={chemOptions}
          onSave={d => createRecMut.mutate(d as TreatmentRecordCreate)}
          onClose={() => setCreateRecOpen(false)}
          busy={createRecMut.isPending}
        />
      )}

      {/* Edit record */}
      {editRec && (
        <RecordForm
          initial={editRec}
          assets={assets}
          chemicals={chemOptions}
          onSave={d => updateRecMut.mutate({ id: editRec.id, d: d as TreatmentRecordUpdate })}
          onClose={() => setEditRec(null)}
          busy={updateRecMut.isPending}
        />
      )}

      {/* Delete record */}
      {deleteRec && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-sm space-y-4">
            <h3 className="text-white font-semibold">Delete Record</h3>
            <p className="text-sm text-slate-300">
              Delete <strong>{deleteRec.record_no}</strong>? This cannot be undone.
            </p>
            <div className="flex gap-2">
              <button
                disabled={deleteRecMut.isPending}
                onClick={() => deleteRecMut.mutate(deleteRec.id)}
                className="px-4 py-1.5 text-sm bg-red-600 hover:bg-red-500 text-white rounded disabled:opacity-40"
              >
                {deleteRecMut.isPending ? "Deleting…" : "Delete"}
              </button>
              <button onClick={() => setDeleteRec(null)} className="px-3 py-1.5 text-sm text-slate-400 hover:text-white">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Create chemical */}
      {createChemOpen && (
        <ChemicalForm
          onSave={d => createChemMut.mutate(d as WaterTreatmentChemicalCreate)}
          onClose={() => setCreateChemOpen(false)}
          busy={createChemMut.isPending}
        />
      )}

      {/* Edit chemical */}
      {editChem && (
        <ChemicalForm
          initial={editChem}
          onSave={d => updateChemMut.mutate({ id: editChem.id, d: d as WaterTreatmentChemicalUpdate })}
          onClose={() => setEditChem(null)}
          busy={updateChemMut.isPending}
        />
      )}

      {/* Delete chemical */}
      {deleteChem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-sm space-y-4">
            <h3 className="text-white font-semibold">Delete Chemical</h3>
            <p className="text-sm text-slate-300">
              Delete <strong>{deleteChem.chemical_name}</strong> from the catalog?
              Existing records referencing this chemical will not be deleted.
            </p>
            <div className="flex gap-2">
              <button
                disabled={deleteChemMut.isPending}
                onClick={() => deleteChemMut.mutate(deleteChem.id)}
                className="px-4 py-1.5 text-sm bg-red-600 hover:bg-red-500 text-white rounded disabled:opacity-40"
              >
                {deleteChemMut.isPending ? "Deleting…" : "Delete"}
              </button>
              <button onClick={() => setDeleteChem(null)} className="px-3 py-1.5 text-sm text-slate-400 hover:text-white">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
