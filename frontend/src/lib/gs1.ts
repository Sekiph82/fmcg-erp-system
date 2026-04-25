// GS1 Barcode + Label Printing System — types & API client

const BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/gs1`;

// ── Enums / Types ─────────────────────────────────────────────────────────────

export type BarcodeType = "EAN13" | "GS1_128" | "QR_CODE" | "CODE128" | "GS1_DATAMATRIX";
export type PackagingLevel = "UNIT" | "INNER_PACK" | "CARTON" | "PALLET";
export type PrintJobStatus = "PENDING" | "PRINTING" | "COMPLETED" | "FAILED" | "CANCELLED";
export type SSCCStatus = "ACTIVE" | "SHIPPED" | "RECEIVED" | "CANCELLED";
export type LabelTemplateStatus = "DRAFT" | "ACTIVE" | "DEPRECATED";
export type PrintTrigger = "MANUAL" | "PRODUCTION_COMPLETE" | "PACKAGING_COMPLETE" | "PALLETIZATION" | "SHIPMENT" | "QC_RELEASE";
export type GS1AIAgentType = "LABEL_VALIDATOR" | "PACKAGING_OPTIMIZER";
export type GS1AIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "APPLIED";

// ── Domain Objects ────────────────────────────────────────────────────────────

export interface GS1CompanyConfig {
  id: string;
  company_name: string;
  gs1_company_prefix: string;
  country_code: string | null;
  extension_digit: number;
  sscc_serial_counter: number;
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

export interface ProductGS1Config {
  id: string;
  product_id: string;
  company_config_id: string | null;
  gtin: string | null;
  barcode_type: BarcodeType;
  packaging_level: PackagingLevel;
  label_template_id: string | null;
  gs1_company_prefix: string | null;
  requires_serialization: boolean;
  requires_lot_tracking: boolean;
  requires_expiry_tracking: boolean;
  units_per_inner_pack: number | null;
  inner_packs_per_carton: number | null;
  cartons_per_pallet: number | null;
  carton_gtin: string | null;
  pallet_gtin: string | null;
  is_active: boolean;
  notes: string | null;
  product_name: string | null;
  created_at: string;
}

export interface LotBarcodeRecord {
  id: string;
  product_config_id: string;
  lot_id: string | null;
  gtin: string;
  lot_number: string;
  production_date: string | null;
  expiry_date: string | null;
  serial_number: string | null;
  barcode_type: BarcodeType;
  gs1_ai_string: string;
  qr_payload: string | null;
  barcode_image_b64: string | null;
  qr_image_b64: string | null;
  is_printed: boolean;
  printed_at: string | null;
  quantity: string | null;
  packaging_level: PackagingLevel | null;
  created_at: string;
}

export interface BarcodeGenerateRequest {
  product_id?: string;
  gtin?: string;
  lot_number?: string;
  expiry_date?: string;
  production_date?: string;
  serial_number?: string;
  barcode_type?: BarcodeType;
  quantity?: number;
  lot_id?: string;
  packaging_level?: PackagingLevel;
  save_record?: boolean;
}

export interface BarcodeGenerateResponse {
  gs1_ai_string: string;
  gs1_raw_string: string;
  qr_payload: string;
  barcode_image_b64: string | null;
  qr_image_b64: string | null;
  check_digit_valid: boolean;
  record_id: string | null;
  gtin: string;
  lot_number: string | null;
  expiry_date: string | null;
  production_date: string | null;
}

export interface GS1DecodeResponse {
  segments: Record<string, string>;
  gtin: string | null;
  lot_number: string | null;
  expiry_date: string | null;
  production_date: string | null;
  serial_number: string | null;
  sscc: string | null;
  is_valid: boolean;
  validation_errors: string[];
  matched_product: Record<string, string> | null;
  matched_lot: Record<string, string> | null;
}

export interface SSCCPallet {
  id: string;
  sscc_code: string;
  extension_digit: number;
  company_prefix: string;
  serial_reference: string;
  check_digit: number;
  pallet_id: string | null;
  status: SSCCStatus;
  warehouse_location: string | null;
  shipment_reference: string | null;
  sscc_image_b64: string | null;
  label_printed: boolean;
  label_printed_at: string | null;
  notes: string | null;
  lot_count: number;
  created_at: string;
}

export interface LabelTemplate {
  id: string;
  name: string;
  description: string | null;
  packaging_level: PackagingLevel | null;
  template_version: number;
  status: LabelTemplateStatus;
  width_mm: string | null;
  height_mm: string | null;
  fields: Record<string, unknown> | null;
  html_template: string | null;
  css_styles: string | null;
  is_default: boolean;
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

export interface PrintJob {
  id: string;
  job_no: string;
  trigger: PrintTrigger;
  template_id: string | null;
  status: PrintJobStatus;
  printed_by: string | null;
  printed_at: string | null;
  quantity: number;
  printer_name: string | null;
  notes: string | null;
  item_count: number;
  created_at: string;
}

export interface GS1AIRecommendation {
  id: string;
  agent_type: GS1AIAgentType;
  title: string;
  description: string;
  affected_entity_type: string | null;
  affected_entity_id: string | null;
  recommendation: string;
  severity: string;
  status: GS1AIRecStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  agent_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface GS1Dashboard {
  total_products_configured: number;
  total_gtins: number;
  total_barcodes_generated: number;
  total_labels_printed: number;
  total_sscc_pallets: number;
  active_sscc_pallets: number;
  total_print_jobs: number;
  pending_print_jobs: number;
  total_label_templates: number;
  ai_recommendations_pending: number;
  recent_barcodes: LotBarcodeRecord[];
  recent_sscc: SSCCPallet[];
}

// ── API Client ────────────────────────────────────────────────────────────────

function authHeader(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const gs1Api = {
  // Dashboard
  getDashboard: () => req<GS1Dashboard>("GET", "/dashboard"),

  // Company config
  listCompanyConfigs: () => req<GS1CompanyConfig[]>("GET", "/config"),
  createCompanyConfig: (d: Partial<GS1CompanyConfig>) => req<GS1CompanyConfig>("POST", "/config", d),

  // Product GS1 config
  listProductConfigs: () => req<ProductGS1Config[]>("GET", "/products"),
  getProductConfig: (id: string) => req<ProductGS1Config>("GET", `/products/${id}`),
  getConfigByProduct: (productId: string) => req<ProductGS1Config>("GET", `/products/by-product/${productId}`),
  createProductConfig: (d: Partial<ProductGS1Config>) => req<ProductGS1Config>("POST", "/products", d),
  updateProductConfig: (id: string, d: Partial<ProductGS1Config>) => req<ProductGS1Config>("PATCH", `/products/${id}`, d),

  // Barcode generation
  generateBarcode: (d: BarcodeGenerateRequest) => req<BarcodeGenerateResponse>("POST", "/barcode/generate", d),
  listBarcodes: (params?: { product_config_id?: string; lot_id?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.product_config_id) q.set("product_config_id", params.product_config_id);
    if (params?.lot_id) q.set("lot_id", params.lot_id);
    if (params?.limit) q.set("limit", String(params.limit));
    return req<LotBarcodeRecord[]>("GET", `/barcode?${q}`);
  },
  getBarcode: (id: string) => req<LotBarcodeRecord>("GET", `/barcode/${id}`),

  // Scan / decode
  decodeGS1: (gs1_string: string) => req<GS1DecodeResponse>("POST", "/scan/decode", { gs1_string }),

  // SSCC
  generateSSCC: (d?: { company_config_id?: string; pallet_id?: string; warehouse_location?: string; notes?: string }) =>
    req<SSCCPallet>("POST", "/sscc/generate", d || {}),
  listSSCC: (params?: { status?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.limit) q.set("limit", String(params.limit));
    return req<SSCCPallet[]>("GET", `/sscc?${q}`);
  },
  getSSCC: (id: string) => req<SSCCPallet>("GET", `/sscc/${id}`),
  addLotToSSCC: (ssccId: string, lot_barcode_id: string, quantity?: number) =>
    req("POST", `/sscc/${ssccId}/lots`, { lot_barcode_id, quantity }),
  updateSSCCStatus: (id: string, status: string, shipment_reference?: string) => {
    const q = new URLSearchParams({ status });
    if (shipment_reference) q.set("shipment_reference", shipment_reference);
    return req("PATCH", `/sscc/${id}/status?${q}`);
  },

  // Label templates
  listTemplates: (packaging_level?: string) => {
    const q = packaging_level ? `?packaging_level=${packaging_level}` : "";
    return req<LabelTemplate[]>("GET", `/labels/templates${q}`);
  },
  getTemplate: (id: string) => req<LabelTemplate>("GET", `/labels/templates/${id}`),
  createTemplate: (d: Partial<LabelTemplate>) => req<LabelTemplate>("POST", "/labels/templates", d),
  updateTemplate: (id: string, d: Partial<LabelTemplate>) => req<LabelTemplate>("PATCH", `/labels/templates/${id}`, d),

  // Print jobs
  createPrintJob: (d: { trigger?: string; template_id?: string; items?: unknown[]; notes?: string }) =>
    req<PrintJob>("POST", "/labels/print", d),
  listPrintJobs: (status?: string) => req<PrintJob[]>("GET", `/labels/print${status ? `?status=${status}` : ""}`),
  completePrintJob: (id: string, printed_by = "user") =>
    req("POST", `/labels/print/${id}/complete?printed_by=${printed_by}`),

  // AI
  runLabelValidator: () => req<{ generated: number }>("POST", "/ai/run-label-validator"),
  runPackagingOptimizer: () => req<{ generated: number }>("POST", "/ai/run-packaging-optimizer"),
  listRecommendations: (agent_type?: string, status?: string) => {
    const q = new URLSearchParams();
    if (agent_type) q.set("agent_type", agent_type);
    if (status) q.set("status", status);
    return req<GS1AIRecommendation[]>("GET", `/ai/recommendations?${q}`);
  },
  reviewRecommendation: (id: string, status: string, reviewed_by?: string) =>
    req<GS1AIRecommendation>("PATCH", `/ai/recommendations/${id}`, { status, reviewed_by }),

  // Reports
  getPrintHistory: () => req<unknown[]>("GET", "/reports/print-history"),
  getSSCCTracking: () => req<unknown[]>("GET", "/reports/sscc-tracking"),
  getPackagingHierarchy: () => req<unknown[]>("GET", "/reports/packaging-hierarchy"),
  getBarcodeUsage: () => req<unknown[]>("GET", "/reports/barcode-usage"),
};

// ── Color Maps ────────────────────────────────────────────────────────────────

export const statusColor: Record<string, string> = {
  PENDING:    "bg-yellow-100 text-yellow-800",
  PRINTING:   "bg-blue-100 text-blue-800",
  COMPLETED:  "bg-green-100 text-green-800",
  FAILED:     "bg-red-100 text-red-800",
  CANCELLED:  "bg-gray-100 text-gray-600",
  ACTIVE:     "bg-green-100 text-green-800",
  SHIPPED:    "bg-blue-100 text-blue-800",
  RECEIVED:   "bg-purple-100 text-purple-800",
  DRAFT:      "bg-gray-100 text-gray-600",
  DEPRECATED: "bg-orange-100 text-orange-800",
};

export const severityColor: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH:     "bg-orange-100 text-orange-800",
  MEDIUM:   "bg-yellow-100 text-yellow-800",
  LOW:      "bg-green-100 text-green-800",
};

export const packagingLevelLabel: Record<PackagingLevel, string> = {
  UNIT:       "Unit / Each",
  INNER_PACK: "Inner Pack",
  CARTON:     "Carton",
  PALLET:     "Pallet",
};
