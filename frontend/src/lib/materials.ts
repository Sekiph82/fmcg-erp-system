import { apiClient } from "./api";

export type MaterialType = "RAW" | "PACKAGING" | "SEMI_FINISHED" | "CONSUMABLE";
export type UnitOfMeasure = "PCS" | "KG" | "G" | "L" | "ML" | "BOX" | "CARTON" | "PALLET";

export interface Material {
  id: string;
  code: string;
  name: string;
  description?: string;
  material_type: MaterialType;
  uom: UnitOfMeasure;
  weight_kg?: number;
  reorder_point: number;
  standard_cost?: number;
  lead_time_days: number;
  is_active: boolean;
  supplier_id?: string;
}

export interface MaterialCreate {
  code: string;
  name: string;
  material_type: MaterialType;
  uom: UnitOfMeasure;
  description?: string;
  reorder_point?: number;
  standard_cost?: number;
  lead_time_days?: number;
  is_active?: boolean;
  supplier_id?: string;
}

export const materialsApi = {
  async list(skip = 0, limit = 50): Promise<Material[]> {
    const res = await apiClient.get<Material[]>("/api/v1/materials/", {
      params: { skip, limit },
    });
    return res.data;
  },

  async get(id: string): Promise<Material> {
    const res = await apiClient.get<Material>(`/api/v1/materials/${id}`);
    return res.data;
  },

  async create(data: MaterialCreate): Promise<Material> {
    const res = await apiClient.post<Material>("/api/v1/materials/", data);
    return res.data;
  },

  async update(id: string, data: Partial<MaterialCreate>): Promise<Material> {
    const res = await apiClient.patch<Material>(`/api/v1/materials/${id}`, data);
    return res.data;
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/materials/${id}`);
  },
};
