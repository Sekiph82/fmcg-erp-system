import apiClient from "@/lib/api";

// ── Enums ────────────────────────────────────────────────────────────────────

export type FlowType =
  | "RAW_ISSUE" | "PKG_ISSUE" | "CONSUMABLE_ISSUE"
  | "WEIGHING_TRANSFER" | "STAGE_TRANSFER"
  | "INTERMEDIATE_CREATE" | "BULK_TRANSFER"
  | "TANK_FILL" | "TANK_TRANSFER" | "LINE_TRANSFER"
  | "FG_RECEIPT" | "RETURN" | "REVERSAL"
  | "SCRAP" | "REWORK" | "RECONCILIATION";

export type FlowStatus = "DRAFT" | "PENDING" | "CONFIRMED" | "POSTED" | "REVERSED" | "CANCELLED";

export type FlowMode = "ONE_STEP" | "TWO_STEP" | "THREE_STEP" | "MULTI_STAGE";

export type StageType =
  | "RAW_WAREHOUSE" | "QUARANTINE_RAW" | "WEIGHING_ROOM" | "STAGED_LINE"
  | "MIXING" | "PREMIX" | "INTERMEDIATE_HOLD" | "BULK_TANK" | "QC_HOLD_TANK"
  | "RELEASED_BULK" | "FILLING_STAGING" | "PACKAGING_STAGING"
  | "SECONDARY_PACKING" | "PALLETIZATION" | "FG_QUARANTINE" | "FG_RELEASED"
  | "REWORK_HOLDING" | "SCRAP_HOLDING" | "TRANSIT";

export type QualityStatus =
  | "QUARANTINE" | "PENDING_INSPECTION" | "RELEASED" | "QC_HOLD"
  | "BLOCKED" | "REJECTED" | "REWORK_PENDING";

export type ReservationStatus = "ACTIVE" | "PARTIALLY_ISSUED" | "FULLY_ISSUED" | "EXPIRED" | "CANCELLED";

export type TankStatus = "EMPTY" | "FILLING" | "FULL" | "IN_USE" | "QC_HOLD" | "CLEANING" | "OUT_OF_SERVICE";

export type ReconciliationStatus = "OPEN" | "IN_PROGRESS" | "PENDING_APPROVAL" | "APPROVED" | "CLOSED";

export type MFAIAgentType = "VARIANCE_ANALYZER" | "FLOW_OPTIMIZER" | "RISK_MONITOR";

export type MFAIRecStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "APPLIED";

// ── Types ────────────────────────────────────────────────────────────────────

export interface FlowStage {
  id: string;
  stage_code: string;
  stage_name: string;
  stage_type: StageType;
  plant_id?: string;
  warehouse_id?: string;
  warehouse_name?: string;
  quality_default_status: QualityStatus;
  sequence_no: number;
  active_flag: boolean;
  notes?: string;
}

export interface FlowLine {
  id: string;
  transaction_id: string;
  line_no: number;
  item_type: string;
  material_id?: string;
  product_id?: string;
  lot_id?: string;
  batch_id?: string;
  quantity: number;
  uom: string;
  source_warehouse_id?: string;
  destination_warehouse_id?: string;
  source_stage_id?: string;
  destination_stage_id?: string;
  source_stage_name?: string;
  destination_stage_name?: string;
  quality_status: QualityStatus;
  movement_reason: string;
  issue_flag: boolean;
  return_flag: boolean;
  scrap_flag: boolean;
  material_name?: string;
  product_name?: string;
  lot_number?: string;
}

export interface FlowTransaction {
  id: string;
  flow_no: string;
  flow_type: FlowType;
  flow_mode: FlowMode;
  status: FlowStatus;
  production_order_id?: string;
  transaction_datetime: string;
  plant_id?: string;
  notes?: string;
  lines: FlowLine[];
}

export interface FlowTransactionCreate {
  flow_type: FlowType;
  flow_mode?: FlowMode;
  production_order_id?: string;
  notes?: string;
  lines: Partial<FlowLine>[];
}

export interface Reservation {
  id: string;
  reservation_no: string;
  production_order_id: string;
  status: ReservationStatus;
  expiry_datetime?: string;
  lines: ReservationLine[];
}

export interface ReservationLine {
  id: string;
  reservation_id: string;
  line_no: number;
  item_type: string;
  material_id?: string;
  warehouse_id: string;
  quantity_required: number;
  quantity_reserved: number;
  quantity_issued: number;
  uom: string;
  material_name?: string;
  lot_number?: string;
}

export interface Consumption {
  id: string;
  production_order_id: string;
  material_id?: string;
  quantity_issued: number;
  quantity_consumed: number;
  quantity_returned: number;
  quantity_scrapped: number;
  quantity_variance: number;
  variance_pct?: number;
  uom: string;
  consumed_at?: string;
  material_name?: string;
}

