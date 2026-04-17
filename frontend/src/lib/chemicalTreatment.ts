/**
 * Chemical Water Treatment — TypeScript types, label maps, API client.
 *
 * Data flows:
 *  water_treatment_chemicals   → chemical master catalog
 *  treatment_chemical_records  → dosing transaction / stock movement log
 */
import { apiClient } from "./api";

// ── Enums & label maps ────────────────────────────────────────────────────────

export type ChemicalCategory =
  | "BOILER_TREATMENT"
  | "OXYGEN_SCAVENGER"
  | "ANTISCALANT"
  | "CORROSION_INHIBITOR"
  | "BIOCIDE"
  | "COAGULANT"
  | "FLOCCULANT"
  | "PH_ADJUSTER"
  | "NEUTRALIZER"
  | "DEFOAMER"
  | "CHLORINE"
  | "DECHLORINATION"
  | "BIO_NUTRIENT"
  | "OTHER";

export const CHEMICAL_CATEGORY_LABELS: Record<ChemicalCategory, string> = {
  BOILER_TREATMENT:    "Boiler Treatment",
  OXYGEN_SCAVENGER:    "Oxygen Scavenger",
  ANTISCALANT:         "Antiscalant",
  CORROSION_INHIBITOR: "Corrosion Inhibitor",
  BIOCIDE:             "Biocide",
  COAGULANT:           "Coagulant",
  FLOCCULANT:          "Flocculant",
  PH_ADJUSTER:         "pH Adjuster",
  NEUTRALIZER:         "Neutralizer",
  DEFOAMER:            "Defoamer",
  CHLORINE:            "Chlorine / Hypochlorite",
  DECHLORINATION:      "Dechlorination",
  BIO_NUTRIENT:        "Biological Nutrient",
  OTHER:               "Other",
};

export const CHEMICAL_CATEGORY_COLORS: Record<ChemicalCategory, string> = {
  BOILER_TREATMENT:    "text-orange-400",
  OXYGEN_SCAVENGER:    "text-blue-400",
  ANTISCALANT:         "text-cyan-400",
  CORROSION_INHIBITOR: "text-amber-400",
  BIOCIDE:             "text-red-400",
  COAGULANT:           "text-violet-400",
  FLOCCULANT:          "text-purple-400",
  PH_ADJUSTER:         "text-emerald-400",
  NEUTRALIZER:         "text-teal-400",
  DEFOAMER:            "text-sky-400",
  CHLORINE:            "text-yellow-400",
  DECHLORINATION:      "text-lime-400",
  BIO_NUTRIENT:        "text-green-400",
  OTHER:               "text-slate-400",
};

export const CHEMICAL_CATEGORY_BG: Record<ChemicalCategory, string> = {
  BOILER_TREATMENT:    "bg-orange-500/10 border-orange-500/20",
  OXYGEN_SCAVENGER:    "bg-blue-500/10 border-blue-500/20",
  ANTISCALANT:         "bg-cyan-500/10 border-cyan-500/20",
  CORROSION_INHIBITOR: "bg-amber-500/10 border-amber-500/20",
  BIOCIDE:             "bg-red-500/10 border-red-500/20",
  COAGULANT:           "bg-violet-500/10 border-violet-500/20",
  FLOCCULANT:          "bg-purple-500/10 border-purple-500/20",
  PH_ADJUSTER:         "bg-emerald-500/10 border-emerald-500/20",
  NEUTRALIZER:         "bg-teal-500/10 border-teal-500/20",
  DEFOAMER:            "bg-sky-500/10 border-sky-500/20",
  CHLORINE:            "bg-yellow-500/10 border-yellow-500/20",
  DECHLORINATION:      "bg-lime-500/10 border-lime-500/20",
  BIO_NUTRIENT:        "bg-green-500/10 border-green-500/20",
  OTHER:               "bg-slate-500/10 border-slate-500/20",
};

export type TreatmentType =
  | "COAGULATION"
  | "FLOCCULATION"
  | "DISINFECTION"
  | "SOFTENING"
  | "REVERSE_OSMOSIS"
  | "BIOLOGICAL"
  | "PH_ADJUSTMENT"
  | "DECHLORINATION"
  | "FILTRATION"
  | "OTHER";

export const TREATMENT_TYPE_LABELS: Record<TreatmentType, string> = {
  COAGULATION:    "Coagulation",
  FLOCCULATION:   "Flocculation",
  DISINFECTION:   "Disinfection",
  SOFTENING:      "Softening",
  REVERSE_OSMOSIS: "Reverse Osmosis",
  BIOLOGICAL:     "Biological",
  PH_ADJUSTMENT:  "pH Adjustment",
  DECHLORINATION: "Dechlorination",
  FILTRATION:     "Filtration",
  OTHER:          "Other",
};

