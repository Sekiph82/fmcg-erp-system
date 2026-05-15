import { apiClient } from "@/lib/api";

export type PRStatus = "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "CONVERTED" | "REJECTED" | "CANCELLED";
export type RFQStatus = "DRAFT" | "SENT" | "RESPONSES_RECEIVED" | "AWARDED" | "CANCELLED";
export type RFQResponseStatus = "PENDING" | "SUBMITTED" | "AWARDED" | "REJECTED";
export type BPAStatus = "ACTIVE" | "EXPIRED" | "CANCELLED";
export type POStatus = "DRAFT" | "APPROVED" | "ORDERED" | "PARTIALLY_RECEIVED" | "RECEIVED" | "CANCELLED";
export type GRNStatus = "DRAFT" | "POSTED";
export type ImportShipmentStatus = "PENDING" | "IN_TRANSIT" | "ARRIVED" | "CUSTOMS_CLEARED" | "DELIVERED";
export type SupplierPaymentMethod = "bank" | "cash" | "mpesa";
export type POPaymentStatus = "pending" | "partially_paid" | "paid";
export type ProcurementApprovalDocumentType = "PR" | "PO" | "RFQ" | "BPA";

export interface ProcurementScopeFields {
  company_id?: string;
  branch_id?: string;
  cost_center_id?: string;
  department?: string;
}

export interface ProcurementAccessHint {
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
  can_approve: boolean;
  can_receive: boolean;
  can_post: boolean;
  can_cancel: boolean;
  can_export: boolean;
  can_import: boolean;
  view_only: boolean;
  reason?: string;
}

export interface PRLine {
  id: string;
  line_no: number;
  material_id?: string;
  material_name?: string;
  material_code?: string;
  product_id?: string;
  product_name?: string;
  product_sku?: string;
  description?: string;
  quantity: number;
  unit: string;
  estimated_unit_cost?: number;
  preferred_supplier_id?: string;
  preferred_supplier_name?: string;
  notes?: string;
}

export interface PR extends ProcurementScopeFields {
  id: string;
  pr_no: string;
  requester_id: string;
  requester_name?: string;
  required_date: string;
  notes?: string;
  status: PRStatus;
  approved_by_id?: string;
  approved_at?: string;
  rejection_reason?: string;
  created_at: string;
  line_count: number;
  access?: ProcurementAccessHint;
}

export interface PRDetail extends PR {
  lines: PRLine[];
}

export interface POLine {
  id: string;
  line_no: number;
  material_id?: string;
  material_name?: string;
  material_code?: string;
  product_id?: string;
  product_name?: string;
  product_sku?: string;
  pr_line_id?: string;
  description?: string;
  ordered_quantity: number;
  unit: string;
  unit_price: number;
  tax_rate: number;
  received_quantity: number;
  line_total: number;
  pending_quantity: number;
}

export interface SupplierPayment extends ProcurementScopeFields {
  id: string;
  po_id: string;
  supplier_id: string;
  payment_date: string;
  amount: number;
  method: SupplierPaymentMethod;
  reference?: string;
  notes?: string;
  created_at: string;
  access?: ProcurementAccessHint;
}

export interface PO extends ProcurementScopeFields {
  id: string;
  po_no: string;
  supplier_id: string;
  supplier_name?: string;
  pr_id?: string;
  pr_no?: string;
  order_date: string;
  expected_delivery_date: string;
  payment_terms?: string;
  currency: string;
  exchange_rate: number;
  status: POStatus;
  notes?: string;
  approved_by_id?: string;
  approved_at?: string;
  created_at: string;
  total_value?: number;
  days_until_delivery?: number;
  payment_status: POPaymentStatus;
  payment_method?: string;
  mpesa_reference?: string;
  paid_amount?: number;
  access?: ProcurementAccessHint;
}

export interface PODetail extends PO {
  lines: POLine[];
}

export interface GRNLine {
  id: string;
  po_line_id?: string;
  material_id?: string;
  material_name?: string;
  product_id?: string;
  product_name?: string;
  received_quantity: number;
  accepted_quantity: number;
  rejected_quantity: number;
  unit: string;
  lot_number?: string;
  expiry_date?: string;
  notes?: string;
  stock_movement_id?: string;
}

export interface GRN extends ProcurementScopeFields {
  id: string;
  grn_no: string;
  po_id: string;
  po_no?: string;
  received_date: string;
  received_by_id?: string;
  warehouse_id: string;
  warehouse_name?: string;
  notes?: string;
  status: GRNStatus;
  created_at: string;
  access?: ProcurementAccessHint;
}

export interface GRNDetail extends GRN {
  lines: GRNLine[];
}