export interface PreparedLot {
  id: string;
  prepared_lot_no: string;
  production_order_id?: string;
  material_id: string;
  target_quantity: number;
  actual_quantity?: number;
  uom: string;
  over_weigh: boolean;
  under_weigh: boolean;
  quality_status: QualityStatus;
  consumed: boolean;
  weighed_at?: string;
  material_name?: string;
}

export interface TankOccupancy {
  id: string;
  tank_code: string;
  tank_name: string;
  stage_id?: string;
  warehouse_id?: string;
  capacity_max?: number;
  uom: string;
  product_id?: string;
  material_id?: string;
  lot_id?: string;
  production_order_id?: string;
  quantity_current: number;
  quantity_reserved: number;
  quality_status: QualityStatus;
  tank_status: TankStatus;
  fill_datetime?: string;
  release_datetime?: string;
  product_name?: string;
  material_name?: string;
  fill_pct?: number;
}

export interface Reconciliation {
  id: string;
  reconciliation_no: string;
  production_order_id: string;
  status: ReconciliationStatus;
  total_issued: number;
  total_consumed: number;
  total_returned: number;
  total_scrapped: number;
  total_variance: number;
  variance_pct?: number;
  output_planned?: number;
  output_actual?: number;
  output_variance?: number;
  variance_reason?: string;
  approved_at?: string;
  closed_at?: string;
  lines: ReconciliationLine[];
}

export interface ReconciliationLine {
  id: string;
  line_no: number;
  material_id?: string;
  bom_quantity?: number;
  issued_quantity: number;
  consumed_quantity: number;
  returned_quantity: number;
  scrapped_quantity: number;
  variance_quantity: number;
  variance_pct?: number;
  uom: string;
  cost_impact?: number;
  material_name?: string;
}

export interface MFAIRec {
  id: string;
  agent_type: MFAIAgentType;
  status: MFAIRecStatus;
  production_order_id?: string;
  title: string;
  description: string;
  severity: string;
  confidence_score?: number;
  estimated_impact?: string;
  actioned_at?: string;
}

export interface MFDashboard {
  total_flows_today: number;
  total_issued_today: number;
  active_reservations: number;
  open_reconciliations: number;
  tanks_in_use: number;
  tanks_qc_hold: number;
  pending_ai_recs: number;
  total_wip_quantity: number;
  recent_flows: FlowTransaction[];
  ai_recommendations: MFAIRec[];
}

// ── Label / Color Maps ────────────────────────────────────────────────────────

export const FLOW_TYPE_LABELS: Record<FlowType, string> = {
  RAW_ISSUE: "Raw Material Issue",
  PKG_ISSUE: "Packaging Issue",
  CONSUMABLE_ISSUE: "Consumable Issue",
  WEIGHING_TRANSFER: "Weighing Transfer",
  STAGE_TRANSFER: "Stage Transfer",
  INTERMEDIATE_CREATE: "Intermediate Create",
  BULK_TRANSFER: "Bulk Transfer",
  TANK_FILL: "Tank Fill",
  TANK_TRANSFER: "Tank Transfer",
  LINE_TRANSFER: "Line Transfer",
  FG_RECEIPT: "FG Receipt",
  RETURN: "Return",
  REVERSAL: "Reversal",
  SCRAP: "Scrap",
  REWORK: "Rework",
  RECONCILIATION: "Reconciliation",
};

export const FLOW_STATUS_COLORS: Record<FlowStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-700",
  PENDING: "bg-yellow-100 text-yellow-700",
  CONFIRMED: "bg-blue-100 text-blue-700",
  POSTED: "bg-green-100 text-green-700",
  REVERSED: "bg-orange-100 text-orange-700",
  CANCELLED: "bg-red-100 text-red-700",
};

export const QUALITY_STATUS_COLORS: Record<QualityStatus, string> = {
  QUARANTINE: "bg-yellow-100 text-yellow-700",
  PENDING_INSPECTION: "bg-blue-100 text-blue-700",
  RELEASED: "bg-green-100 text-green-700",
  QC_HOLD: "bg-orange-100 text-orange-700",
  BLOCKED: "bg-red-100 text-red-800",
  REJECTED: "bg-red-200 text-red-900",
  REWORK_PENDING: "bg-purple-100 text-purple-700",
};

export const TANK_STATUS_COLORS: Record<TankStatus, string> = {
  EMPTY: "bg-gray-100 text-gray-600",
  FILLING: "bg-blue-100 text-blue-700",
  FULL: "bg-green-100 text-green-700",
  IN_USE: "bg-emerald-100 text-emerald-700",
  QC_HOLD: "bg-orange-100 text-orange-700",
  CLEANING: "bg-cyan-100 text-cyan-700",
  OUT_OF_SERVICE: "bg-red-100 text-red-700",
};

