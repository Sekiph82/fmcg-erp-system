import { apiClient } from "./api";

const BASE = "/api/v1/custom-fields";
const VALUES_BASE = "/api/v1/custom-fields/values";

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

export type FieldWidth = "full" | "half" | "third";

export type WFTriggerEvent =
  | "record_created" | "record_updated" | "field_changed"
  | "value_equals" | "value_gt" | "value_lt";

export type WFActionType =
  | "send_notification" | "set_field_value" | "assign_tag"
  | "trigger_workflow" | "webhook_call";

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
  field_width?: FieldWidth;
  reference_entity?: string;
  formula?: string;
  created_by?: string;
  notes?: string;
  created_at: string;
  options: FieldOption[];
  validation_rules: ValidationRule[];
}

export interface FormLayoutItem {
  custom_field_id: string;
  display_order: number;
  section_label?: string;
  field_width?: FieldWidth;
}

export interface WorkflowRule {
  rule_id: string;
  rule_name: string;
  entity_type: EntityType;
  trigger_event: WFTriggerEvent;
  condition_field?: string;
  condition_operator?: string;
  condition_value?: string;
  action_type: WFActionType;
  action_payload: Record<string, unknown>;
  active_flag: boolean;
  created_by?: string;
  notes?: string;
  created_at: string;
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

export const customFieldsApi = {
  listFields: (params?: { entity_type?: string; active_only?: boolean }) =>
    apiClient.get<CustomFieldDefinition[]>(BASE, { params }).then(r => r.data),
  createField: (data: object) =>
    apiClient.post<CustomFieldDefinition>(BASE, data).then(r => r.data),
  getField: (id: string) =>
    apiClient.get<CustomFieldDefinition>(`${BASE}/${id}`).then(r => r.data),
  updateField: (id: string, data: object) =>
    apiClient.patch<CustomFieldDefinition>(`${BASE}/${id}`, data).then(r => r.data),
  disableField: (id: string) =>
    apiClient.post<CustomFieldDefinition>(`${BASE}/${id}/disable`).then(r => r.data),
  addOption: (id: string, data: object) =>
    apiClient.post<{ ok: boolean }>(`${BASE}/${id}/options`, data).then(r => r.data),
  removeOption: (optionId: string) =>
    apiClient.delete<{ ok: boolean }>(`${BASE}/options/${optionId}`).then(r => r.data),

  getEntityFields: (entityType: string) =>
    apiClient.get<CustomFieldDefinition[]>(`${BASE}/entity/${entityType}`).then(r => r.data),
  getMetadata: () =>
    apiClient.get<Record<string, unknown>>(`${BASE}/metadata`).then(r => r.data),
  getUsageStats: () =>
    apiClient.get<UsageStat[]>(`${BASE}/usage-stats`).then(r => r.data),

  getValues: (entityType: string, entityId: string) =>
    apiClient.get<FieldValueOut[]>(`${VALUES_BASE}/${entityType}/${entityId}`).then(r => r.data),
  setValues: (entityType: string, entityId: string, values: Record<string, unknown>, updatedBy = "User") =>
    apiClient.post<FieldValueOut[]>(`${VALUES_BASE}/${entityType}/${entityId}`, { values, updated_by: updatedBy }).then(r => r.data),
  validateValues: (entityType: string, entityId: string, values: Record<string, unknown>) =>
    apiClient.post<ValidationResult>(`${VALUES_BASE}/${entityType}/${entityId}/validate`, { values }).then(r => r.data),
  getMissingRequired: (entityType: string) =>
    apiClient.get<{ entity_id: string; field_code: string; field_label: string }[]>(
      `${VALUES_BASE}/${entityType}/missing-required`
    ).then(r => r.data),

  listAIRecs: () =>
    apiClient.get<CFAIRec[]>(`${BASE}/ai/recs`).then(r => r.data),
  runFieldDesignAssistant: () =>
    apiClient.post<{ generated: number }>(`${BASE}/ai/run/field-design-assistant`).then(r => r.data),
  runDataQualityMonitor: () =>
    apiClient.post<{ generated: number }>(`${BASE}/ai/run/data-quality-monitor`).then(r => r.data),
  runReportingAssistant: () =>
    apiClient.post<{ generated: number }>(`${BASE}/ai/run/reporting-assistant`).then(r => r.data),
  ackAIRec: (id: string, data: { status: CFAIRecStatus }) =>
    apiClient.patch<CFAIRec>(`${BASE}/ai/recs/${id}`, data).then(r => r.data),

  getFormLayout: (entityType: string) =>
    apiClient.get<CustomFieldDefinition[]>(`${BASE}/form-layout/${entityType}`).then(r => r.data),
  reorderFormLayout: (entityType: string, items: FormLayoutItem[]) =>
    apiClient.post<CustomFieldDefinition[]>(`${BASE}/form-layout/${entityType}/reorder`, { items }).then(r => r.data),

  listWorkflowRules: (params?: { entity_type?: string; active_only?: boolean }) =>
    apiClient.get<WorkflowRule[]>(`${BASE}/workflow-rules`, { params }).then(r => r.data),
  createWorkflowRule: (data: object) =>
    apiClient.post<WorkflowRule>(`${BASE}/workflow-rules`, data).then(r => r.data),
  updateWorkflowRule: (id: string, data: object) =>
    apiClient.patch<WorkflowRule>(`${BASE}/workflow-rules/${id}`, data).then(r => r.data),
  deleteWorkflowRule: (id: string) =>
    apiClient.delete<{ ok: boolean }>(`${BASE}/workflow-rules/${id}`).then(r => r.data),
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

export const WF_TRIGGER_LABEL: Record<string, string> = {
  record_created: "Record Created",
  record_updated: "Record Updated",
  field_changed: "Field Value Changed",
  value_equals: "Field Value Equals",
  value_gt: "Field Value Greater Than",
  value_lt: "Field Value Less Than",
};

export const WF_ACTION_LABEL: Record<string, string> = {
  send_notification: "Send Notification",
  set_field_value: "Set Field Value",
  assign_tag: "Assign Tag",
  trigger_workflow: "Trigger Another Workflow",
  webhook_call: "Call Webhook",
};

export const FIELD_WIDTH_LABEL: Record<string, string> = {
  full: "Full Width",
  half: "Half Width",
  third: "One Third",
};