export type DosingMode = "MANUAL" | "AUTO";

// ── Chemical Master ────────────────────────────────────────────────────────────

export interface WaterTreatmentChemical {
  id:               string;
  chemical_code:    string;
  chemical_name:    string;
  chemical_category: ChemicalCategory;
  description?:     string | null;
  supplier_id?:     string | null;
  supplier_name?:   string | null;
  stock_uom:        string;
  dosing_uom:       string;
  unit_cost?:       number | null;
  target_dose_min?: number | null;
  target_dose_max?: number | null;
  low_stock_threshold?: number | null;
  material_id?:     string | null;
  is_active:        boolean;
  notes?:           string | null;
  created_at?:      string | null;
}

export interface WaterTreatmentChemicalCreate {
  chemical_code:    string;
  chemical_name:    string;
  chemical_category: ChemicalCategory;
  description?:     string;
  supplier_id?:     string;
  stock_uom:        string;
  dosing_uom:       string;
  unit_cost?:       number;
  target_dose_min?: number;
  target_dose_max?: number;
  low_stock_threshold?: number;
  material_id?:     string;
  is_active?:       boolean;
  notes?:           string;
}

export interface WaterTreatmentChemicalUpdate extends Partial<Omit<WaterTreatmentChemicalCreate, "chemical_code">> {}

export interface ChemicalOption {
  id:               string;
  chemical_code:    string;
  chemical_name:    string;
  chemical_category: ChemicalCategory;
  stock_uom:        string;
  dosing_uom:       string;
  unit_cost?:       number | null;
}

// ── Treatment Records ─────────────────────────────────────────────────────────

export interface TreatmentRecord {
  id:               string;
  record_no:        string;
  asset_id:         string;
  asset_name?:      string | null;
  asset_no?:        string | null;

  record_datetime:  string;
  date?:            string | null;
  treatment_type:   TreatmentType;

  chemical_id?:      string | null;
  chemical_code?:    string | null;
  chemical_name:     string;
  chemical_category?: ChemicalCategory | null;

  treatment_area?:   string | null;
  dosing_point?:     string | null;

  supplier_id?:      string | null;
  supplier_name?:    string | null;
  batch_lot_no?:     string | null;
  unit_cost?:        number | null;

  stock_uom?:        string | null;
  dosing_uom?:       string | null;

  opening_stock?:    number | null;
  received_qty?:     number | null;
  consumed_qty?:     number | null;
  closing_stock?:    number | null;

  quantity_dosed:    number;
  unit:              string;
  target_dose_ppm?:  number | null;
  actual_dose_ppm?:  number | null;
  water_volume_m3?:  number | null;

  manual_or_auto_dose?: DosingMode | null;
  related_meter_id?: string | null;

  water_treated_m3?:   number | null;
  steam_produced_ton?: number | null;

  feed_ph?:               number | null;
  product_ph?:            number | null;
  feed_turbidity_ntu?:    number | null;
  product_turbidity_ntu?: number | null;
  residual_chlorine_ppm?: number | null;
  tds_feed_ppm?:          number | null;
  tds_product_ppm?:       number | null;

  source_method:    string;
  is_anomaly:       boolean;
  anomaly_note?:    string | null;
  overdose_flag:    boolean;
  underdose_flag:   boolean;
  shift_ref?:       string | null;
  inventory_synced: boolean;
  notes?:           string | null;

  created_at?:      string | null;
  updated_at?:      string | null;
}

export interface TreatmentRecordCreate {
  asset_id:          string;
  record_datetime:   string;
  date?:             string;
  treatment_type:    TreatmentType;
  chemical_id?:      string;
  chemical_code?:    string;
  chemical_name:     string;
  chemical_category?: ChemicalCategory;
  treatment_area?:   string;
  dosing_point?:     string;
  supplier_id?:      string;
  batch_lot_no?:     string;
  unit_cost?:        number;
  stock_uom?:        string;
  dosing_uom?:       string;
  opening_stock?:    number;
  received_qty?:     number;
  consumed_qty?:     number;
  closing_stock?:    number;
  quantity_dosed:    number;
  unit:              string;
  target_dose_ppm?:  number;
  actual_dose_ppm?:  number;
  water_volume_m3?:  number;
  manual_or_auto_dose?: DosingMode;
  related_meter_id?: string;
  water_treated_m3?:   number;
  steam_produced_ton?: number;
  feed_ph?:               number;
  product_ph?:            number;
  feed_turbidity_ntu?:    number;
  product_turbidity_ntu?: number;
  residual_chlorine_ppm?: number;
  tds_feed_ppm?:          number;
  tds_product_ppm?:       number;
  source_method?:    string;
  is_anomaly?:       boolean;
  anomaly_note?:     string;
  overdose_flag?:    boolean;
  underdose_flag?:   boolean;
  shift_ref?:        string;
  notes?:            string;
}

