import { apiClient } from "./api";

export type WADirection = "INBOUND" | "OUTBOUND";
export type WAMsgType   = "TEXT" | "TEMPLATE" | "IMAGE" | "DOCUMENT" | "AUDIO";
export type WAStatus    = "QUEUED" | "SENT" | "DELIVERED" | "READ" | "FAILED";

export interface WAConfig {
  id: string;
  display_name: string;
  business_phone_no?: string | null;
  provider: string;
  is_active: boolean;
  is_demo_mode: boolean;
  created_at: string;
}

export interface WAConfigUpdate {
  display_name?: string;
  business_phone_id?: string;
  business_phone_no?: string;
  api_token?: string;
  webhook_verify_token?: string;
  provider?: string;
  is_demo_mode?: boolean;
  is_active?: boolean;
}

export interface WAMessage {
  id: string;
  config_id: string;
  direction: WADirection;
  message_type: WAMsgType;
  status: WAStatus;
  phone: string;
  contact_name?: string | null;
  body?: string | null;
  template_name?: string | null;
  template_vars?: string[] | null;
  external_msg_id?: string | null;
  error_message?: string | null;
  delivered_at?: string | null;
  read_at?: string | null;
  linked_module?: string | null;
  linked_object_id?: string | null;
  linked_object_ref?: string | null;
  sent_by_id?: string | null;
  created_at: string;
}

export interface WATemplate {
  id: string;
  template_name: string;
  display_name: string;
  category: string;
  language: string;
  header_text?: string | null;
  body_template: string;
  footer_text?: string | null;
  buttons?: Record<string, unknown>[] | null;
  variable_count: number;
  module_context?: string | null;
  is_active: boolean;
  created_at: string;
}

const BASE = "/api/v1/whatsapp";

export const waApi = {
  async listConfigs(): Promise<WAConfig[]> {
    const r = await apiClient.get<WAConfig[]>(`${BASE}/configs`);
    return r.data;
  },
  async addConfig(data: {
    display_name: string; business_phone_no?: string; provider?: string; is_demo_mode?: boolean;
  }): Promise<WAConfig> {
    const r = await apiClient.post<WAConfig>(`${BASE}/configs`, data);
    return r.data;
  },
  async updateConfig(id: string, data: WAConfigUpdate): Promise<WAConfig> {
    const r = await apiClient.patch<WAConfig>(`${BASE}/configs/${id}`, data);
    return r.data;
  },
  async sendText(data: {
    config_id: string; phone: string; body: string; contact_name?: string;
    linked_module?: string; linked_object_id?: string; linked_object_ref?: string;
  }): Promise<WAMessage> {
    const r = await apiClient.post<WAMessage>(`${BASE}/send/text`, data);
    return r.data;
  },
  async sendTemplate(data: {
    config_id: string; phone: string; template_name: string; variables?: string[];
    contact_name?: string; linked_module?: string; linked_object_id?: string; linked_object_ref?: string;
  }): Promise<WAMessage> {
    const r = await apiClient.post<WAMessage>(`${BASE}/send/template`, data);
    return r.data;
  },
  async listMessages(params?: {
    phone?: string; direction?: WADirection; linked_object_id?: string; config_id?: string; limit?: number;
  }): Promise<WAMessage[]> {
    const r = await apiClient.get<WAMessage[]>(`${BASE}/messages`, { params });
    return r.data;
  },
  async simulateInbound(data: {
    config_id: string; phone: string; body: string; contact_name?: string;
    linked_module?: string; linked_object_id?: string; linked_object_ref?: string;
  }): Promise<WAMessage> {
    const r = await apiClient.post<WAMessage>(`${BASE}/simulate-inbound`, data);
    return r.data;
  },
  async listTemplates(module_context?: string): Promise<WATemplate[]> {
    const r = await apiClient.get<WATemplate[]>(`${BASE}/templates`, {
      params: module_context ? { module_context } : undefined,
    });
    return r.data;
  },
  async createTemplate(data: {
    template_name: string; display_name: string; category?: string;
    body_template: string; header_text?: string; footer_text?: string;
    variable_count?: number; module_context?: string;
  }): Promise<WATemplate> {
    const r = await apiClient.post<WATemplate>(`${BASE}/templates`, data);
    return r.data;
  },
  async seedDemoTemplates(): Promise<WATemplate[]> {
    const r = await apiClient.post<WATemplate[]>(`${BASE}/seed-demo-templates`);
    return r.data;
  },
};

export const STATUS_COLOR: Record<WAStatus, string> = {
  QUEUED:    "bg-gray-100 text-gray-500",
  SENT:      "bg-blue-100 text-blue-600",
  DELIVERED: "bg-green-100 text-green-600",
  READ:      "bg-indigo-100 text-indigo-700",
  FAILED:    "bg-red-100 text-red-600",
};

export const STATUS_ICON: Record<WAStatus, string> = {
  QUEUED:    "○",
  SENT:      "✓",
  DELIVERED: "✓✓",
  READ:      "✓✓",
  FAILED:    "✗",
};
