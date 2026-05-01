import { apiClient } from "./api";

export type HttpMethod = "POST" | "PUT";
export type AuthType = "none" | "basic" | "bearer" | "hmac";
export type DeliveryStatus = "pending" | "sent" | "failed" | "retrying" | "dead_letter";

export interface EventDefinition {
  id: string;
  event_code: string;
  event_name: string;
  module: string;
  description?: string;
  active_flag: boolean;
  created_at: string;
}

export interface EventLog {
  id: string;
  event_code: string;
  module: string;
  reference_type?: string;
  reference_id?: string;
  payload: Record<string, unknown>;
  actor_id?: string;
  partition_key?: string;
  created_at: string;
}

export interface Subscription {
  id: string;
  name: string;
  endpoint_url: string;
  http_method: HttpMethod;
  auth_type: AuthType;
  event_codes?: string[];
  filter_expression?: Array<{ field: string; op: string; value: unknown }>;
  max_retries: number;
  timeout_seconds: number;
  active_flag: boolean;
  created_at: string;
}

export interface SubscriptionCreate {
  name: string;
  endpoint_url: string;
  http_method?: HttpMethod;
  headers?: Record<string, string>;
  auth_type?: AuthType;
  secret_key?: string;
  auth_user?: string;
  filter_expression?: Array<{ field: string; op: string; value: unknown }>;
  event_codes?: string[];
  transform_template?: Record<string, string>;
  max_retries?: number;
  timeout_seconds?: number;
}

export interface DeliveryAttempt {
  id: string;
  event_log_id: string;
  subscription_id: string;
  attempt_no: number;
  response_status?: number;
  response_body?: string;
  error_message?: string;
  attempted_at?: string;
  next_retry_at?: string;
  status: DeliveryStatus;
  duration_ms?: number;
  created_at: string;
}

export interface InboundEndpoint {
  id: string;
  name: string;
  endpoint_path: string;
  method: HttpMethod;
  auth_type: AuthType;
  handler_module?: string;
  description?: string;
  active_flag: boolean;
  last_received_at?: string;
  receive_count: number;
  created_at: string;
}

export interface WebhookDashboard {
  total_events_24h: number;
  total_events_7d: number;
  total_deliveries_24h: number;
  delivery_success_rate_24h: number;
  pending_deliveries: number;
  dead_letter_count: number;
  active_subscriptions: number;
  top_events: Array<{ event_code: string; count: number }>;
  recent_failures: Array<Record<string, unknown>>;
}

export interface WebhookReport {
  delivery_success_rate: number;
  total_delivered: number;
  total_failed: number;
  total_dead_letter: number;
  avg_retry_count: number;
  top_event_producers: Array<{ module: string; count: number }>;
  failure_reasons: Array<{ http_status: number; count: number }>;
  subscription_latency: Array<{ subscription_id: string; avg_latency_ms: number }>;
}

const BASE = "/api/v1/webhooks";

export async function getDashboard(): Promise<WebhookDashboard> {
  const res = await apiClient.get<WebhookDashboard>(`${BASE}/dashboard`);
  return res.data;
}

export async function listEventDefinitions(module?: string): Promise<EventDefinition[]> {
  const res = await apiClient.get<EventDefinition[]>(`${BASE}/event-definitions`, { params: { module } });
  return res.data;
}

export async function seedEventDefinitions(): Promise<void> {
  await apiClient.post(`${BASE}/event-definitions/seed`);
}

export async function listEvents(params?: {
  event_code?: string; module?: string; reference_id?: string; limit?: number;
}): Promise<EventLog[]> {
  const res = await apiClient.get<EventLog[]>(`${BASE}/events`, { params });
  return res.data;
}

export async function publishEvent(data: {
  event_code: string; payload: Record<string, unknown>;
  reference_type?: string; reference_id?: string;
}): Promise<EventLog> {
  const res = await apiClient.post<EventLog>(`${BASE}/events/publish`, data);
  return res.data;
}

export async function replayEvents(data: {
  event_ids?: string[]; event_code?: string;
  from_dt?: string; to_dt?: string; subscription_ids?: string[];
}): Promise<{ detail: string }> {
  const res = await apiClient.post<{ detail: string }>(`${BASE}/events/replay`, data);
  return res.data;
}

export async function listSubscriptions(activeOnly = false): Promise<Subscription[]> {
  const res = await apiClient.get<Subscription[]>(`${BASE}/subscriptions`, { params: { active_only: activeOnly } });
  return res.data;
}

export async function createSubscription(data: SubscriptionCreate): Promise<Subscription> {
  const res = await apiClient.post<Subscription>(`${BASE}/subscriptions`, data);
  return res.data;
}

export async function updateSubscription(id: string, data: Partial<SubscriptionCreate & { active_flag: boolean }>): Promise<Subscription> {
  const res = await apiClient.patch<Subscription>(`${BASE}/subscriptions/${id}`, data);
  return res.data;
}

export async function deleteSubscription(id: string): Promise<void> {
  await apiClient.delete(`${BASE}/subscriptions/${id}`);
}

export async function testSubscription(id: string): Promise<{ success: boolean; status_code?: number; response?: string; error?: string }> {
  const res = await apiClient.post(`${BASE}/subscriptions/${id}/test`);
  return res.data;
}

export async function listDeliveries(params?: {
  subscription_id?: string; delivery_status?: DeliveryStatus; limit?: number;
}): Promise<DeliveryAttempt[]> {
  const res = await apiClient.get<DeliveryAttempt[]>(`${BASE}/deliveries`, { params });
  return res.data;
}

export async function listDeadLetter(limit = 100): Promise<DeliveryAttempt[]> {
  const res = await apiClient.get<DeliveryAttempt[]>(`${BASE}/deliveries/dead-letter`, { params: { limit } });
  return res.data;
}

export async function retryDelivery(id: string): Promise<DeliveryAttempt> {
  const res = await apiClient.post<DeliveryAttempt>(`${BASE}/deliveries/${id}/retry`);
  return res.data;
}

export async function processPending(): Promise<{ processed: number; retried: number }> {
  const res = await apiClient.post<{ processed: number; retried: number }>(`${BASE}/deliveries/process-pending`);
  return res.data;
}

export async function listInboundEndpoints(): Promise<InboundEndpoint[]> {
  const res = await apiClient.get<InboundEndpoint[]>(`${BASE}/inbound-endpoints`);
  return res.data;
}

export async function createInboundEndpoint(data: Partial<InboundEndpoint>): Promise<InboundEndpoint> {
  const res = await apiClient.post<InboundEndpoint>(`${BASE}/inbound-endpoints`, data);
  return res.data;
}

export async function getReport(days = 7): Promise<WebhookReport> {
  const res = await apiClient.get<WebhookReport>(`${BASE}/reports`, { params: { days } });
  return res.data;
}

export async function getHealthMonitor() {
  const res = await apiClient.get(`${BASE}/ai/health-monitor`);
  return res.data;
}

export async function getPayloadAdvisor() {
  const res = await apiClient.get(`${BASE}/ai/payload-advisor`);
  return res.data;
}

export async function getAnomalyDetector() {
  const res = await apiClient.get(`${BASE}/ai/anomaly-detector`);
  return res.data;
}

export const STATUS_BADGE: Record<DeliveryStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  sent: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  retrying: "bg-blue-100 text-blue-800",
  dead_letter: "bg-gray-900 text-white",
};
