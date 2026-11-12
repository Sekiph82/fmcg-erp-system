import axios from "axios";
import type { CommercialAccessHint, CommercialScopeFields } from "@/lib/sales";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/api/v1";
const r = <T>(p: Promise<{ data: T }>) => p.then((res) => res.data);
const ax = axios.create({ baseURL: API, withCredentials: true });

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

export interface CRMRecord extends CommercialScopeFields {
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
  assigned_customer_id?: string;
  distributor_id?: string;
  source_type: CRMSourceType;
  region_id?: string;
  channel_id?: string;
  assigned_rep_id?: string;
  assigned_team_id?: string;
  stage_id?: string;
  territory_id?: string;
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
  access?: CommercialAccessHint | null;
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

export interface CRMTerritory extends CommercialScopeFields {
  id: string;
  territory_code: string;
  territory_name: string;
  region?: string;
  parent_territory_id?: string;
  assigned_rep_ids?: string;
  active_flag: boolean;
  notes?: string;
  created_at?: string;
  access?: CommercialAccessHint | null;
}

export interface CRMTerritoryPerformance {
  territory_id: string;
  territory_name: string;
  region?: string;
  assigned_rep_ids?: string;
  total_records: number;
  open_records: number;
  won_records: number;
  lost_records: number;
  pipeline_value: number;
  weighted_value: number;
  win_rate_pct: number;
}

export interface CRM360View {
  record_id: string;
  company_name: string;
  record_type: string;
  status: string;
  lead_score: number;
  temperature: string;
  pipeline_age_days: number;
  days_since_last_activity?: number;
  last_activity_type?: string;
  total_activities: number;
  completed_activities: number;
  overdue_activities: number;
  activity_completion_rate: number;
  communication_risk: string;
  interest_product_count: number;
  expected_revenue: number;
  probability_pct: number;
  weighted_value: number;
  deal_risk_flag: boolean;
  credit_signal: string;
  qualified_flag: boolean;
  territory_name?: string;
  assigned_rep_id?: string;
  next_action_date?: string;
  expected_close_date?: string;
  days_to_close?: number;
  activity_health_score: number;
  summary_flags: string[];
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

  // Territories
  getTerritories: (activeOnly = false) => r(ax.get<CRMTerritory[]>(`/crm/territories`, { params: { active_only: activeOnly } })),
  createTerritory: (data: Partial<CRMTerritory>) => r(ax.post<CRMTerritory>(`/crm/territories`, data)),
  updateTerritory: (id: string, data: Partial<CRMTerritory>) => r(ax.patch<CRMTerritory>(`/crm/territories/${id}`, data)),
  getTerritoryPerformance: () => r(ax.get<CRMTerritoryPerformance[]>(`/crm/territories/performance`)),

  // 360 View
  get360: (id: string) => r(ax.get<CRM360View>(`/crm/records/${id}/360`)),

