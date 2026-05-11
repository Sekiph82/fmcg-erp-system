import { apiClient } from "./api";

export interface RoleShort {
  id: string;
  name: string;
  is_active: boolean;
}

export interface UserShort {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: RoleShort[];
}

export interface Permission {
  id: string;
  code: string;
  name: string;
  description?: string;
  module: string;
  action: string;
  is_active: boolean;
  is_mobile_visible: boolean;
}

export interface Role {
  id: string;
  name: string;
  description?: string;
  is_system_role: boolean;
  is_active: boolean;
  permissions: Permission[];
}

export interface UserDetail extends UserShort {
  roles: Role[];
}

export interface PaginatedUsers {
  total: number;
  page: number;
  page_size: number;
  items: UserShort[];
}

export interface UserCreate {
  email: string;
  username: string;
  full_name: string;
  password: string;
  is_active?: boolean;
  is_superuser?: boolean;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  is_active?: boolean;
}

export interface PasswordReset {
  new_password: string;
}

export interface AccessScope {
  id: string;
  user_id?: string | null;
  role_id?: string | null;
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
}

export type AccessScopeAssign = Omit<AccessScope, "id" | "user_id" | "role_id">;

export const usersApi = {
  list: (params?: {
    skip?: number;
    limit?: number;
    search?: string;
    is_active?: boolean;
    role_id?: string;
  }) =>
    apiClient
      .get<PaginatedUsers>("/api/v1/users/", { params })
      .then((r) => r.data),

  get: (id: string) =>
    apiClient.get<UserDetail>(`/api/v1/users/${id}`).then((r) => r.data),

  create: (data: UserCreate) =>
    apiClient.post<UserDetail>("/api/v1/users/", data).then((r) => r.data),

  update: (id: string, data: UserUpdate) =>
    apiClient.patch<UserDetail>(`/api/v1/users/${id}`, data).then((r) => r.data),

  activate: (id: string) =>
    apiClient.post<UserDetail>(`/api/v1/users/${id}/activate`).then((r) => r.data),

  deactivate: (id: string) =>
    apiClient.post<UserDetail>(`/api/v1/users/${id}/deactivate`).then((r) => r.data),

  resetPassword: (id: string, data: PasswordReset) =>
    apiClient.post(`/api/v1/users/${id}/reset-password`, data),

  assignRoles: (id: string, role_ids: string[]) =>
    apiClient
      .put<UserDetail>(`/api/v1/users/${id}/roles`, { role_ids })
      .then((r) => r.data),

  listScopes: (id: string) =>
    apiClient.get<AccessScope[]>(`/api/v1/users/${id}/scopes`).then((r) => r.data),

  assignScopes: (id: string, scopes: AccessScopeAssign[]) =>
    apiClient
      .put<AccessScope[]>(`/api/v1/users/${id}/scopes`, { scopes })
      .then((r) => r.data),
};