export interface ImportShipment extends ProcurementScopeFields {
  id: string;
  shipment_no: string;
  po_id: string;
  po_no?: string;
  supplier_name?: string;
  bl_number?: string;
  vessel_name?: string;
  port_of_loading?: string;
  port_of_discharge?: string;
  eta?: string;
  ata?: string;
  customs_ref?: string;
  customs_cleared_at?: string;
  landed_cost_freight?: number;
  landed_cost_insurance?: number;
  landed_cost_duties?: number;
  landed_cost_other?: number;
  total_landed_cost: number;
  status: ImportShipmentStatus;
  notes?: string;
  created_at: string;
  access?: ProcurementAccessHint;
}

export interface SupplierEvaluation extends ProcurementScopeFields {
  id: string;
  supplier_id: string;
  evaluation_date: string;
  po_id?: string;
  po_no?: string;
  on_time_delivery_score: number;
  quality_score: number;
  price_competitiveness_score: number;
  responsiveness_score: number;
  overall_score: number;
  evaluator_id?: string;
  notes?: string;
  created_at: string;
  access?: ProcurementAccessHint;
}

export interface SupplierDashboardRow extends ProcurementScopeFields {
  supplier_id: string;
  supplier_name: string;
  supplier_code: string;
  is_preferred: boolean;
  lead_time_days: number;
  performance_score?: number;
  compliance_notes?: string;
  total_pos: number;
  open_pos: number;
  overdue_pos: number;
  avg_on_time_delivery?: number;
  avg_quality?: number;
  avg_overall?: number;
  last_evaluation_date?: string;
  access?: ProcurementAccessHint;
}

export interface InboundScheduleRow {
  po_id: string;
  po_no: string;
  supplier_name: string;
  expected_delivery_date: string;
  days_until_delivery: number;
  status: POStatus;
  total_value?: number;
  is_overdue: boolean;
  has_shipment: boolean;
  shipment_eta?: string;
}

export interface DeliveryAlertRow {
  alert_type: "OVERDUE" | "APPROACHING" | "NO_SHIPMENT";
  po_id: string;
  po_no: string;
  supplier_name: string;
  expected_delivery_date: string;
  days_delta: number;
  message: string;
}

export interface RFQResponseRead {
  id: string;
  rfq_id: string;
  supplier_id: string;
  supplier_name?: string;
  quoted_unit_price?: number;
  quoted_currency: string;
  lead_time_days?: number;
  valid_until?: string;
  payment_terms?: string;
  notes?: string;
  status: RFQResponseStatus;
  score?: number;
  created_at: string;
}

export interface RFQRead extends ProcurementScopeFields {
  id: string;
  rfq_no: string;
  pr_id?: string;
  title: string;
  material_id?: string;
  product_id?: string;
  description?: string;
  quantity: number;
  unit: string;
  required_by?: string;
  response_deadline?: string;
  status: RFQStatus;
  awarded_supplier_id?: string;
  awarded_supplier_name?: string;
  notes?: string;
  created_at: string;
  response_count: number;
  access?: ProcurementAccessHint;
}

export interface RFQDetail extends RFQRead {
  responses: RFQResponseRead[];
}

export interface BlanketAgreement extends ProcurementScopeFields {
  id: string;
  bpa_no: string;
  supplier_id: string;
  supplier_name?: string;
  material_id?: string;
  product_id?: string;
  description?: string;
  agreed_unit_price: number;
  currency: string;
  agreed_quantity?: number;
  consumed_quantity: number;
  remaining_quantity?: number;
  unit: string;
  valid_from: string;
  valid_to: string;
  payment_terms?: string;
  status: BPAStatus;
  is_expired: boolean;
  notes?: string;
  created_at: string;
  access?: ProcurementAccessHint;
}

export interface AutoReorderPolicy extends ProcurementScopeFields {
  id: string;
  material_id?: string;
  product_id?: string;
  warehouse_id?: string;
  reorder_point: number;
  reorder_quantity: number;
  max_stock_level?: number;
  lead_time_days: number;
  preferred_supplier_id?: string;
  preferred_supplier_name?: string;
  auto_create_pr: boolean;
  active_flag: boolean;
  notes?: string;
  created_at: string;
  access?: ProcurementAccessHint;
}

export interface ProcurementApprovalRule extends ProcurementScopeFields {
  id: string;
  rule_name: string;
  document_type: ProcurementApprovalDocumentType;
  supplier_category?: string;
  product_category?: string;
  min_amount?: number;
  max_amount?: number;
  currency?: string;
  approval_level: number;
  approver_user_id?: string;
  approver_role_id?: string;
  requires_all_matching_approvers: boolean;
  is_active: boolean;
  effective_from?: string;
  effective_to?: string;
  notes?: string;
  created_at: string;
}

