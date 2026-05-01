import { apiClient } from "@/lib/api";

export type PayFrequency = "MONTHLY" | "WEEKLY" | "BIWEEKLY";
export type PayrollRunStatus = "DRAFT" | "CALCULATED" | "APPROVED" | "PAID" | "CANCELLED";
export type KeComponentType = "NHIF" | "NSSF" | "HOUSING_LEVY" | "PERSONAL_RELIEF";
export type EmissionScope = "SCOPE1" | "SCOPE2" | "SCOPE3";

export interface PayrollProfile {
  id: string;
  employee_id: string;
  employee_name?: string;
  employee_code?: string;
  basic_salary: number;
  pay_frequency: PayFrequency;
  housing_allowance: number;
  transport_allowance: number;
  other_allowances?: Record<string, number>;
  tax_pin?: string;
  nhif_no?: string;
  nssf_no?: string;
  bank_name?: string;
  bank_account_no?: string;
  bank_branch?: string;
  is_active: boolean;
  notes?: string;
}

export interface TaxBand {
  id: string;
  tax_year: number;
  lower_limit: number;
  upper_limit?: number;
  rate: number;
  description?: string;
  is_active: boolean;
}

export interface StatutoryRate {
  id: string;
  component: KeComponentType;
  rate_year: number;
  rate_value: number;
  is_percentage: boolean;
  max_amount?: number;
  notes?: string;
  is_active: boolean;
}

export interface PayrollRun {
  id: string;
  run_no: string;
  period_month: number;
  period_year: number;
  period_start: string;
  period_end: string;
  run_date?: string;
  status: PayrollRunStatus;
  total_gross: number;
  total_paye: number;
  total_nhif: number;
  total_nssf: number;
  total_housing_levy: number;
  total_net: number;
  employee_count: number;
  notes?: string;
}

export interface PayrollLine {
  id: string;
  run_id: string;
  employee_id: string;
  employee_name?: string;
  employee_code?: string;
  tax_pin?: string;
  nhif_no?: string;
  nssf_no?: string;
  basic_salary: number;
  housing_allowance: number;
  transport_allowance: number;
  other_allowances: number;
  overtime_pay: number;
  gross_salary: number;
  nssf_employee: number;
  taxable_income: number;
  paye_before_relief: number;
  personal_relief: number;
  paye_amount: number;
  nhif_amount: number;
  housing_levy: number;
  other_deductions: number;
  total_deductions: number;
  net_salary: number;
  components_json?: {
    earnings: Record<string, number>;
    deductions: Record<string, number>;
  };
}

export interface Payslip {
  id: string;
  payroll_line_id: string;
  employee_id: string;
  run_id: string;
  issue_date: string;
  is_sent: boolean;
  employee_name?: string;
  employee_code?: string;
  department?: string;
  period_month?: number;
  period_year?: number;
  gross_salary?: number;
  net_salary?: number;
  paye_amount?: number;
  nhif_amount?: number;
  nssf_employee?: number;
  housing_levy?: number;
  components_json?: PayrollLine["components_json"];
}

export interface PayrollInsight {
  agent: string;
  insights: string[];
  details?: any[];
  generated_at: string;
}

export interface SeedResult {
  tax_bands_seeded: number;
  nhif_tiers_seeded: number;
  statutory_rates_seeded: number;
  message: string;
}

const BASE = "/api/v1/payroll-ke";

