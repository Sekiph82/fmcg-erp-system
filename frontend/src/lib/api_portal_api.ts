const BASE = "/api/v1/developer";

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
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(await res.text());
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

export const devPortalApi = {
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