export const procurementApi = {
  // PRs
  async listPRs(params?: { status?: PRStatus }): Promise<PR[]> {
    const res = await apiClient.get<PR[]>("/api/v1/procurement/pr/", { params });
    return res.data;
  },
  async getPR(id: string): Promise<PRDetail> {
    const res = await apiClient.get<PRDetail>(`/api/v1/procurement/pr/${id}`);
    return res.data;
  },
  async createPR(data: object): Promise<PRDetail> {
    const res = await apiClient.post<PRDetail>("/api/v1/procurement/pr/", data);
    return res.data;
  },
  async updatePR(id: string, data: object): Promise<PRDetail> {
    const res = await apiClient.patch<PRDetail>(`/api/v1/procurement/pr/${id}`, data);
    return res.data;
  },
  async submitPR(id: string): Promise<PR> {
    const res = await apiClient.post<PR>(`/api/v1/procurement/pr/${id}/submit`);
    return res.data;
  },
  async approvePR(id: string, approve: boolean, rejection_reason?: string): Promise<PR> {
    const res = await apiClient.post<PR>(`/api/v1/procurement/pr/${id}/approve`, { approve, rejection_reason });
    return res.data;
  },
  async convertPRToPO(id: string, data: object): Promise<PODetail> {
    const res = await apiClient.post<PODetail>(`/api/v1/procurement/pr/${id}/convert`, data);
    return res.data;
  },
  async addPRLine(id: string, data: object): Promise<PRDetail> {
    const res = await apiClient.post<PRDetail>(`/api/v1/procurement/pr/${id}/lines`, data);
    return res.data;
  },
  async deletePRLine(prId: string, lineId: string): Promise<void> {
    await apiClient.delete(`/api/v1/procurement/pr/${prId}/lines/${lineId}`).then((r) => r.data);
  },

  // POs
  async listPOs(params?: { status?: POStatus; supplier_id?: string }): Promise<PO[]> {
    const res = await apiClient.get<PO[]>("/api/v1/procurement/po/", { params });
    return res.data;
  },
  async getPO(id: string): Promise<PODetail> {
    const res = await apiClient.get<PODetail>(`/api/v1/procurement/po/${id}`);
    return res.data;
  },
  async createPO(data: object): Promise<PODetail> {
    const res = await apiClient.post<PODetail>("/api/v1/procurement/po/", data);
    return res.data;
  },
  async updatePO(id: string, data: object): Promise<PODetail> {
    const res = await apiClient.patch<PODetail>(`/api/v1/procurement/po/${id}`, data);
    return res.data;
  },
  async approvePO(id: string): Promise<PO> {
    const res = await apiClient.post<PO>(`/api/v1/procurement/po/${id}/approve`);
    return res.data;
  },
  async markOrdered(id: string): Promise<PO> {
    const res = await apiClient.post<PO>(`/api/v1/procurement/po/${id}/order`);
    return res.data;
  },
  async cancelPO(id: string): Promise<PO> {
    const res = await apiClient.post<PO>(`/api/v1/procurement/po/${id}/cancel`);
    return res.data;
  },

  // GRNs
  async listGRNs(params?: { po_id?: string }): Promise<GRN[]> {
    const res = await apiClient.get<GRN[]>("/api/v1/procurement/grn/", { params });
    return res.data;
  },
  async getGRN(id: string): Promise<GRNDetail> {
    const res = await apiClient.get<GRNDetail>(`/api/v1/procurement/grn/${id}`);
    return res.data;
  },
  async createGRN(data: object): Promise<GRNDetail> {
    const res = await apiClient.post<GRNDetail>("/api/v1/procurement/grn/", data);
    return res.data;
  },
  async postGRN(id: string): Promise<GRNDetail> {
    const res = await apiClient.post<GRNDetail>(`/api/v1/procurement/grn/${id}/post`);
    return res.data;
  },

  // Shipments
  async listShipments(params?: { po_id?: string }): Promise<ImportShipment[]> {
    const res = await apiClient.get<ImportShipment[]>("/api/v1/procurement/shipments/", { params });
    return res.data;
  },
  async getShipment(id: string): Promise<ImportShipment> {
    const res = await apiClient.get<ImportShipment>(`/api/v1/procurement/shipments/${id}`);
    return res.data;
  },
  async createShipment(data: object): Promise<ImportShipment> {
    const res = await apiClient.post<ImportShipment>("/api/v1/procurement/shipments/", data);
    return res.data;
  },
  async updateShipment(id: string, data: object): Promise<ImportShipment> {
    const res = await apiClient.patch<ImportShipment>(`/api/v1/procurement/shipments/${id}`, data);
    return res.data;
  },

  // Supplier Payments
  async recordPayment(poId: string, data: { payment_date: string; amount: number; method: string; reference?: string; notes?: string }): Promise<SupplierPayment> {
    const res = await apiClient.post<SupplierPayment>(`/api/v1/procurement/po/${poId}/payments`, data);
    return res.data;
  },
  async listPayments(poId: string): Promise<SupplierPayment[]> {
    const res = await apiClient.get<SupplierPayment[]>(`/api/v1/procurement/po/${poId}/payments`);
    return res.data;
  },

  // Evaluations
  async listEvaluations(params?: { supplier_id?: string }): Promise<SupplierEvaluation[]> {
    const res = await apiClient.get<SupplierEvaluation[]>("/api/v1/procurement/evaluations/", { params });
    return res.data;
  },
  async createEvaluation(data: object): Promise<SupplierEvaluation> {
    const res = await apiClient.post<SupplierEvaluation>("/api/v1/procurement/evaluations/", data);
    return res.data;
  },
  async supplierDashboard(): Promise<SupplierDashboardRow[]> {
    const res = await apiClient.get<SupplierDashboardRow[]>("/api/v1/procurement/suppliers/dashboard");
    return res.data;
  },

  // Delivery planning
  async inboundSchedule(daysAhead = 30): Promise<InboundScheduleRow[]> {
    const res = await apiClient.get<InboundScheduleRow[]>("/api/v1/procurement/delivery/schedule", {
      params: { days_ahead: daysAhead },
    });
    return res.data;
  },
  async deliveryAlerts(): Promise<DeliveryAlertRow[]> {
    const res = await apiClient.get<DeliveryAlertRow[]>("/api/v1/procurement/delivery/alerts");
    return res.data;
  },

  async listApprovalRules(params?: { active_only?: boolean }): Promise<ProcurementApprovalRule[]> {
    const res = await apiClient.get<ProcurementApprovalRule[]>("/api/v1/procurement/approval-rules", { params });
    return res.data;
  },
  async createApprovalRule(data: object): Promise<ProcurementApprovalRule> {
    const res = await apiClient.post<ProcurementApprovalRule>("/api/v1/procurement/approval-rules", data);
    return res.data;
  },
  async updateApprovalRule(id: string, data: object): Promise<ProcurementApprovalRule> {
    const res = await apiClient.patch<ProcurementApprovalRule>(`/api/v1/procurement/approval-rules/${id}`, data);
    return res.data;
  },

  // RFQ
  async listRFQs(params?: { status?: RFQStatus }): Promise<RFQRead[]> {
    const res = await apiClient.get<RFQRead[]>("/api/v1/procurement/rfq/", { params });
    return res.data;
  },
  async createRFQ(data: object): Promise<RFQDetail> {
    const res = await apiClient.post<RFQDetail>("/api/v1/procurement/rfq/", data);
    return res.data;
  },
  async getRFQ(id: string): Promise<RFQDetail> {
    const res = await apiClient.get<RFQDetail>(`/api/v1/procurement/rfq/${id}`);
    return res.data;
  },
  async updateRFQ(id: string, data: object): Promise<RFQDetail> {
    const res = await apiClient.patch<RFQDetail>(`/api/v1/procurement/rfq/${id}`, data);
    return res.data;
  },
  async addRFQResponse(rfqId: string, data: object): Promise<RFQResponseRead> {
    const res = await apiClient.post<RFQResponseRead>(`/api/v1/procurement/rfq/${rfqId}/responses`, data);
    return res.data;
  },

  // Blanket Purchase Agreements
  async listBPAs(params?: { supplier_id?: string; status?: BPAStatus }): Promise<BlanketAgreement[]> {
    const res = await apiClient.get<BlanketAgreement[]>("/api/v1/procurement/bpa/", { params });
    return res.data;
  },
  async createBPA(data: object): Promise<BlanketAgreement> {
    const res = await apiClient.post<BlanketAgreement>("/api/v1/procurement/bpa/", data);
    return res.data;
  },
  async updateBPA(id: string, data: object): Promise<BlanketAgreement> {
    const res = await apiClient.patch<BlanketAgreement>(`/api/v1/procurement/bpa/${id}`, data);
    return res.data;
  },

  // Auto Reorder Policies
  async listReorderPolicies(params?: { active_only?: boolean }): Promise<AutoReorderPolicy[]> {
    const res = await apiClient.get<AutoReorderPolicy[]>("/api/v1/procurement/reorder-policies/", { params });
    return res.data;
  },
  async createReorderPolicy(data: object): Promise<AutoReorderPolicy> {
    const res = await apiClient.post<AutoReorderPolicy>("/api/v1/procurement/reorder-policies/", data);
    return res.data;
  },
  async updateReorderPolicy(id: string, data: object): Promise<AutoReorderPolicy> {
    const res = await apiClient.patch<AutoReorderPolicy>(`/api/v1/procurement/reorder-policies/${id}`, data);
    return res.data;
  },
  async deleteReorderPolicy(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/procurement/reorder-policies/${id}`);
  },
};
