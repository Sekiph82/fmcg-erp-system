const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = `${API}/api/v1/custom-fields`;
const VALUES_BASE = `${API}/api/v1/custom-fields/values`;

export type FieldType =
  | "text" | "long_text" | "number" | "decimal" | "currency"
  | "date" | "datetime" | "boolean" | "select" | "multi_select"
  | "reference" | "file_attachment" | "url" | "email" | "phone" | "computed";

export type EntityType =
  | "customer" | "supplier" | "product" | "sales_order" | "purchase_order"
  | "production_order" | "employee" | "asset" | "contract" | "crm_record"
  | "expense" | "lot";

export type ValidationRuleType =
  | "required" | "min" | "max" | "min_length" | "max_length" | "regex" | "unique" | "reference_exists";

export type CFAIAgentType = "field_design_assistant" | "data_quality_monitor" | "reporting_assistant";
export type CFAIRecStatus = "pending" | "acknowledged" | "actioned" | "dismissed";

export interface FieldOption {
  option_id: string;
  custom_field_id: string;
  option_value: string;
  option_label: string;
  display_order: number;
  active_flag: boolean;
}

export interface ValidationRule {
  validation_rule_id: string;
  custom_field_id: string;
  rule_type: ValidationRuleType;
  rule_value?: string;
  error_message?: string;
  active_flag: boolean;
}

export interface CustomFieldDefinition {
  custom_field_id: string;
  field_code: string;
  field_label: string;
  entity_type: EntityType;
  field_type: FieldType;
  help_text?: string;
  placeholder?: string;
  default_value?: string;
  required_flag: boolean;
  unique_flag: boolean;
  searchable_flag: boolean;
  filterable_flag: boolean;
  reportable_flag: boolean;
  importable_flag: boolean;
  exportable_flag: boolean;
  sensitive_flag: boolean;
  active_flag: boolean;
  display_order: number;
  section_label?: string;
  reference_entity?: string;
  formula?: string;
  created_by?: string;
  notes?: string;
  created_at: string;
  options: FieldOption[];
  validation_rules: ValidationRule[];
}

export interface FieldValueOut {
  custom_field_id: string;
  field_code: string;
  field_label: string;
  field_type: FieldType;
  value?: unknown;
  display_value?: string;
  required_flag: boolean;
  sensitive_flag: boolean;
}

export interface ValidationError {
  field_code: string;
  field_label: string;
  errors: string[];
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

export interface UsageStat {
  custom_field_id: string;
  field_code: string;
  field_label: string;
  entity_type: string;
  value_count: number;
}

export interface CFAIRec {
  rec_id: string;
  agent_type: CFAIAgentType;
  entity_type?: string;
  title: string;
  body: string;
  score?: number;
  status: CFAIRecStatus;
  rec_metadata: Record<string, unknown>;
  created_at: string;
}

async function api<T>(path: string, base = BASE, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function qs(params?: Record<string, string | boolean | undefined>): string {
  if (!params) return "";
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const customFieldsApi = {
  listFields: (params?: { entity_type?: string; active_only?: boolean }) =>
    api<CustomFieldDefinition[]>(`${qs(params)}`),
  createField: (data: object) =>
    api<CustomFieldDefinition>("", BASE, { method: "POST", body: JSON.stringify(data) }),
  getField: (id: string) => api<CustomFieldDefinition>(`/${id}`),
  updateField: (id: string, data: object) =>
    api<CustomFieldDefinition>(`/${id}`, BASE, { method: "PATCH", body: JSON.stringify(data) }),
  disableField: (id: string) =>
    api<CustomFieldDefinition>(`/${id}/disable`, BASE, { method: "POST" }),
  addOption: (id: string, data: object) =>
    api<{ ok: boolean }>(`/${id}/options`, BASE, { method: "POST", body: JSON.stringify(data) }),
  removeOption: (optionId: string) =>
    api<{ ok: boolean }>(`/options/${optionId}`, BASE, { method: "DELETE" }),

  getEntityFields: (entityType: string) =>
    api<CustomFieldDefinition[]>(`/entity/${entityType}`),
  getMetadata: () => api<Record<string, unknown>>("/metadata"),
  getUsageStats: () => api<UsageStat[]>("/usage-stats"),

  getValues: (entityType: string, entityId: string) =>
    api<FieldValueOut[]>(`/${entityType}/${entityId}`, VALUES_BASE),
  setValues: (entityType: string, entityId: string, values: Record<string, unknown>, updatedBy = "User") =>
    api<FieldValueOut[]>(`/${entityType}/${entityId}`, VALUES_BASE, {
      method: "POST", body: JSON.stringify({ values, updated_by: updatedBy }),
    }),
  validateValues: (entityType: string, entityId: string, values: Record<string, unknown>) =>
    api<ValidationResult>(`/${entityType}/${entityId}/validate`, VALUES_BASE, {
      method: "POST", body: JSON.stringify({ values }),
    }),
  getMissingRequired: (entityType: string) =>
    api<{ entity_id: string; field_code: string; field_label: string }[]>(
      `/${entityType}/missing-required`, VALUES_BASE
    ),

  listAIRecs: () => api<CFAIRec[]>("/ai/recs"),
  runFieldDesignAssistant: () =>
    api<{ generated: number }>("/ai/run/field-design-assistant", BASE, { method: "POST" }),
  runDataQualityMonitor: () =>
    api<{ generated: number }>("/ai/run/data-quality-monitor", BASE, { method: "POST" }),
  runReportingAssistant: () =>
    api<{ generated: number }>("/ai/run/reporting-assistant", BASE, { method: "POST" }),
  ackAIRec: (id: string, data: { status: CFAIRecStatus }) =>
    api<CFAIRec>(`/ai/recs/${id}`, BASE, { method: "PATCH", body: JSON.stringify(data) }),
};

export const ENTITY_LABEL: Record<EntityType, string> = {
  customer: "Customer", supplier: "Supplier", product: "Product",
  sales_order: "Sales Order", purchase_order: "Purchase Order",
  production_order: "Production Order", employee: "Employee",
  asset: "Asset", contract: "Contract", crm_record: "CRM Record",
  expense: "Expense", lot: "Inventory Lot",
};

export const FIELD_TYPE_LABEL: Record<FieldType, string> = {
  text: "Text", long_text: "Long Text", number: "Number", decimal: "Decimal",
  currency: "Currency (KES)", date: "Date", datetime: "Date & Time",
  boolean: "Yes/No", select: "Dropdown", multi_select: "Multi-Select",
  reference: "Reference Link", file_attachment: "File Attachment",
  url: "URL", email: "Email", phone: "Phone", computed: "Computed (Formula)",
};

export const FIELD_TYPE_ICON: Record<FieldType, string> = {
  text: "Aa", long_text: "¶", number: "#", decimal: "0.0",
  currency: "KES", date: "📅", datetime: "🕐", boolean: "☑",
  select: "▽", multi_select: "☑☑", reference: "🔗",
  file_attachment: "📎", url: "🌐", email: "✉", phone: "📞", computed: "∑",
};
