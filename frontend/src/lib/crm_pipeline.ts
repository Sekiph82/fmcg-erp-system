import axios from "axios";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/api/v1";
const r = <T>(p: Promise<{ data: T }>) => p.then((res) => res.data);
const ax = axios.create({ baseURL: API });

// ── Types ─────────────────────────────────────────────────────────────────────

export type CRMRecordType   = "LEAD" | "OPPORTUNITY";
export type CRMAccountType  = "PROSPECT" | "CUSTOMER" | "DISTRIBUTOR" | "RETAILER" | "MODERN_TRADE" | "INSTITUTIONAL" | "SUPPLIER_XSELL" | "OTHER";
export type CRMSourceType   = "WEBSITE" | "REFERRAL" | "FIELD_SALES" | "EVENT" | "OUTBOUND" | "INBOUND" | "CAMPAIGN" | "MANUAL" | "IMPORT";
export type CRMStageType    = "LEAD" | "OPPORTUNITY" | "TERMINAL" | "NURTURING";
export type CRMTemperature  = "COLD" | "WARM" | "HOT";
export type CRMStatus       = "OPEN" | "WON" | "LOST" | "ON_HOLD" | "ARCHIVED";
export type CRMActivityType = "CALL" | "EMAIL" | "MEETING" | "WHATSAPP" | "VISIT" | "TASK" | "NOTE" | "DEMO" | "SAMPLE_SENT" | "QUOTATION_SENT" | "NEGOTIATION" | "COMPLAINT_FOLLOWUP" | "OTHER";
export type CRMActivityResult = "PLANNED" | "COMPLETED" | "NO_RESPONSE" | "RESCHEDULED" | "CANCELLED";
export type CRMLossReason   = "PRICE_TOO_HIGH" | "COMPETITOR_RELATION" | "PRODUCT_MISMATCH" | "TIMELINE_ISSUE" | "NO_BUDGET" | "NO_RESPONSE" | "COMPETITOR_PROMO" | "DISTRIBUTOR_CONFLICT" | "CAPACITY_SUPPLY" | "INTERNAL_FOLLOWUP" | "OTHER";
export type CRMWinReason    = "BETTER_PRICE" | "BETTER_PRODUCT_FIT" | "FASTER_RESPONSE" | "STRONGER_RELATION" | "AVAILABILITY" | "TECHNICAL_SUPPORT" | "PROMOTION_SUPPORT" | "OTHER";
export type CRMAIAgentType  = "LEAD_PRIORITIZATION" | "PIPELINE_RISK" | "WIN_LOSS_INSIGHT";
export type CRMAIRecStatus  = "PENDING" | "ACKNOWLEDGED" | "ACTIONED" | "DISMISSED";

export interface CRMStage {
  id: string;
  stage_code: string;
  stage_name: string;
  stage_type: CRMStageType;
  default_probability: number;
  sequence_no: number;
  active_flag: boolean;
  color_code?: string;
  notes?: string;
  created_at?: string;
}

export interface CRMInterestLine {
  id: string;
  crm_record_id: string;
  item_id?: string;
  item_name?: string;
  category_id?: string;
  brand_id?: string;
  expected_qty?: number;
  expected_frequency?: string;
  expected_value?: number;
  competitive_brand?: string;
  competitor_price?: number;
  notes?: string;
}

export interface CRMActivity {
  id: string;
  crm_record_id: string;
  activity_type: CRMActivityType;
  subject: string;
  description?: string;
  activity_datetime?: string;
  due_datetime?: string;
  completed_datetime?: string;
  assigned_to?: string;
  created_by?: string;
  result_status: CRMActivityResult;
  outcome_code?: string;
  next_step?: string;
  notes?: string;
  created_at?: string;
}

