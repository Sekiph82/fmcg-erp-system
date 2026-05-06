import { apiClient } from "./api";

export type EmailProvider = "GMAIL" | "OUTLOOK" | "SMTP";

export interface EmailAccount {
  id: string;
  provider: EmailProvider;
  email_address: string;
  display_name?: string | null;
  is_active: boolean;
  sync_enabled: boolean;
  last_sync_at?: string | null;
  sync_error?: string | null;
  created_at: string;
}

export interface EmailMessage {
  id: string;
  thread_id: string;
  from_email: string;
  from_name?: string | null;
  to_emails: string[];
  cc_emails?: string[] | null;
  subject: string;
  body_text?: string | null;
  received_at: string;
  is_inbound: boolean;
  is_read: boolean;
  has_attachments: boolean;
  sent_by_id?: string | null;
}

export interface EmailThread {
  id: string;
  account_id: string;
  subject: string;
  snippet?: string | null;
  participants?: string[] | null;
  is_read: boolean;
  message_count: number;
  last_message_at?: string | null;
  linked_module?: string | null;
  linked_object_id?: string | null;
  linked_object_ref?: string | null;
  created_at: string;
  messages: EmailMessage[];
}

export interface EmailTemplate {
  id: string;
  name: string;
  module?: string | null;
  subject_template: string;
  body_template: string;
  is_active: boolean;
  created_at: string;
}

const BASE = "/api/v1/email";

export const emailApi = {
  async listAccounts(): Promise<EmailAccount[]> {
    const r = await apiClient.get<EmailAccount[]>(`${BASE}/accounts`);
    return r.data;
  },
  async addAccount(data: { provider: EmailProvider; email_address: string; display_name?: string; sync_enabled?: boolean }): Promise<EmailAccount> {
    const r = await apiClient.post<EmailAccount>(`${BASE}/accounts`, data);
    return r.data;
  },
  async removeAccount(id: string): Promise<void> {
    await apiClient.delete(`${BASE}/accounts/${id}`);
  },
  async listThreads(params?: {
    linked_object_id?: string; linked_module?: string; account_id?: string; unread_only?: boolean;
  }): Promise<EmailThread[]> {
    const r = await apiClient.get<EmailThread[]>(`${BASE}/threads`, { params });
    return r.data;
  },
  async getThread(id: string): Promise<EmailThread> {
    const r = await apiClient.get<EmailThread>(`${BASE}/threads/${id}`);
    return r.data;
  },
  async linkThread(id: string, data: { linked_module: string; linked_object_id: string; linked_object_ref?: string }): Promise<EmailThread> {
    const r = await apiClient.patch<EmailThread>(`${BASE}/threads/${id}/link`, null, { params: data });
    return r.data;
  },
  async sendEmail(data: {
    account_id: string; to_emails: string[]; cc_emails?: string[]; subject: string; body_text: string;
    linked_module?: string; linked_object_id?: string; linked_object_ref?: string; thread_id?: string;
  }): Promise<EmailThread> {
    const r = await apiClient.post<EmailThread>(`${BASE}/send`, data);
    return r.data;
  },
  async syncAccount(accountId: string): Promise<{ synced: number; account: string }> {
    const r = await apiClient.post<{ synced: number; account: string }>(`${BASE}/sync/${accountId}`);
    return r.data;
  },
  async listTemplates(module?: string): Promise<EmailTemplate[]> {
    const r = await apiClient.get<EmailTemplate[]>(`${BASE}/templates`, { params: module ? { module } : undefined });
    return r.data;
  },
  async createTemplate(data: { name: string; module?: string; subject_template: string; body_template: string }): Promise<EmailTemplate> {
    const r = await apiClient.post<EmailTemplate>(`${BASE}/templates`, data);
    return r.data;
  },
};

export const PROVIDER_COLOR: Record<EmailProvider, string> = {
  GMAIL:   "bg-red-100 text-red-700",
  OUTLOOK: "bg-blue-100 text-blue-700",
  SMTP:    "bg-gray-100 text-gray-700",
};

export function fmtEmailDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const diffH = (now.getTime() - d.getTime()) / 3600000;
  if (diffH < 24) return d.toLocaleTimeString("en-KE", { hour: "2-digit", minute: "2-digit" });
  if (diffH < 168) return d.toLocaleDateString("en-KE", { weekday: "short" });
  return d.toLocaleDateString("en-KE", { day: "2-digit", month: "short" });
}
