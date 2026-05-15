import { apiClient } from "./api";

export interface ModuleManifestEntry {
  key: string;
  label: string;
  route_prefix: string;
  import_path: string;
  permission_actions: string[];
  permission_codes: string[];
  sidebar_group: string;
  icon_key: string;
  ai_mode: string;
  enabled: boolean;
  critical: boolean;
}

export interface ModuleManifest {
  modules: ModuleManifestEntry[];
  permission_codes: string[];
  visible_permission_codes: string[];
}

export interface PermissionCoverage {
  registry_permission_count: number;
  database_permission_count: number;
  covered_registry_permissions: string[];
  missing_registry_permissions: string[];
  database_only_permissions: string[];
}

export async function getModuleManifest(): Promise<ModuleManifest> {
  const res = await apiClient.get<ModuleManifest>("/api/v1/modules/manifest");
  return res.data;
}

export async function getPermissionCoverage(): Promise<PermissionCoverage> {
  const res = await apiClient.get<PermissionCoverage>("/api/v1/modules/permissions/coverage");
  return res.data;
}