export interface CRMCompetitor {
  id: string;
  crm_record_id: string;
  competitor_name: string;
  competitor_product?: string;
  offer_type?: string;
  competitor_price?: number;
  competitor_strength?: string;
  competitor_weakness?: string;
  risk_level?: string;
  notes?: string;
  created_at?: string;
}

export interface CRMWinLoss {
  id: string;
  crm_record_id: string;
  final_status: string;
  close_date?: string;
  final_revenue?: number;
  final_margin?: number;
  loss_reason_code?: CRMLossReason;
  win_reason_code?: CRMWinReason;
  competitor_name?: string;
  narrative?: string;
  recorded_by?: string;
  notes?: string;
}

export interface CRMRecord {
  id: string;
  record_type: CRMRecordType;
  lead_code?: string;
  opportunity_code?: string;
  account_type: CRMAccountType;
  company_name: string;
  contact_person_name?: string;
  contact_email?: string;
  contact_phone?: string;
  customer_id?: string;
  distributor_id?: string;
  source_type: CRMSourceType;
  region_id?: string;
  channel_id?: string;
  assigned_rep_id?: string;
  assigned_team_id?: string;
  stage_id?: string;
  stage?: CRMStage;
  probability_pct?: number;
  expected_close_date?: string;
  expected_revenue?: number;
  expected_margin?: number;
  currency: string;
  lead_score: number;
  temperature: CRMTemperature;
  next_action_date?: string;
  status: CRMStatus;
  qualified_flag: boolean;
  qualified_date?: string;
  converted_date?: string;
  linked_quotation_id?: string;
  linked_order_id?: string;
  created_by?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
  interest_lines?: CRMInterestLine[];
  activities?: CRMActivity[];
  competitors?: CRMCompetitor[];
  win_loss?: CRMWinLoss;
}

export interface CRMAIRec {
  id: string;
  agent_type: CRMAIAgentType;
  crm_record_id?: string;
  title: string;
  body: string;
  priority?: string;
  action_label?: string;
  status: CRMAIRecStatus;
  acknowledged_by?: string;
  notes?: string;
  created_at?: string;
}

export interface CRMDashboard {
  total_leads: number;
  total_opportunities: number;
  open_records: number;
  won_this_month: number;
  lost_this_month: number;
  total_pipeline_value: number;
  weighted_pipeline_value: number;
  overdue_activities: number;
  hot_records: number;
  conversion_rate_pct: number;
  avg_deal_size: number;
  stage_distribution: { stage: string; color: string; count: number; value: number }[];
  top_reps: { rep: string; count: number; value: number }[];
}

// ── Label Maps ─────────────────────────────────────────────────────────────────

export const STAGE_TYPE_LABELS: Record<CRMStageType, string> = {
  LEAD: "Lead Stage",
  OPPORTUNITY: "Opportunity Stage",
  TERMINAL: "Terminal",
  NURTURING: "Nurturing",
};

export const TEMPERATURE_LABELS: Record<CRMTemperature, string> = {
  COLD: "Cold",
  WARM: "Warm",
  HOT: "Hot",
};

export const TEMPERATURE_COLORS: Record<CRMTemperature, string> = {
  COLD: "#6B7280",
  WARM: "#F59E0B",
  HOT: "#EF4444",
};

export const STATUS_LABELS: Record<CRMStatus, string> = {
  OPEN: "Open",
  WON: "Won",
  LOST: "Lost",
  ON_HOLD: "On Hold",
  ARCHIVED: "Archived",
};

export const STATUS_COLORS: Record<CRMStatus, string> = {
  OPEN: "#3B82F6",
  WON: "#10B981",
  LOST: "#EF4444",
  ON_HOLD: "#F59E0B",
  ARCHIVED: "#6B7280",
};

