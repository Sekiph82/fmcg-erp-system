import { apiClient } from "./api";

export type CompanyUserRole = "ADMIN" | "USER" | "VIEWER";

export interface Company {
  id: string;
  name: string;
  short_code: string;
  registration_no?: string | null;
  tax_pin?: string | null;
  country: string;
  base_currency: string;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  logo_url?: string | null;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  branch_count: number;
  user_count: number;
}

export interface Branch {
  id: string;
  company_id: string;
  name: string;
  branch_code: string;
  branch_type?: string | null;
  address?: string | null;
  city?: string | null;
  phone?: string | null;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
}

export interface UserAccess {
  id: string;
  user_id: string;
  company_id: string;
  role: CompanyUserRole;
  is_default: boolean;
  username?: string | null;
  full_name?: string | null;
  created_at: string;
}

export interface CompanySummary {
  company_id: string;
  company_name: string;
  short_code: string;
  base_currency: string;
  branch_count: number;
  user_count: number;
  total_budgeted: number;
  open_po_count: number;
  open_so_count: number;
  product_count: number;
  warehouse_count: number;
}

const BASE = "/api/v1/companies";

export const companyApi = {
  async list(): Promise<Company[]> {
    const r = await apiClient.get<Company[]>(`${BASE}/`);
    return r.data;
  },
  async create(data: {
    name: string; short_code: string; registration_no?: string; tax_pin?: string;
    country?: string; base_currency?: string; address?: string; phone?: string; email?: string;
  }): Promise<Company> {
    const r = await apiClient.post<Company>(`${BASE}/`, data);
    return r.data;
  },
  async get(id: string): Promise<Company> {
    const r = await apiClient.get<Company>(`${BASE}/${id}`);
    return r.data;
  },
  async update(id: string, data: Partial<Company>): Promise<Company> {
    const r = await apiClient.patch<Company>(`${BASE}/${id}`, data);
    return r.data;
  },
  async setDefault(id: string): Promise<Company> {
    const r = await apiClient.post<Company>(`${BASE}/${id}/set-default`);
    return r.data;
  },
  async listBranches(companyId: string): Promise<Branch[]> {
    const r = await apiClient.get<Branch[]>(`${BASE}/${companyId}/branches`);
    return r.data;
  },
  async addBranch(companyId: string, data: {
    name: string; branch_code: string; branch_type?: string; address?: string; city?: string; phone?: string;
  }): Promise<Branch> {
    const r = await apiClient.post<Branch>(`${BASE}/${companyId}/branches`, data);
    return r.data;
  },
  async listUsers(companyId: string): Promise<UserAccess[]> {
    const r = await apiClient.get<UserAccess[]>(`${BASE}/${companyId}/users`);
    return r.data;
  },
  async grantAccess(companyId: string, data: { user_id: string; role: CompanyUserRole; is_default?: boolean }): Promise<UserAccess> {
    const r = await apiClient.post<UserAccess>(`${BASE}/${companyId}/users`, data);
    return r.data;
  },
  async revokeAccess(companyId: string, userId: string): Promise<void> {
    await apiClient.delete(`${BASE}/${companyId}/users/${userId}`);
  },
  async getSummary(companyId: string): Promise<CompanySummary> {
    const r = await apiClient.get<CompanySummary>(`${BASE}/${companyId}/summary`);
    return r.data;
  },
};

// ── Local company context ─────────────────────────────────────────────────────

const STORAGE_KEY = "active_company_id";

export function getActiveCompanyId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(STORAGE_KEY);
}

export function setActiveCompanyId(id: string): void {
  localStorage.setItem(STORAGE_KEY, id);
}

export function clearActiveCompanyId(): void {
  localStorage.removeItem(STORAGE_KEY);
}
