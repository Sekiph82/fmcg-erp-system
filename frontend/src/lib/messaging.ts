import { apiClient } from "./api";

export type ChannelType = "TEAM" | "DIRECT";

export interface Channel {
  id: string;
  name: string;
  slug: string;
  channel_type: ChannelType;
  description?: string | null;
  module_context?: string | null;
  is_archived: boolean;
  created_at: string;
  member_count: number;
  unread_count: number;
}

export interface Message {
  id: string;
  channel_id: string;
  sender_id?: string | null;
  sender_name?: string | null;
  sender_initials?: string | null;
  body: string;
  parent_id?: string | null;
  is_edited: boolean;
  is_deleted: boolean;
  created_at: string;
  link_module?: string | null;
  link_type?: string | null;
  link_id?: string | null;
  link_ref?: string | null;
  mentions?: string[] | null;
  reply_count: number;
}

export interface MessagePage {
  messages: Message[];
  has_more: boolean;
  oldest_at?: string | null;
}

const BASE = "/api/v1/messaging";

export const messagingApi = {
  async listChannels(): Promise<Channel[]> {
    const r = await apiClient.get<Channel[]>(`${BASE}/channels/`);
    return r.data;
  },
  async createChannel(data: {
    name: string; description?: string; module_context?: string; member_ids?: string[];
  }): Promise<Channel> {
    const r = await apiClient.post<Channel>(`${BASE}/channels/`, data);
    return r.data;
  },
  async getOrCreateDM(target_user_id: string): Promise<Channel> {
    const r = await apiClient.post<Channel>(`${BASE}/channels/dm`, { target_user_id });
    return r.data;
  },
  async joinChannel(id: string): Promise<Channel> {
    const r = await apiClient.post<Channel>(`${BASE}/channels/${id}/join`);
    return r.data;
  },
  async getMessages(channelId: string, params?: { before?: string; since?: string; limit?: number }): Promise<MessagePage> {
    const r = await apiClient.get<MessagePage>(`${BASE}/channels/${channelId}/messages`, { params });
    return r.data;
  },
  async postMessage(channelId: string, data: {
    body: string; parent_id?: string; link_module?: string;
    link_type?: string; link_id?: string; link_ref?: string; mentions?: string[];
  }): Promise<Message> {
    const r = await apiClient.post<Message>(`${BASE}/channels/${channelId}/messages`, data);
    return r.data;
  },
  async getThread(channelId: string, msgId: string): Promise<Message[]> {
    const r = await apiClient.get<Message[]>(`${BASE}/channels/${channelId}/messages/${msgId}/thread`);
    return r.data;
  },
  async editMessage(msgId: string, body: string): Promise<Message> {
    const r = await apiClient.patch<Message>(`${BASE}/messages/${msgId}`, { body });
    return r.data;
  },
  async deleteMessage(msgId: string): Promise<void> {
    await apiClient.delete(`${BASE}/messages/${msgId}`);
  },
  async search(q: string, channel_id?: string): Promise<Message[]> {
    const r = await apiClient.get<Message[]>(`${BASE}/search`, { params: { q, channel_id } });
    return r.data;
  },
};

export function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString("en-KE", { day: "2-digit", month: "short" });
}