export const ACTIVITY_TYPE_LABELS: Record<CRMActivityType, string> = {
  CALL: "Call",
  EMAIL: "Email",
  MEETING: "Meeting",
  WHATSAPP: "WhatsApp",
  VISIT: "Site Visit",
  TASK: "Task",
  NOTE: "Note",
  DEMO: "Demo",
  SAMPLE_SENT: "Sample Sent",
  QUOTATION_SENT: "Quotation Sent",
  NEGOTIATION: "Negotiation",
  COMPLAINT_FOLLOWUP: "Complaint Follow-up",
  OTHER: "Other",
};

export const ACTIVITY_RESULT_LABELS: Record<CRMActivityResult, string> = {
  PLANNED: "Planned",
  COMPLETED: "Completed",
  NO_RESPONSE: "No Response",
  RESCHEDULED: "Rescheduled",
  CANCELLED: "Cancelled",
};

export const SOURCE_LABELS: Record<CRMSourceType, string> = {
  WEBSITE: "Website",
  REFERRAL: "Referral",
  FIELD_SALES: "Field Sales",
  EVENT: "Event / Trade Show",
  OUTBOUND: "Outbound Call",
  INBOUND: "Inbound Inquiry",
  CAMPAIGN: "Campaign",
  MANUAL: "Manual Entry",
  IMPORT: "Import",
};

export const LOSS_REASON_LABELS: Record<CRMLossReason, string> = {
  PRICE_TOO_HIGH: "Price Too High",
  COMPETITOR_RELATION: "Competitor Relationship",
  PRODUCT_MISMATCH: "Product Mismatch",
  TIMELINE_ISSUE: "Timeline Issue",
  NO_BUDGET: "No Budget",
  NO_RESPONSE: "No Response",
  COMPETITOR_PROMO: "Competitor Promotion",
  DISTRIBUTOR_CONFLICT: "Distributor Conflict",
  CAPACITY_SUPPLY: "Capacity / Supply Issue",
  INTERNAL_FOLLOWUP: "Internal Follow-up Failure",
  OTHER: "Other",
};

export const WIN_REASON_LABELS: Record<CRMWinReason, string> = {
  BETTER_PRICE: "Better Price",
  BETTER_PRODUCT_FIT: "Better Product Fit",
  FASTER_RESPONSE: "Faster Response",
  STRONGER_RELATION: "Stronger Relationship",
  AVAILABILITY: "Product Availability",
  TECHNICAL_SUPPORT: "Technical Support",
  PROMOTION_SUPPORT: "Promotion Support",
  OTHER: "Other",
};

export const AI_AGENT_LABELS: Record<CRMAIAgentType, string> = {
  LEAD_PRIORITIZATION: "Lead Prioritization Assistant",
  PIPELINE_RISK: "Pipeline Risk Monitor",
  WIN_LOSS_INSIGHT: "Win/Loss Insight Assistant",
};

