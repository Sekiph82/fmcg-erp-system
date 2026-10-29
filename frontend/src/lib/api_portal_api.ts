import axios, { AxiosResponse } from "axios";
import { apiClient } from "@/lib/api";

const BASE = "/api/v1/developer";

/** A user-safe error for Developer Portal requests. Response bodies are never
 * copied verbatim into the UI because proxies may return HTML or diagnostics. */
export class DevPortalRequestError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "DevPortalRequestError";
  }
}

function safeErrorMessage(status?: number): string {
  if (status === 401) return "Your session has expired. Sign in again to use Developer Portal.";
  if (status === 403) return "Your account does not have permission to view this Developer Portal resource.";
  if (status === 404) return "This Developer Portal resource is unavailable. Check the API service and try again.";
  if (status && status >= 500) return "The API service could not complete this request. Try again shortly.";
  if (status) return "The Developer Portal request was rejected. Check the request and try again.";
  return "The API service could not be reached. Check your connection and try again.";
}

export interface ApiKeyOut {
  key_id: string;
  key_name: string;
  key_prefix: string;
  scopes: string | null;
  rate_limit_per_min: number;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  description: string | null;
}

export interface ApiKeyCreated extends ApiKeyOut {
  raw_key: string;
  warning: string;
}

export type ApiClientEnvironment = "development" | "sandbox" | "production";

export interface ApiClientApplication {
  client_id: string;
  name: string;
  description: string | null;
  environment: ApiClientEnvironment;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DevPortalDashboard {
  total_keys: number;
  active_keys: number;
  total_api_calls: number;
  success_calls: number;
  error_calls: number;
  available_scopes: string[];
  default_rate_limit: number;
}

export interface UsageLog {
  log_id: string;
  endpoint: string | null;
  method: string | null;
  status_code: number | null;
  response_ms: number | null;
  created_at: string;
}

export interface DevResources {
  openapi_json: string;
  openapi_ui: string;
  redoc_ui: string;
  postman_collection_note: string;
  authentication: Record<string, string>;
  rate_limits: Record<string, string>;
  sdk_note: string;
  webhooks: Record<string, string>;
}

export interface GraphQLSchemaInfo {
  status: string;
  note: string;
  planned_types: string[];
  planned_queries: string[];
  planned_mutations: string[];
  rest_api_base: string;
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  let response: AxiosResponse<string>;
  try {
    response = await apiClient.request<string>({
      url: BASE + path,
      method: opts?.method ?? "GET",
      data: typeof opts?.body === "string" ? opts.body : undefined,
      headers: {
        Accept: "application/json",
        ...(typeof opts?.body === "string" ? { "Content-Type": "application/json" } : {}),
      },
      timeout: 15000,
      signal: opts?.signal ?? undefined,
      responseType: "text",
    });
  } catch (error) {
    const status = axios.isAxiosError(error) ? error.response?.status : undefined;
    throw new DevPortalRequestError(safeErrorMessage(status), status);
  }
  if (response.status === 204) return undefined as T;
  const contentType = response.headers["content-type"];
  if (typeof contentType !== "string" || !contentType.toLowerCase().includes("application/json")) {
    throw new DevPortalRequestError("The API returned an unexpected response. Check the API service and try again.", response.status);
  }
  try {
    const data: unknown = JSON.parse(response.data);
    if (typeof data !== "object" || data === null) {
      throw new DevPortalRequestError("The API response could not be read. Try again shortly.", response.status);
    }
    return data as T;
  } catch (error) {
    if (error instanceof DevPortalRequestError) throw error;
    throw new DevPortalRequestError("The API response could not be read. Try again shortly.", response.status);
  }
}

export const devPortalApi = {
  createApplication: (body: {
    name: string;
    description?: string;
    environment: ApiClientEnvironment;
  }) => req<ApiClientApplication>("/applications", { method: "POST", body: JSON.stringify(body) }),

  listApplications: (includeInactive = false) =>
    req<ApiClientApplication[]>(`/applications?include_inactive=${includeInactive}`),

  updateApplication: (clientId: string, body: Partial<Pick<ApiClientApplication, "name" | "description" | "environment" | "is_active">>) =>
    req<ApiClientApplication>(`/applications/${encodeURIComponent(clientId)}`, { method: "PATCH", body: JSON.stringify(body) }),

  createKey: (body: {
    key_name: string;
    scopes?: string;
    rate_limit_per_min?: number;
    description?: string;
    expires_at?: string;
  }) => req<ApiKeyCreated>("/keys", { method: "POST", body: JSON.stringify(body) }),

  listKeys: (includeInactive = false) =>
    req<ApiKeyOut[]>(`/keys?include_inactive=${includeInactive}`),

  revokeKey: (keyId: string) => req<void>(`/keys/${keyId}`, { method: "DELETE" }),

  keyUsage: (keyId: string) => req<UsageLog[]>(`/keys/${keyId}/usage`),

  getDashboard: () => req<DevPortalDashboard>("/dashboard"),

  getGraphQLInfo: () => req<GraphQLSchemaInfo>("/graphql/schema"),

  getResources: () => req<DevResources>("/resources"),
};
