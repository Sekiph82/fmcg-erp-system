const BASE = "/api/v1/mobile";

export type MobilePlatform = "ios" | "android" | "web";

export interface DeviceOut {
  push_token_id: string;
  device_id: string;
  device_name: string | null;
  platform: MobilePlatform;
  token: string;
  active_flag: boolean;
  app_version: string | null;
  created_at: string;
  last_seen_at: string;
}

export interface MobileApprovalItem {
  request_id: string;
  reference_type: string;
  reference_id: string | null;
  title: string;
  amount: number | null;
  currency: string;
  requested_by: string;
  created_at: string;
}

export interface MobileKpis {
  pending_approvals: number;
  active_devices: number;
  active_sessions_7d: number;
}

export interface DeviceStats {
  total_active_devices: number;
  total_registered_ever: number;
  by_platform: Record<string, number>;
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

export const mobileApi = {
  registerDevice: (body: {
    device_id: string;
    platform: MobilePlatform;
    token: string;
    device_name?: string;
    app_version?: string;
    os_version?: string;
  }) => req<{ push_token_id: string; status: string }>("/devices", { method: "POST", body: JSON.stringify(body) }),

  listDevices: () => req<DeviceOut[]>("/devices"),

  deactivateDevice: (tokenId: string) =>
    req<void>(`/devices/${tokenId}`, { method: "DELETE" }),

  sendPush: (body: { user_ids: string[]; title: string; body: string; data?: Record<string, unknown> }) =>
    req<{ queued: number; title: string; body: string; note: string }>("/push/send", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getApprovals: () => req<MobileApprovalItem[]>("/approvals"),

  getKpis: () => req<MobileKpis>("/kpis"),

  getDeviceStats: () => req<DeviceStats>("/devices/stats"),
};
