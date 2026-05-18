import { apiClient } from "./api";

export type TwoFAMethod = "totp" | "sms" | "email";

export interface TwoFASetupResponse {
  method: TwoFAMethod;
  secret_key?: string;
  qr_code_uri?: string;
  qr_code_image?: string;
  session_token?: string;  // SMS/email only — pass to verify2FA
}

export interface TwoFAEnableResponse {
  is_enabled: boolean;
  recovery_codes: string[];
}

export interface TwoFASettingsRead {
  is_enabled: boolean;
  method?: TwoFAMethod;
  has_recovery_codes: boolean;
}

export interface LoginVerifyResponse {
  access_token?: string;
  token_type: string;
}

export interface StepUpResponse {
  authorized: boolean;
  stepup_token?: string;
}

export interface TwoFAStatusReport {
  total_users: number;
  users_with_2fa_enabled: number;
  users_without_2fa: number;
  method_breakdown: Record<string, number>;
  failed_attempts_last_24h: number;
}

export async function getSettings(): Promise<TwoFASettingsRead> {
  const res = await apiClient.get<TwoFASettingsRead>("/api/v1/auth/2fa/settings");
  return res.data;
}

export async function setup2FA(method: TwoFAMethod, phone_number?: string, email?: string): Promise<TwoFASetupResponse> {
  const res = await apiClient.post<TwoFASetupResponse>("/api/v1/auth/2fa/setup", { method, phone_number, email });
  return res.data;
}

export async function verify2FA(code: string, session_token?: string): Promise<TwoFAEnableResponse> {
  const res = await apiClient.post<TwoFAEnableResponse>("/api/v1/auth/2fa/verify", { code, session_token });
  return res.data;
}

export async function resendOTP(session_token: string): Promise<{ session_token: string; cooldown_seconds: number }> {
  const res = await apiClient.post<{ session_token: string; cooldown_seconds: number }>(
    "/api/v1/auth/2fa/resend-otp",
    { session_token },
  );
  return res.data;
}

export async function disable2FA(password: string): Promise<void> {
  await apiClient.post("/api/v1/auth/2fa/disable", { password });
}

export async function loginVerify(session_token: string, code: string): Promise<LoginVerifyResponse> {
  const res = await apiClient.post<LoginVerifyResponse>("/api/v1/auth/2fa/login-verify", { session_token, code });
  return res.data;
}

export async function useRecoveryCode(session_token: string, code: string): Promise<LoginVerifyResponse> {
  const res = await apiClient.post<LoginVerifyResponse>("/api/v1/auth/2fa/use-recovery-code", { session_token, code });
  return res.data;
}

export async function regenerateRecoveryCodes(): Promise<{ codes: string[] }> {
  const res = await apiClient.post<{ codes: string[] }>("/api/v1/auth/2fa/recovery-codes/regenerate");
  return res.data;
}

export async function stepUp(code: string, action: string): Promise<StepUpResponse> {
  const res = await apiClient.post<StepUpResponse>("/api/v1/auth/2fa/step-up", { code, action });
  return res.data;
}

export async function get2FAReport(): Promise<TwoFAStatusReport> {
  const res = await apiClient.get<TwoFAStatusReport>("/api/v1/auth/2fa/report");
  return res.data;
}

export async function getSecurityRiskReport() {
  const res = await apiClient.get("/api/v1/auth/2fa/ai/security-risk");
  return res.data;
}

export async function getAccessAnomalyReport() {
  const res = await apiClient.get("/api/v1/auth/2fa/ai/access-anomaly");
  return res.data;
}
