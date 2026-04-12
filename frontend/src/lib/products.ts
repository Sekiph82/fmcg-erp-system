import { apiClient } from "./api";

export type ProductCategory = "FOOD" | "BEVERAGE" | "PERSONAL_CARE" | "HOUSEHOLD" | "OTHER";
export type UnitOfMeasure = "PCS" | "KG" | "G" | "L" | "ML" | "BOX" | "CARTON" | "PALLET";

export interface Product {
  id: string;
  sku: string;
  barcode?: string;
  name: string;
  description?: string;
  category: ProductCategory;
  uom: UnitOfMeasure;
  units_per_carton: number;
  weight_kg?: number;
  shelf_life_days?: number;
  reorder_point: number;
  standard_cost?: number;
  selling_price?: number;
  is_active: boolean;
}

export interface ProductCreate {
  sku: string;
  name: string;
  category: ProductCategory;
  uom: UnitOfMeasure;
  units_per_carton?: number;
  reorder_point?: number;
  selling_price?: number;
  standard_cost?: number;
  shelf_life_days?: number;
  is_active?: boolean;
}

export const productsApi = {
  async list(skip = 0, limit = 50): Promise<Product[]> {
    const res = await apiClient.get<Product[]>("/api/v1/products/", {
      params: { skip, limit },
    });
    return res.data;
  },

  async get(id: string): Promise<Product> {
    const res = await apiClient.get<Product>(`/api/v1/products/${id}`);
    return res.data;
  },

  async create(data: ProductCreate): Promise<Product> {
    const res = await apiClient.post<Product>("/api/v1/products/", data);
    return res.data;
  },

  async update(id: string, data: Partial<ProductCreate>): Promise<Product> {
    const res = await apiClient.patch<Product>(`/api/v1/products/${id}`, data);
    return res.data;
  },
};