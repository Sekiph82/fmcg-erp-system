import { apiClient } from "./api";

export type DistributorStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED";

export interface Distributor {
  id: string;
  code: string;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  city?: string;
  region?: string;
  territory?: string;
  credit_limit?: number;
  payment_terms_days: number;
  currency: string;
  status: DistributorStatus;
  warehouse_id?: string;
  notes?: string;
  created_at: string;
}

export interface DistributorCreate {
  code: string;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  city?: string;
  region?: string;
  territory?: string;
  credit_limit?: number;
  payment_terms_days?: number;
  currency?: string;
}

export const distributorsApi = {
  list: (params?: { region?: string; active_only?: boolean }) =>
    apiClient.get<Distributor[]>("/api/v1/distributors/", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Distributor>(`/api/v1/distributors/${id}`).then((r) => r.data),

  create: (data: DistributorCreate) =>
    apiClient.post<Distributor>("/api/v1/distributors/", data).then((r) => r.data),

  update: (id: string, data: Partial<DistributorCreate> & { status?: DistributorStatus }) =>
    apiClient.patch<Distributor>(`/api/v1/distributors/${id}`, data).then((r) => r.data),
};
