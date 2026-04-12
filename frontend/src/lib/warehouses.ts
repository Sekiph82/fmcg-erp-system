import { apiClient } from "./api";

export type WarehouseType =
  | "FINISHED_GOODS"
  | "RAW_MATERIAL"
  | "TRANSIT"
  | "RETURNS";

export interface Warehouse {
  id: string;
  code: string;
  name: string;
  warehouse_type: WarehouseType;
  address?: string;
  city?: string;
  country?: string;
  capacity_sqm?: number;
  is_active: boolean;
}

export interface WarehouseCreate {
  code: string;
  name: string;
  warehouse_type: WarehouseType;
  address?: string;
  city?: string;
  country?: string;
  capacity_sqm?: number;
  is_active?: boolean;
}

export const warehousesApi = {
  async list(skip = 0, limit = 50): Promise<Warehouse[]> {
    const res = await apiClient.get<Warehouse[]>("/api/v1/warehouses/", {
      params: { skip, limit },
    });
    return res.data;
  },

  async get(id: string): Promise<Warehouse> {
    const res = await apiClient.get<Warehouse>(`/api/v1/warehouses/${id}`);
    return res.data;
  },

  async create(data: WarehouseCreate): Promise<Warehouse> {
    const res = await apiClient.post<Warehouse>("/api/v1/warehouses/", data);
    return res.data;
  },

  async update(id: string, data: Partial<WarehouseCreate>): Promise<Warehouse> {
    const res = await apiClient.patch<Warehouse>(`/api/v1/warehouses/${id}`, data);
    return res.data;
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/warehouses/${id}`);
  },
};