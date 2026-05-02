import { apiClient } from "@/lib/api";

export type QCType = "INCOMING" | "IN_PROCESS" | "FINISHED_GOODS";
export type QCStatus = "PENDING" | "IN_PROGRESS" | "PASSED" | "FAILED" | "CONDITIONAL_RELEASE" | "CANCELLED";
export type QCDecision = "ACCEPT" | "REJECT" | "CONDITIONAL_RELEASE" | "REWORK";
export type ParameterType = "NUMERIC" | "TEXT" | "BOOLEAN" | "PASS_FAIL";

export interface QCParameter {
  id: string;
  name: string;
  description?: string;
  parameter_type: ParameterType;
  unit?: string;
  min_value?: number;
  max_value?: number;
  expected_value?: string;
  is_critical: boolean;
  applicable_types: string;
  is_active: boolean;
}

export interface QCTestResult {
  id: string;
  inspection_id: string;
  parameter_id?: string;
  parameter_name: string;
  parameter_type: ParameterType;
  unit?: string;
  numeric_value?: number;
  text_value?: string;
  boolean_value?: boolean;
  min_spec?: number;
  max_spec?: number;
  expected_text?: string;
  is_passed?: boolean;
  is_critical: boolean;
  tested_by_id?: string;
  tested_by_name?: string;
  notes?: string;
  created_at: string;
  display_value: string;
  spec_range?: string;
}

export interface QCInspection {
  id: string;
  inspection_no: string;
  qc_type: QCType;
  status: QCStatus;
  grn_id?: string;
  production_order_id?: string;
  lot_id?: string;
  supplier_id?: string;
  supplier_name?: string;
  material_id?: string;
  material_name?: string;
  material_code?: string;
  product_id?: string;
  product_name?: string;
  product_sku?: string;
  warehouse_id?: string;
  lot_number?: string;
  batch_no?: string;
  sample_size?: number;
  sample_unit?: string;
  inspection_date: string;
  inspector_id?: string;
  inspector_name?: string;
  notes?: string;
  decision?: QCDecision;
  decided_by_id?: string;
  decided_at?: string;
  decision_notes?: string;
  rework_candidate: boolean;
  quarantine_applied: boolean;
  created_at: string;
  test_count: number;
  pass_count: number;
  fail_count: number;
  critical_fail: boolean;
}

export interface QCInspectionDetail extends QCInspection {
  test_results: QCTestResult[];
}

export interface COATestLine {
  parameter_name: string;
  unit?: string;
  spec_range?: string;
  result_value: string;
  is_passed?: boolean;
  is_critical: boolean;
}

export interface COAReport {
  inspection_no: string;
  qc_type: string;
  inspection_date: string;
  lot_number?: string;
  batch_no?: string;
  product_name?: string;
  product_sku?: string;
  material_name?: string;
  supplier_name?: string;
  inspector_name?: string;
  decision?: string;
  decision_notes?: string;
  decided_at?: string;
  overall_result: string;
  test_lines: COATestLine[];
}

export interface RejectionSummaryRow {
  material_name?: string;
  product_name?: string;
  supplier_name?: string;
  total_inspections: number;
  total_rejected: number;
  rejection_rate: number;
  last_rejection_date?: string;
}

export const qualityApi = {
  // Parameters
  async listParameters(params?: { qc_type?: QCType; active_only?: boolean }): Promise<QCParameter[]> {
    const res = await apiClient.get<QCParameter[]>("/api/v1/quality/parameters/", { params });
    return res.data;
  },
  async createParameter(data: object): Promise<QCParameter> {
    const res = await apiClient.post<QCParameter>("/api/v1/quality/parameters/", data);
    return res.data;
  },
  async updateParameter(id: string, data: object): Promise<QCParameter> {
    const res = await apiClient.patch<QCParameter>(`/api/v1/quality/parameters/${id}`, data);
    return res.data;
  },
  async deleteParameter(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/quality/parameters/${id}`).then((r) => r.data);
  },

  // Inspections
  async listInspections(params?: {
    qc_type?: QCType;
    status?: QCStatus;
    supplier_id?: string;
    material_id?: string;
    product_id?: string;
  }): Promise<QCInspection[]> {
    const res = await apiClient.get<QCInspection[]>("/api/v1/quality/inspections/", { params });
    return res.data;
  },
  async getInspection(id: string): Promise<QCInspectionDetail> {
    const res = await apiClient.get<QCInspectionDetail>(`/api/v1/quality/inspections/${id}`);
    return res.data;
  },
  async createInspection(data: object): Promise<QCInspectionDetail> {
    const res = await apiClient.post<QCInspectionDetail>("/api/v1/quality/inspections/", data);
    return res.data;
  },
  async updateInspection(id: string, data: object): Promise<QCInspectionDetail> {
    const res = await apiClient.patch<QCInspectionDetail>(`/api/v1/quality/inspections/${id}`, data);
    return res.data;
  },
  async addTestResult(inspectionId: string, data: object): Promise<QCInspectionDetail> {
    const res = await apiClient.post<QCInspectionDetail>(`/api/v1/quality/inspections/${inspectionId}/results`, data);
    return res.data;
  },
  async deleteTestResult(inspectionId: string, resultId: string): Promise<void> {
    await apiClient.delete(`/api/v1/quality/inspections/${inspectionId}/results/${resultId}`).then((r) => r.data);
  },
  async decide(inspectionId: string, data: object): Promise<QCInspectionDetail> {
    const res = await apiClient.post<QCInspectionDetail>(`/api/v1/quality/inspections/${inspectionId}/decide`, data);
    return res.data;
  },
  async releaseQuarantine(inspectionId: string, notes?: string): Promise<QCInspectionDetail> {
    const res = await apiClient.post<QCInspectionDetail>(
      `/api/v1/quality/inspections/${inspectionId}/release-quarantine`,
      null,
      { params: notes ? { notes } : {} }
    );
    return res.data;
  },
  async getCOA(inspectionId: string): Promise<COAReport> {
    const res = await apiClient.get<COAReport>(`/api/v1/quality/inspections/${inspectionId}/coa`);
    return res.data;
  },
  async createForGRN(params: {
    grn_id: string; grn_line_id: string; inspection_no: string;
    material_id?: string; supplier_id?: string; warehouse_id?: string; lot_number?: string;
  }): Promise<QCInspectionDetail> {
    const res = await apiClient.post<QCInspectionDetail>("/api/v1/quality/create-for-grn", null, { params });
    return res.data;
  },
  async createForOrder(params: {
    production_order_id: string; inspection_no: string;
    product_id?: string; warehouse_id?: string; lot_number?: string; batch_no?: string;
    qc_type?: QCType;
  }): Promise<QCInspectionDetail> {
    const res = await apiClient.post<QCInspectionDetail>("/api/v1/quality/create-for-order", null, { params });
    return res.data;
  },

  // Reports
  async rejectionSummary(): Promise<RejectionSummaryRow[]> {
    const res = await apiClient.get<RejectionSummaryRow[]>("/api/v1/quality/reports/rejections");
    return res.data;
  },
};
