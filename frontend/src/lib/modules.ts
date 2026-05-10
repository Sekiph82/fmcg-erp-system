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

export async function getModuleManifest(): Promise<ModuleManifest> {
  const res = await apiClient.get<ModuleManifest>("/api/v1/modules/manifest");
  return res.data;
}
