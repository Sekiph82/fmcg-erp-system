import { apiClient } from "./api";

export type SupplierPaymentMethod = "bank" | "cash" | "mpesa";
export type SupplierQualificationStatus = "PENDING" | "APPROVED" | "CONDITIONAL" | "SUSPENDED" | "REJECTED";

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
  is_preferred: boolean;
  supplier_category?: string | null;
  qualification_status?: SupplierQualificationStatus | null;
  risk_level?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | null;
  approved_from?: string | null;
  approved_until?: string | null;
  approved_by_id?: string | null;
  approved_at?: string | null;
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
    const res = await apiClient.get<Supplier>(`/api/v1/suppliers/${id}`);
    return res.data;
  },

  async create(data: SupplierCreate): Promise<Supplier> {
    const res = await apiClient.post<Supplier>("/api/v1/suppliers/", data);
    return res.data;
  },

  async update(id: string, data: Partial<SupplierCreate>): Promise<Supplier> {
    const res = await apiClient.patch<Supplier>(`/api/v1/suppliers/${id}`, data);
    return res.data;
  },

  async decideQualification(
    id: string,
    data: { qualification_status: SupplierQualificationStatus; approved_from?: string | null; approved_until?: string | null; reason: string },
  ): Promise<Supplier> {
    const res = await apiClient.post<Supplier>(`/api/v1/suppliers/${id}/qualification`, data);
    return res.data;
  },

  async decidePreference(id: string, data: { is_preferred: boolean; reason: string }): Promise<Supplier> {
    const res = await apiClient.post<Supplier>(`/api/v1/suppliers/${id}/preference`, data);
    return res.data;
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/suppliers/${id}`).then((r) => r.data);
  },
};