export function fmtCurrency(val?: number | null, currency = "KES"): string {
  if (val == null) return "—";
  return `${currency} ${val.toLocaleString("en-KE", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

// ── API Client ─────────────────────────────────────────────────────────────────

export const crmApi = {
  // Stages
  getStages: (activeOnly = false) => r(ax.get<CRMStage[]>(`/crm/stages`, { params: { active_only: activeOnly } })),
  createStage: (data: Partial<CRMStage>) => r(ax.post<CRMStage>(`/crm/stages`, data)),
  updateStage: (id: string, data: Partial<CRMStage>) => r(ax.patch<CRMStage>(`/crm/stages/${id}`, data)),
  seedDefaultStages: () => r(ax.post<CRMStage[]>(`/crm/stages/seed-defaults`)),

  // Records
  getLeads: (params?: Record<string, unknown>) => r(ax.get<CRMRecord[]>(`/crm/leads`, { params })),
  createLead: (data: Partial<CRMRecord>) => r(ax.post<CRMRecord>(`/crm/leads`, data)),
  getOpportunities: (params?: Record<string, unknown>) => r(ax.get<CRMRecord[]>(`/crm/opportunities`, { params })),
  createOpportunity: (data: Partial<CRMRecord>) => r(ax.post<CRMRecord>(`/crm/opportunities`, data)),
  getAllRecords: (params?: Record<string, unknown>) => r(ax.get<CRMRecord[]>(`/crm/records`, { params })),
  getRecord: (id: string) => r(ax.get<CRMRecord>(`/crm/records/${id}`)),
  updateRecord: (id: string, data: Partial<CRMRecord>) => r(ax.patch<CRMRecord>(`/crm/records/${id}`, data)),

  // Lifecycle
  qualify: (id: string, data: Record<string, unknown>) => r(ax.post<CRMRecord>(`/crm/records/${id}/qualify`, data)),
  convert: (id: string, data: Record<string, unknown>) => r(ax.post<CRMRecord>(`/crm/records/${id}/convert-to-opportunity`, data)),
  closeWon: (id: string, data: Record<string, unknown>) => r(ax.post<CRMRecord>(`/crm/records/${id}/close-won`, data)),
  closeLost: (id: string, data: Record<string, unknown>) => r(ax.post<CRMRecord>(`/crm/records/${id}/close-lost`, data)),
  onHold: (id: string, notes?: string) => r(ax.post<CRMRecord>(`/crm/records/${id}/on-hold`, null, { params: { notes } })),
  reopen: (id: string) => r(ax.post<CRMRecord>(`/crm/records/${id}/reopen`)),
  updateScore: (id: string) => r(ax.post<CRMRecord>(`/crm/records/${id}/update-score`)),

  // Interest lines
  addInterestLine: (recordId: string, data: Partial<CRMInterestLine>) =>
    r(ax.post<CRMInterestLine>(`/crm/records/${recordId}/interest-lines`, data)),
  deleteInterestLine: (lineId: string) => ax.delete(`/crm/interest-lines/${lineId}`),

  // Activities
  getActivities: (params?: Record<string, unknown>) => r(ax.get<CRMActivity[]>(`/crm/activities`, { params })),
  createActivity: (data: Partial<CRMActivity>) => r(ax.post<CRMActivity>(`/crm/activities`, data)),
  completeActivity: (id: string, data: Record<string, unknown>) =>
    r(ax.post<CRMActivity>(`/crm/activities/${id}/complete`, data)),

  // Competitors
  addCompetitor: (data: Partial<CRMCompetitor>) => r(ax.post<CRMCompetitor>(`/crm/competitors`, data)),

  // Deduplication
  checkDuplicates: (companyName: string, email?: string, phone?: string) =>
    r(ax.get<CRMRecord[]>(`/crm/check-duplicates`, { params: { company_name: companyName, email, phone } })),

  // Dashboard & Reports
  getDashboard: () => r(ax.get<CRMDashboard>(`/crm/dashboard`)),
  getForecast: (monthsAhead = 6) => r(ax.get<Record<string, unknown>[]>(`/crm/forecast`, { params: { months_ahead: monthsAhead } })),
  getPipelineReport: () => r(ax.get<Record<string, unknown>[]>(`/crm/reports/pipeline`)),
  getWinLossReport: () => r(ax.get<Record<string, unknown>>(`/crm/reports/win-loss`)),

  // AI
  runLeadPrioritization: () => r(ax.post<{ generated: number; message: string }>(`/crm/ai/run-lead-prioritization`)),
  runPipelineRisk: () => r(ax.post<{ generated: number; message: string }>(`/crm/ai/run-pipeline-risk`)),
  runWinLossInsight: () => r(ax.post<{ generated: number; message: string }>(`/crm/ai/run-win-loss-insight`)),
  getAIRecs: (params?: Record<string, unknown>) => r(ax.get<CRMAIRec[]>(`/crm/ai/recommendations`, { params })),
  ackAIRec: (id: string, data: Record<string, unknown>) => r(ax.patch<CRMAIRec>(`/crm/ai/recommendations/${id}`, data)),
};
