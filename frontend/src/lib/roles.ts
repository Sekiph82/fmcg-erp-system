import { apiClient } from "./api";
import type { AccessScope, AccessScopeAssign, Permission, Role } from "./users";

export type { AccessScope, AccessScopeAssign, Permission, Role };

export interface RoleCreate {
  name: string;
  description?: string;
  permission_ids?: string[];
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  permission_ids?: string[];
}

export const rolesApi = {
  list: (params?: { skip?: number; limit?: number; is_active?: boolean }) =>
    apiClient.get<Role[]>("/api/v1/roles/", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Role>(`/api/v1/roles/${id}`).then((r) => r.data),

  create: (data: RoleCreate) =>
    apiClient.post<Role>("/api/v1/roles/", data).then((r) => r.data),

  update: (id: string, data: RoleUpdate) =>
    apiClient.patch<Role>(`/api/v1/roles/${id}`, data).then((r) => r.data),

  activate: (id: string) =>
    apiClient.post<Role>(`/api/v1/roles/${id}/activate`).then((r) => r.data),

  deactivate: (id: string) =>
    apiClient.post<Role>(`/api/v1/roles/${id}/deactivate`).then((r) => r.data),

  assignPermissions: (id: string, permission_ids: string[]) =>
    apiClient
      .put<Role>(`/api/v1/roles/${id}/permissions`, { permission_ids })
      .then((r) => r.data),

  listScopes: (id: string) =>
    apiClient.get<AccessScope[]>(`/api/v1/roles/${id}/scopes`).then((r) => r.data),

  assignScopes: (id: string, scopes: AccessScopeAssign[]) =>
    apiClient
      .put<AccessScope[]>(`/api/v1/roles/${id}/scopes`, { scopes })
      .then((r) => r.data),

  listPermissions: (module?: string) =>
    apiClient
      .get<Permission[]>("/api/v1/roles/permissions", { params: module ? { module } : undefined })
      .then((r) => r.data),
};

// Group permissions by module for matrix view
export function groupByModule(permissions: Permission[]): Record<string, Permission[]> {
  return permissions.reduce(
    (acc, p) => {
      if (!acc[p.module]) acc[p.module] = [];
      acc[p.module].push(p);
      return acc;
    },
    {} as Record<string, Permission[]>,
  );
}

export const STANDARD_ACTIONS = ["view", "create", "edit", "delete", "approve", "export", "import", "import_template"];

// Modules that participate in bulk import
export const IMPORT_MODULES = [
  "inventory", "products", "materials", "production", "procurement",
  "sales", "finance", "logistics", "quality", "maintenance",
  "warehouses", "wms", "hr", "tax", "users",
] as const;

export type ImportModule = (typeof IMPORT_MODULES)[number];

// Roles that carry full cross-module import authority
export const FULL_IMPORT_ROLES = ["owner", "ceo", "coo", "cfo", "cto", "data_manager"] as const;
