import { apiClient } from "./api";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface Permission {
  id: string;
  code: string;
  name: string;
  module: string;
  action: string;
  is_mobile_visible: boolean;
}

export interface Role {
  id: string;
  name: string;
  is_active: boolean;
  permissions: Permission[];
}

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: Role[];
  permission_codes: string[];
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