export const AI_AGENT_LABELS: Record<MFAIAgentType, string> = {
  VARIANCE_ANALYZER: "Variance Analyzer",
  FLOW_OPTIMIZER: "Flow Optimizer",
  RISK_MONITOR: "Risk Monitor",
};

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

// ── API Client ────────────────────────────────────────────────────────────────

const BASE = "/api/v1/material-flow";

export const mfApi = {
  getDashboard: () => apiClient.get<MFDashboard>(`${BASE}/dashboard`),

  // Stages
  listStages: () => apiClient.get<FlowStage[]>(`${BASE}/stages`),
  createStage: (d: Partial<FlowStage>) => apiClient.post<FlowStage>(`${BASE}/stages`, d),

  // Transactions
  listTransactions: (params?: Record<string, string>) =>
    apiClient.get<FlowTransaction[]>(`${BASE}/transactions`, { params }),
  getTransaction: (id: string) => apiClient.get<FlowTransaction>(`${BASE}/transactions/${id}`),
  createTransaction: (d: FlowTransactionCreate) => apiClient.post<FlowTransaction>(`${BASE}/transactions`, d),
  confirmTransaction: (id: string) => apiClient.post<FlowTransaction>(`${BASE}/transactions/${id}/confirm`, {}),
  reverseTransaction: (id: string) => apiClient.post<FlowTransaction>(`${BASE}/transactions/${id}/reverse`, {}),

  // Issues / Returns / Transfers / FG
  issueMaterials: (d: FlowTransactionCreate) => apiClient.post<FlowTransaction>(`${BASE}/issues`, d),
  returnMaterials: (d: FlowTransactionCreate) => apiClient.post<FlowTransaction>(`${BASE}/returns`, d),
  transferMaterials: (d: FlowTransactionCreate) => apiClient.post<FlowTransaction>(`${BASE}/transfers`, d),
  fgReceipt: (d: FlowTransactionCreate) => apiClient.post<FlowTransaction>(`${BASE}/fg-receipts`, d),

  // Reservations
  listReservations: (params?: Record<string, string>) =>
    apiClient.get<Reservation[]>(`${BASE}/reservations`, { params }),
  getReservation: (id: string) => apiClient.get<Reservation>(`${BASE}/reservations/${id}`),
  createReservation: (d: object) => apiClient.post<Reservation>(`${BASE}/reservations`, d),
  cancelReservation: (id: string) => apiClient.post<Reservation>(`${BASE}/reservations/${id}/cancel`, {}),

  // Consumptions
  recordConsumption: (d: object) => apiClient.post<Consumption>(`${BASE}/consumptions`, d),
  listConsumptions: (orderId: string) => apiClient.get<Consumption[]>(`${BASE}/consumptions/${orderId}`),

  // Prepared lots
  listPreparedLots: (params?: Record<string, string>) =>
    apiClient.get<PreparedLot[]>(`${BASE}/prepared-lots`, { params }),
  createPreparedLot: (d: object) => apiClient.post<PreparedLot>(`${BASE}/prepared-lots`, d),
  recordWeigh: (id: string, d: object) => apiClient.post<PreparedLot>(`${BASE}/prepared-lots/${id}/weigh`, d),

  // Tanks
  listTanks: (params?: Record<string, string>) => apiClient.get<TankOccupancy[]>(`${BASE}/tanks`, { params }),
  getTank: (id: string) => apiClient.get<TankOccupancy>(`${BASE}/tanks/${id}`),
  createTank: (d: object) => apiClient.post<TankOccupancy>(`${BASE}/tanks`, d),
  updateTank: (id: string, d: object) => apiClient.patch<TankOccupancy>(`${BASE}/tanks/${id}`, d),

  // Reconciliation
  getReconciliation: (orderId: string) => apiClient.get<Reconciliation>(`${BASE}/reconciliation/${orderId}`),
  closeReconciliation: (orderId: string, d?: object) =>
    apiClient.post<Reconciliation>(`${BASE}/reconciliation/${orderId}/close`, d || {}),

  // History
  getHistory: (params?: Record<string, string>) =>
    apiClient.get<FlowTransaction[]>(`${BASE}/history`, { params }),

  // AI
  runAI: (orderId?: string) =>
    apiClient.post<MFAIRec[]>(`${BASE}/ai/run`, {}, { params: orderId ? { production_order_id: orderId } : {} }),
  listAIRecs: (params?: Record<string, string>) =>
    apiClient.get<MFAIRec[]>(`${BASE}/ai/recommendations`, { params }),
  actionAIRec: (id: string, status: MFAIRecStatus, notes?: string) =>
    apiClient.post<MFAIRec>(`${BASE}/ai/recommendations/${id}/action`, { status, notes }),
};