export const payrollKeApi = {
  // Profiles
  async listProfiles(): Promise<PayrollProfile[]> {
    const res = await apiClient.get(`${BASE}/profiles`);
    return res.data?.data ?? res.data;
  },
  async getProfile(id: string): Promise<PayrollProfile> {
    const res = await apiClient.get(`${BASE}/profiles/${id}`);
    return res.data?.data ?? res.data;
  },
  async createProfile(data: Omit<PayrollProfile, "id" | "employee_name" | "employee_code">): Promise<PayrollProfile> {
    const res = await apiClient.post(`${BASE}/profiles`, data);
    return res.data?.data ?? res.data;
  },
  async updateProfile(id: string, data: Partial<PayrollProfile>): Promise<PayrollProfile> {
    const res = await apiClient.patch(`${BASE}/profiles/${id}`, data);
    return res.data?.data ?? res.data;
  },

  // Tax bands & rates
  async listTaxBands(params?: { tax_year?: number }): Promise<TaxBand[]> {
    const res = await apiClient.get(`${BASE}/tax-bands`, { params });
    return res.data?.data ?? res.data;
  },
  async listStatutoryRates(): Promise<StatutoryRate[]> {
    const res = await apiClient.get(`${BASE}/statutory-rates`);
    return res.data?.data ?? res.data;
  },
  async seedRates(tax_year = 2024): Promise<SeedResult> {
    const res = await apiClient.post(`${BASE}/seed-rates`, null, { params: { tax_year } });
    return res.data?.data ?? res.data;
  },

  // Runs
  async listRuns(): Promise<PayrollRun[]> {
    const res = await apiClient.get(`${BASE}/runs`);
    return res.data?.data ?? res.data;
  },
  async getRun(id: string): Promise<PayrollRun> {
    const res = await apiClient.get(`${BASE}/runs/${id}`);
    return res.data?.data ?? res.data;
  },
  async createRun(data: { period_month: number; period_year: number; period_start: string; period_end: string; notes?: string }): Promise<PayrollRun> {
    const res = await apiClient.post(`${BASE}/runs`, data);
    return res.data?.data ?? res.data;
  },
  async calculateRun(id: string, tax_year?: number): Promise<PayrollRun> {
    const res = await apiClient.post(`${BASE}/runs/${id}/calculate`, null, { params: tax_year ? { tax_year } : {} });
    return res.data?.data ?? res.data;
  },
  async approveRun(id: string): Promise<PayrollRun> {
    const res = await apiClient.post(`${BASE}/runs/${id}/approve`);
    return res.data?.data ?? res.data;
  },
  async getRunLines(id: string): Promise<PayrollLine[]> {
    const res = await apiClient.get(`${BASE}/runs/${id}/lines`);
    return res.data?.data ?? res.data;
  },
  async getRunPayslips(id: string): Promise<Payslip[]> {
    const res = await apiClient.get(`${BASE}/runs/${id}/payslips`);
    return res.data?.data ?? res.data;
  },
  async getPayslip(id: string): Promise<Payslip> {
    const res = await apiClient.get(`${BASE}/payslips/${id}`);
    return res.data?.data ?? res.data;
  },

  // Reports
  async payeReport(runId: string) {
    const res = await apiClient.get(`${BASE}/runs/${runId}/reports/paye`);
    return res.data?.data ?? res.data;
  },
  async nhifReport(runId: string) {
    const res = await apiClient.get(`${BASE}/runs/${runId}/reports/nhif`);
    return res.data?.data ?? res.data;
  },
  async nssfReport(runId: string) {
    const res = await apiClient.get(`${BASE}/runs/${runId}/reports/nssf`);
    return res.data?.data ?? res.data;
  },
  async payrollSummary(runId: string) {
    const res = await apiClient.get(`${BASE}/runs/${runId}/reports/summary`);
    return res.data?.data ?? res.data;
  },

  // AI
  async aiAnomaly(runId: string): Promise<PayrollInsight> {
    const res = await apiClient.get(`${BASE}/runs/${runId}/ai/anomaly`);
    return res.data?.data ?? res.data;
  },
  async aiCompliance(): Promise<PayrollInsight> {
    const res = await apiClient.get(`${BASE}/ai/compliance`);
    return res.data?.data ?? res.data;
  },
};

export const MONTH_NAMES = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export const STATUS_COLORS: Record<PayrollRunStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  CALCULATED: "bg-blue-100 text-blue-700",
  APPROVED: "bg-green-100 text-green-700",
  PAID: "bg-purple-100 text-purple-700",
  CANCELLED: "bg-red-100 text-red-600",
};
