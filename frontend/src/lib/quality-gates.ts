import { apiClient } from "@/lib/api";

export type QualityGateSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type GateTrigger =
  | "ON_RECEIPT"
  | "ON_PRODUCTION_RELEASE"
  | "ON_IN_PROCESS"
  | "ON_FINISHED_GOODS_RELEASE"
  | "ON_DISPATCH";
export type GateQCType = "INCOMING" | "IN_PROCESS" | "FINISHED_GOODS";
export type GateAuditResult = "PASS" | "BLOCKED" | "WAIVED" | "NO_GATE";

export interface GateTemplateParameter {
  id: string;
  parameter_name: string;
  parameter_type: "NUMERIC" | "TEXT" | "BOOLEAN" | "PASS_FAIL";
  target_value?: string | null;
  min_value?: number | null;
  max_value?: number | null;
}

export interface GateTemplate {
  id: string;
  name: string;
  qc_type: GateQCType;
  is_active: boolean;
  is_mandatory: boolean;
  blocks_progression: boolean;
  release_required: boolean;
  parameters: GateTemplateParameter[];
}

export interface QualityGateDefinition {
  id: string;
  code: string;
  name: string;
  gate_type: string;
  trigger_event: GateTrigger;
  target_module: string;
  description?: string | null;
  is_active: boolean;
  version: number;
  effective_from: string;
  effective_to?: string | null;
  severity: QualityGateSeverity;
  is_mandatory: boolean;
  waiver_allowed: boolean;
  waiver_reason_required: boolean;
  waiver_approval_required: boolean;
  required_template_ids: string[];
  required_templates: GateTemplate[];
  created_at: string;
  updated_at: string;
}

export interface QualityGateDefinitionCreate {
  code: string;
  name: string;
  gate_type: string;
  trigger_event: GateTrigger;
  target_module: string;
  description?: string;
  is_active: boolean;
  version: number;
  effective_from: string;
  severity: QualityGateSeverity;
  is_mandatory: boolean;
  waiver_allowed: boolean;
  waiver_reason_required: boolean;
  waiver_approval_required: boolean;
  required_template_ids: string[];
}

export interface QualityGateDefinitionUpdate {
  effective_to?: string;
}

export interface QualityGateAuditEvent {
  id: string;
  evaluation_id: string;
  target_module: string;
  trigger_event: GateTrigger;
  gate_definition_id?: string | null;
  gate_code: string;
  gate_version: number;
  scope_type: string;
  scope_id: string;
  business_type: string;
  business_id: string;
  required_template_name?: string | null;
  result: GateAuditResult;
  evaluated_by_id?: string | null;
  reason?: string | null;
  evaluated_at: string;
}

export const qualityGatesApi = {
  async listDefinitions(): Promise<QualityGateDefinition[]> {
    const response = await apiClient.get<QualityGateDefinition[]>("/api/v1/qms/gate-definitions", {
      params: { active_only: false },
    });
    return response.data;
  },

  async listTemplates(qcType: GateQCType): Promise<GateTemplate[]> {
    const response = await apiClient.get<GateTemplate[]>("/api/v1/qms/templates", {
      params: { qc_type: qcType, active_only: true },
    });
    return response.data;
  },

  async listAuditHistory(result?: GateAuditResult): Promise<QualityGateAuditEvent[]> {
    const response = await apiClient.get<QualityGateAuditEvent[]>("/api/v1/qms/gate-audit-history", {
      params: { limit: 100, ...(result ? { result } : {}) },
    });
    return response.data;
  },

  async createDefinition(data: QualityGateDefinitionCreate): Promise<QualityGateDefinition> {
    const response = await apiClient.post<QualityGateDefinition>("/api/v1/qms/gate-definitions", data);
    return response.data;
  },

  async updateDefinition(id: string, data: QualityGateDefinitionUpdate): Promise<QualityGateDefinition> {
    const response = await apiClient.patch<QualityGateDefinition>(`/api/v1/qms/gate-definitions/${id}`, data);
    return response.data;
  },
};
