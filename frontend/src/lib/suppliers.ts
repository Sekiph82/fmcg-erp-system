import { apiClient } from "./api";

export type SupplierPaymentMethod = "bank" | "cash" | "mpesa";

export interface Supplier {
  id: string;
  code: string;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  country?: string;
  tax_id?: string;
  payment_terms_days: number;
  is_active: boolean;
  preferred_payment_method?: SupplierPaymentMethod;
  mpesa_phone_number?: string;
}

export interface SupplierCreate {
  code: string;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  city?: string;
  country?: string;
  payment_terms_days?: number;
  is_active?: boolean;
  preferred_payment_method?: SupplierPaymentMethod;
  mpesa_phone_number?: string;
}

export const suppliersApi = {
  async list(skip = 0, limit = 50): Promise<Supplier[]> {
    const res = await apiClient.get<Supplier[]>("/api/v1/suppliers/", {
      params: { skip, limit },
    });
    return res.data;
  },

  async get(id: string): Promise<Supplier> {
    const res = await apiClient.get<Supplier>(`/api/v1/suppliers/${id}`).then((r) => r.data);
    return res.data;
  },

  async create(data: SupplierCreate): Promise<Supplier> {
    const res = await apiClient.post<Supplier>("/api/v1/suppliers/", data).then((r) => r.data);
    return res.data;
  },

  async update(id: string, data: Partial<SupplierCreate>): Promise<Supplier> {
    const res = await apiClient.patch<Supplier>(`/api/v1/suppliers/${id}`, data).then((r) => r.data);
    return res.data;
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/suppliers/${id}`).then((r) => r.data);
  },
};