export type TreatmentRecordUpdate = Partial<TreatmentRecordCreate>;

// ── KPIs ──────────────────────────────────────────────────────────────────────

export interface ChemicalKPIs {
  date_from?:              string | null;
  date_to?:                string | null;
  total_records:           number;
  total_quantity_dosed?:   number | null;
  total_consumed_qty?:     number | null;
  total_received_qty?:     number | null;
  total_cost?:             number | null;
  chemical_per_m3_water?:  number | null;
  chemical_per_ton_steam?: number | null;
  overdose_count:          number;
  underdose_count:         number;
  anomaly_count:           number;
  low_stock_chemicals:     string[];
}

// ── Filters ───────────────────────────────────────────────────────────────────

export interface ChemTreatmentFilters {
  date_from?:         string;
  date_to?:           string;
  asset_id?:          string;
  chemical_id?:       string;
  chemical_category?: ChemicalCategory;
  treatment_area?:    string;
  supplier_id?:       string;
  is_anomaly?:        boolean;
  overdose_flag?:     boolean;
  underdose_flag?:    boolean;
  shift_ref?:         string;
  batch_lot_no?:      string;
  skip?:              number;
  limit?:             number;
}

// ── API client ────────────────────────────────────────────────────────────────

export const chemTreatmentApi = {
  // KPIs
  kpis: (filters: Partial<ChemTreatmentFilters>) =>
    apiClient
      .get<ChemicalKPIs>("/chemical-treatment/kpis", { params: filters })
      .then((r) => r.data),

  // Chemical master
  chemicals: (params?: { chemical_category?: string; is_active?: boolean; search?: string }) =>
    apiClient
      .get<WaterTreatmentChemical[]>("/chemical-treatment/chemicals", { params })
      .then((r) => r.data),

  chemicalOptions: () =>
    apiClient
      .get<ChemicalOption[]>("/chemical-treatment/chemicals/options")
      .then((r) => r.data),

  getChemical: (id: string) =>
    apiClient
      .get<WaterTreatmentChemical>(`/chemical-treatment/chemicals/${id}`)
      .then((r) => r.data),

  createChemical: (data: WaterTreatmentChemicalCreate) =>
    apiClient
      .post<WaterTreatmentChemical>("/chemical-treatment/chemicals", data)
      .then((r) => r.data),

  updateChemical: (id: string, data: WaterTreatmentChemicalUpdate) =>
    apiClient
      .patch<WaterTreatmentChemical>(`/chemical-treatment/chemicals/${id}`, data)
      .then((r) => r.data),

  deleteChemical: (id: string) =>
    apiClient.delete(`/chemical-treatment/chemicals/${id}`),

  // Treatment records
  records: (filters: ChemTreatmentFilters) =>
    apiClient
      .get<TreatmentRecord[]>("/chemical-treatment/records", { params: filters })
      .then((r) => r.data),

  getRecord: (id: string) =>
    apiClient
      .get<TreatmentRecord>(`/chemical-treatment/records/${id}`)
      .then((r) => r.data),

  createRecord: (data: TreatmentRecordCreate) =>
    apiClient
      .post<TreatmentRecord>("/chemical-treatment/records", data)
      .then((r) => r.data),

  updateRecord: (id: string, data: TreatmentRecordUpdate) =>
    apiClient
      .patch<TreatmentRecord>(`/chemical-treatment/records/${id}`, data)
      .then((r) => r.data),

  deleteRecord: (id: string) =>
    apiClient.delete(`/chemical-treatment/records/${id}`),

  // Assets dropdown
  assets: () =>
    apiClient
      .get<{ id: string; asset_no: string; name: string; utility_type: string }[]>(
        "/chemical-treatment/assets"
      )
      .then((r) => r.data),
};

export const downloadChemicalTreatmentCsv = async (filters: ChemTreatmentFilters) => {
  const response = await apiClient.get("/chemical-treatment/records/export/csv", {
    params: filters,
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(response.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `chemical-treatment-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
};