  // M36.S02 scoring, forecast detail/snapshots, funnel
  getScoreRules: () => r(ax.get<ScoreRulesResponse>(`/crm/score-rules`)),
  createScoreRule: (data: ScoreRuleInput) => r(ax.post<ScoreRule>(`/crm/score-rules`, data)),
  updateScoreRule: (id: string, data: Partial<ScoreRuleInput>) => r(ax.patch<ScoreRule>(`/crm/score-rules/${id}`, data)),
  seedScoreRules: () => r(ax.post<{ created: number }>(`/crm/score-rules/seed-defaults`)),
  recalculateScores: () => r(ax.post<{ scored: number; changed: number; rules: number }>(`/crm/scores/recalculate`)),
  getScoreQueue: (limit = 50) => r(ax.get<ScoreQueueItem[]>(`/crm/scores/queue`, { params: { limit } })),
  getScoreHistory: (id: string) => r(ax.get<ScoreHistoryItem[]>(`/crm/records/${id}/score-history`)),
  getForecastDetail: (params: ForecastFilters) => r(ax.get<ForecastDetail>(`/crm/forecast/detail`, { params })),
  createForecastSnapshot: (data: ForecastFilters & { label?: string }) => r(ax.post<ForecastSnapshot>(`/crm/forecast/snapshots`, data)),
  listForecastSnapshots: () => r(ax.get<ForecastSnapshot[]>(`/crm/forecast/snapshots`)),
  getForecastSnapshot: (id: string) => r(ax.get<ForecastSnapshot>(`/crm/forecast/snapshots/${id}`)),
  getFunnel: (params: FunnelFilters) => r(ax.get<FunnelReport>(`/crm/reports/funnel`, { params })),
  getCustomerTimeline: (customerId: string, params: { limit?: number; before?: string; types?: string }) =>
    r(ax.get<CustomerTimeline>(`/crm/customers/${customerId}/timeline`, { params })),
  listLeadForms: () => r(ax.get<LeadForm[]>(`/crm/lead-forms`)),
  createLeadForm: (data: Partial<LeadForm>) => r(ax.post<LeadForm>(`/crm/lead-forms`, data)),
  updateLeadForm: (id: string, data: Partial<LeadForm>) => r(ax.patch<LeadForm>(`/crm/lead-forms/${id}`, data)),
  listLeadSubmissions: (id: string) => r(ax.get<LeadSubmissionRow[]>(`/crm/lead-forms/${id}/submissions`)),
};

export interface LeadForm {
  id: string; slug: string; name: string; title: string; intro: string | null; consent_text: string | null;
  require_consent: boolean; success_message: string | null; active_flag: boolean; assigned_rep_id: string | null;
  territory_id: string | null; sales_region_id: string | null; sales_team_id: string | null;
}
export interface LeadSubmissionRow {
  id: string; received_at: string; status: string; crm_record_id: string | null; contact_email: string | null;
  consent_given: boolean; utm_source: string | null; utm_medium: string | null; utm_campaign: string | null;
  referrer: string | null; landing_page: string | null;
}

export interface TimelineEvent {
  key: string; type: string; at: string; title: string; status: string | null; ref: string | null;
  link: string | null; detail: string | null;
}
export interface CustomerTimeline {
  customer: { id: string; code: string; name: string };
  events: TimelineEvent[]; next: string | null; hidden_sources: string[];
}

export interface ScoreBreakdownItem { rule: string; category: string; points: number; reason: string }
export interface ScoreRuleInput {
  name: string; category: "FIT" | "ENGAGEMENT"; field: string; operator: string; value?: string | null;
  points: number; max_points?: number | null; active_flag?: boolean; sequence_no?: number;
}
export interface ScoreRule extends ScoreRuleInput { id: string; active_flag: boolean; sequence_no: number }
export interface ScoreRulesResponse {
  rules: ScoreRule[]; using_defaults: boolean; defaults: ScoreRuleInput[]; fields: Record<string, string>;
}
export interface ScoreQueueItem {
  id: string; lead_code: string | null; company_name: string; lead_score: number; temperature: string;
  assigned_rep_id: string | null; breakdown: ScoreBreakdownItem[] | null;
}
export interface ScoreHistoryItem {
  score: number; previous_score: number | null; temperature: string; breakdown: ScoreBreakdownItem[];
  computed_at: string; computed_by: string | null;
}
export interface ForecastFilters { months_ahead?: number; assigned_rep_id?: string; territory_id?: string; stage_id?: string }
export interface ForecastCell { expected_revenue: number; weighted_revenue: number; deal_count: number }
export interface ForecastDetail {
  filters: ForecastFilters & { start: string }; currencies: string[];
  rows: (ForecastCell & { month: string; currency: string })[];
  by_stage: (ForecastCell & { stage: string; currency: string })[];
  overdue_open: (ForecastCell & { currency: string })[];
}
export interface ForecastSnapshot extends Partial<ForecastDetail> { id: string; label: string | null; taken_at: string }
export interface FunnelFilters { date_from?: string; date_to?: string; assigned_rep_id?: string; territory_id?: string }
export interface FunnelReport {
  records: number;
  funnel: { stage_id: string; stage: string; sequence: number; reached: number; conversion_from_previous_pct: number | null }[];
  aging: { stage: string; open: number; avg_days: number; max_days: number; over_30_days: number }[];
  reps: { assigned_rep_id: string; total: number; open: number; won: number; lost: number; win_rate_pct: number | null;
          won_revenue_by_currency: Record<string, number>; avg_cycle_days: number | null }[];
  loss_reasons: { reason: string; count: number }[];
}
