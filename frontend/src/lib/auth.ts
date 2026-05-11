import { apiClient } from "./api";

export interface LoginResponse {
  access_token?: string;
  token_type: string;
  two_fa_required?: boolean;
  session_token?: string;
  method?: string;
  must_change_password?: boolean;
}

export interface Permission {
  id: string;
  code: string;
  name: string;
  module: string;
  action: string;
  is_active: boolean;
  is_mobile_visible: boolean;
}

export interface Role {
  id: string;
  name: string;
  is_system_role: boolean;
  is_active: boolean;
  permissions: Permission[];
}

export interface AccessScope {
  scope_type: string;
  scope_id: string;
  scope_name?: string | null;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
  can_approve: boolean;
  can_post: boolean;
  can_release: boolean;
  can_cancel: boolean;
  can_export: boolean;
  can_import: boolean;
  can_transfer: boolean;
  can_adjust: boolean;
  can_receive: boolean;
  can_dispatch: boolean;
  is_active: boolean;
  source: "user" | "role";
}

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
  roles: Role[];
  permission_codes: string[];
  modules: string[];
  scopes: AccessScope[];
  feature_flags: Record<string, boolean>;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const params = new URLSearchParams();
  params.append("username", username);
  params.append("password", password);

  const res = await apiClient.post<LoginResponse>(
    "/api/v1/auth/login",
    params,
    {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    }
  );

  return res.data;
}

export async function getMe(): Promise<User> {
  const res = await apiClient.get<User>("/api/v1/auth/me");
  return res.data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/api/v1/auth/logout");
}

export async function changeOwnPassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiClient.post("/api/v1/users/me/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}
