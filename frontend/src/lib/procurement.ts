import { apiClient } from "@/lib/api";

export type PRStatus = "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "CONVERTED" | "REJECTED" | "CANCELLED";
export type POStatus = "DRAFT" | "APPROVED" | "ORDERED" | "PARTIALLY_RECEIVED" | "RECEIVED" | "CANCELLED";
export type GRNStatus = "DRAFT" | "POSTED";
export type ImportShipmentStatus = "PENDING" | "IN_TRANSIT" | "ARRIVED" | "CUSTOMS_CLEARED" | "DELIVERED";
export type SupplierPaymentMethod = "bank" | "cash" | "mpesa";
export type POPaymentStatus = "pending" | "partially_paid" | "paid";

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

export interface PR {
  id: string;
  pr_no: string;
  requester_id: string;
  requester_name?: string;
  department?: string;
  required_date: string;
  notes?: string;
  status: PRStatus;
  approved_by_id?: string;
  approved_at?: string;
  rejection_reason?: string;
  created_at: string;
  line_count: number;
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

export interface SupplierPayment {
  id: string;
  po_id: string;
  supplier_id: string;
  payment_date: string;
  amount: number;
  method: SupplierPaymentMethod;
  reference?: string;
  notes?: string;
  created_at: string;
}

export interface PO {
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

export interface GRN {
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
}

export interface GRNDetail extends GRN {
  lines: GRNLine[];
}

export interface ImportShipment {
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
}

export interface SupplierEvaluation {
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
}

export interface SupplierDashboardRow {
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

export const procurementApi = {
  // PRs
  async listPRs(params?: { status?: PRStatus }): Promise<PR[]> {
    const res = await apiClient.get<PR[]>("/api/v1/procurement/pr/", { params }).then((r) => r.data);
    return res.data;
  },
  async getPR(id: string): Promise<PRDetail> {
    const res = await apiClient.get<PRDetail>(`/api/v1/procurement/pr/${id}`).then((r) => r.data);
    return res.data;
  },
  async createPR(data: object): Promise<PRDetail> {
    const res = await apiClient.post<PRDetail>("/api/v1/procurement/pr/", data).then((r) => r.data);
    return res.data;
  },
  async updatePR(id: string, data: object): Promise<PRDetail> {
    const res = await apiClient.patch<PRDetail>(`/api/v1/procurement/pr/${id}`, data).then((r) => r.data);
    return res.data;
  },
  async submitPR(id: string): Promise<PR> {
    const res = await apiClient.post<PR>(`/api/v1/procurement/pr/${id}/submit`).then((r) => r.data);
    return res.data;
  },
  async approvePR(id: string, approve: boolean, rejection_reason?: string): Promise<PR> {
    const res = await apiClient.post<PR>(`/api/v1/procurement/pr/${id}/approve`, { approve, rejection_reason }).then((r) => r.data);
    return res.data;
  },
  async convertPRToPO(id: string, data: object): Promise<PODetail> {
    const res = await apiClient.post<PODetail>(`/api/v1/procurement/pr/${id}/convert`, data).then((r) => r.data);
    return res.data;
  },
  async addPRLine(id: string, data: object): Promise<PRDetail> {
    const res = await apiClient.post<PRDetail>(`/api/v1/procurement/pr/${id}/lines`, data).then((r) => r.data);
    return res.data;
  },
  async deletePRLine(prId: string, lineId: string): Promise<void> {
    await apiClient.delete(`/api/v1/procurement/pr/${prId}/lines/${lineId}`).then((r) => r.data);
  },

  // POs
  async listPOs(params?: { status?: POStatus; supplier_id?: string }): Promise<PO[]> {
    const res = await apiClient.get<PO[]>("/api/v1/procurement/po/", { params }).then((r) => r.data);
    return res.data;
  },
  async getPO(id: string): Promise<PODetail> {
    const res = await apiClient.get<PODetail>(`/api/v1/procurement/po/${id}`).then((r) => r.data);
    return res.data;
  },
  async createPO(data: object): Promise<PODetail> {
    const res = await apiClient.post<PODetail>("/api/v1/procurement/po/", data).then((r) => r.data);
    return res.data;
  },
  async updatePO(id: string, data: object): Promise<PODetail> {
    const res = await apiClient.patch<PODetail>(`/api/v1/procurement/po/${id}`, data).then((r) => r.data);
    return res.data;
  },
  async approvePO(id: string): Promise<PO> {
    const res = await apiClient.post<PO>(`/api/v1/procurement/po/${id}/approve`).then((r) => r.data);
    return res.data;
  },
  async markOrdered(id: string): Promise<PO> {
    const res = await apiClient.post<PO>(`/api/v1/procurement/po/${id}/order`).then((r) => r.data);
    return res.data;
  },
  async cancelPO(id: string): Promise<PO> {
    const res = await apiClient.post<PO>(`/api/v1/procurement/po/${id}/cancel`).then((r) => r.data);
    return res.data;
  },

  // GRNs
  async listGRNs(params?: { po_id?: string }): Promise<GRN[]> {
    const res = await apiClient.get<GRN[]>("/api/v1/procurement/grn/", { params }).then((r) => r.data);
    return res.data;
  },
  async getGRN(id: string): Promise<GRNDetail> {
    const res = await apiClient.get<GRNDetail>(`/api/v1/procurement/grn/${id}`).then((r) => r.data);
    return res.data;
  },
  async createGRN(data: object): Promise<GRNDetail> {
    const res = await apiClient.post<GRNDetail>("/api/v1/procurement/grn/", data).then((r) => r.data);
    return res.data;
  },
  async postGRN(id: string): Promise<GRNDetail> {
    const res = await apiClient.post<GRNDetail>(`/api/v1/procurement/grn/${id}/post`).then((r) => r.data);
    return res.data;
  },

  // Shipments
  async listShipments(params?: { po_id?: string }): Promise<ImportShipment[]> {
    const res = await apiClient.get<ImportShipment[]>("/api/v1/procurement/shipments/", { params }).then((r) => r.data);
    return res.data;
  },
  async getShipment(id: string): Promise<ImportShipment> {
    const res = await apiClient.get<ImportShipment>(`/api/v1/procurement/shipments/${id}`).then((r) => r.data);
    return res.data;
  },
  async createShipment(data: object): Promise<ImportShipment> {
    const res = await apiClient.post<ImportShipment>("/api/v1/procurement/shipments/", data).then((r) => r.data);
    return res.data;
  },
  async updateShipment(id: string, data: object): Promise<ImportShipment> {
    const res = await apiClient.patch<ImportShipment>(`/api/v1/procurement/shipments/${id}`, data).then((r) => r.data);
    return res.data;
  },

  // Supplier Payments
  async recordPayment(poId: string, data: { payment_date: string; amount: number; method: string; reference?: string; notes?: string }): Promise<SupplierPayment> {
    const res = await apiClient.post<SupplierPayment>(`/api/v1/procurement/po/${poId}/payments`, data).then((r) => r.data);
    return res.data;
  },
  async listPayments(poId: string): Promise<SupplierPayment[]> {
    const res = await apiClient.get<SupplierPayment[]>(`/api/v1/procurement/po/${poId}/payments`).then((r) => r.data);
    return res.data;
  },

  // Evaluations
  async listEvaluations(params?: { supplier_id?: string }): Promise<SupplierEvaluation[]> {
    const res = await apiClient.get<SupplierEvaluation[]>("/api/v1/procurement/evaluations/", { params }).then((r) => r.data);
    return res.data;
  },
  async createEvaluation(data: object): Promise<SupplierEvaluation> {
    const res = await apiClient.post<SupplierEvaluation>("/api/v1/procurement/evaluations/", data).then((r) => r.data);
    return res.data;
  },
  async supplierDashboard(): Promise<SupplierDashboardRow[]> {
    const res = await apiClient.get<SupplierDashboardRow[]>("/api/v1/procurement/suppliers/dashboard").then((r) => r.data);
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
    const res = await apiClient.get<DeliveryAlertRow[]>("/api/v1/procurement/delivery/alerts").then((r) => r.data);
    return res.data;
  },
};
