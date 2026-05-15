import { apiClient } from "./api";

export type EmployeeStatus = "ACTIVE" | "INACTIVE" | "ON_LEAVE" | "TERMINATED";
export type AttendanceStatus = "PRESENT" | "ABSENT" | "LATE" | "LEAVE" | "HALF_DAY";
export type LeaveType = "ANNUAL" | "SICK" | "MATERNITY" | "PATERNITY" | "UNPAID" | "COMPASSIONATE" | "OTHER";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";
export type PaymentMethod = "MPESA" | "BANK" | "CASH";
export type PayrollStatus = "DRAFT" | "APPROVED" | "PAID" | "CANCELLED";

export interface HRScopeFields {
  company_id?: string | null;
  branch_id?: string | null;
  department_id?: string | null;
  cost_center_id?: string | null;
}

export interface EmployeeShort {
  id: string;
  employee_code: string;
  full_name: string;
  department: string;
  role: string;
  status: EmployeeStatus;
}

export interface Employee extends EmployeeShort, HRScopeFields {
  phone: string | null;
  email: string | null;
  hire_date: string;
  user_id: string | null;
  manager_employee_id?: string | null;
  payment_method: PaymentMethod | null;
  mpesa_number: string | null;
  bank_account: string | null;
  salary_grade: string | null;
  terminated_at?: string | null;
  archived_at?: string | null;
  archived_by_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShiftTemplate extends HRScopeFields {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  department: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ShiftAssignment extends HRScopeFields {
  id: string;
  employee_id: string;
  shift_template_id: string;
  effective_from: string;
  effective_to: string | null;
  supervisor_id: string | null;
  notes: string | null;
  shift_template: ShiftTemplate | null;
  employee: EmployeeShort | null;
}

export interface AttendanceRecord extends HRScopeFields {
  id: string;
  employee_id: string;
  attendance_date: string;
  status: AttendanceStatus;
  clock_in: string | null;
  clock_out: string | null;
  notes: string | null;
  recorded_by_id: string | null;
  employee: EmployeeShort | null;
}

export interface LeaveRequest extends HRScopeFields {
  id: string;
  employee_id: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  days_requested: number;
  reason: string | null;
  approval_status: ApprovalStatus;
  reviewed_by_id: string | null;
  review_note: string | null;
  employee: EmployeeShort | null;
}

export interface LeaveBalance extends HRScopeFields {
  id: string;
  employee_id: string;
  leave_type: LeaveType;
  year: number;
  entitled_days: number;
  used_days: number;
  remaining: number;
}

export interface PayrollPeriod extends HRScopeFields {
  id: string;
  period_month: number;
  period_year: number;
  status: PayrollStatus;
  notes: string | null;
  approved_by_id: string | null;
}

export interface PayrollLine extends HRScopeFields {
  id: string;
  period_id: string;
  employee_id: string;
  salary_components: Record<string, number> | null;
  gross_pay: number;
  net_pay: number;
  payment_method: PaymentMethod | null;
  payment_reference: string | null;
  is_paid: boolean;
  paid_by_id: string | null;
  employee: EmployeeShort | null;
}

export interface PayrollPeriodDetail extends PayrollPeriod {
  lines: PayrollLine[];
}

const base = "/api/v1/hr";

export const hrApi = {
  // Employees
  listEmployees: (params?: { department?: string; status?: string; search?: string }) =>
    apiClient.get<EmployeeShort[]>(`${base}/employees/`, { params }).then((r) => r.data),
  getEmployee: (id: string) =>
    apiClient.get<Employee>(`${base}/employees/${id}`).then((r) => r.data),
  createEmployee: (data: Record<string, unknown>) =>
    apiClient.post<Employee>(`${base}/employees/`, data).then((r) => r.data),
  updateEmployee: (id: string, data: Record<string, unknown>) =>
    apiClient.patch<Employee>(`${base}/employees/${id}`, data).then((r) => r.data),

  // Shift Templates
  listShiftTemplates: (activeOnly = true) =>
    apiClient.get<ShiftTemplate[]>(`${base}/shifts/templates/`, { params: { active_only: activeOnly } }).then((r) => r.data),
  createShiftTemplate: (data: Record<string, unknown>) =>
    apiClient.post<ShiftTemplate>(`${base}/shifts/templates/`, data).then((r) => r.data),
  updateShiftTemplate: (id: string, data: Record<string, unknown>) =>
    apiClient.patch<ShiftTemplate>(`${base}/shifts/templates/${id}`, data).then((r) => r.data),

  // Shift Assignments
  listShiftAssignments: (params?: { employee_id?: string; department?: string; as_of?: string }) =>
    apiClient.get<ShiftAssignment[]>(`${base}/shifts/assignments/`, { params }).then((r) => r.data),
  createShiftAssignment: (data: Record<string, unknown>) =>
    apiClient.post<ShiftAssignment>(`${base}/shifts/assignments/`, data).then((r) => r.data),
  updateShiftAssignment: (id: string, data: Record<string, unknown>) =>
    apiClient.patch<ShiftAssignment>(`${base}/shifts/assignments/${id}`, data).then((r) => r.data),

  // Attendance
  listAttendance: (params?: { employee_id?: string; department?: string; date_from?: string; date_to?: string; status?: string }) =>
    apiClient.get<AttendanceRecord[]>(`${base}/attendance/`, { params }).then((r) => r.data),
  recordAttendance: (data: Record<string, unknown>) =>
    apiClient.post<AttendanceRecord>(`${base}/attendance/`, data).then((r) => r.data),
  bulkRecordAttendance: (records: Record<string, unknown>[]) =>
    apiClient.post<AttendanceRecord[]>(`${base}/attendance/bulk/`, { records }).then((r) => r.data),
  updateAttendance: (id: string, data: Record<string, unknown>) =>
    apiClient.patch<AttendanceRecord>(`${base}/attendance/${id}`, data).then((r) => r.data),

  // Leave
  listLeaveRequests: (params?: { employee_id?: string; approval_status?: string }) =>
    apiClient.get<LeaveRequest[]>(`${base}/leave/`, { params }).then((r) => r.data),
  createLeaveRequest: (data: Record<string, unknown>) =>
    apiClient.post<LeaveRequest>(`${base}/leave/`, data).then((r) => r.data),
  reviewLeaveRequest: (id: string, data: { approval_status: ApprovalStatus; review_note?: string }) =>
    apiClient.post<LeaveRequest>(`${base}/leave/${id}/review`, data).then((r) => r.data),
  listLeaveBalances: (params?: { employee_id?: string; year?: number }) =>
    apiClient.get<LeaveBalance[]>(`${base}/leave/balances/`, { params }).then((r) => r.data),

  // Payroll
  listPayrollPeriods: () =>
    apiClient.get<PayrollPeriod[]>(`${base}/payroll/periods/`).then((r) => r.data),
  createPayrollPeriod: (data: { period_month: number; period_year: number; notes?: string }) =>
    apiClient.post<PayrollPeriod>(`${base}/payroll/periods/`, data).then((r) => r.data),
  getPayrollPeriod: (id: string) =>
    apiClient.get<PayrollPeriodDetail>(`${base}/payroll/periods/${id}`).then((r) => r.data),
  addPayrollLine: (periodId: string, data: Record<string, unknown>) =>
    apiClient.post<PayrollLine>(`${base}/payroll/periods/${periodId}/lines/`, data).then((r) => r.data),
  updatePayrollLine: (lineId: string, data: Record<string, unknown>) =>
    apiClient.patch<PayrollLine>(`${base}/payroll/lines/${lineId}`, data).then((r) => r.data),
  approvePayrollPeriod: (id: string) =>
    apiClient.post<PayrollPeriod>(`${base}/payroll/periods/${id}/approve`).then((r) => r.data),
  exportPayrollPeriod: (id: string) =>
    apiClient.get<Record<string, unknown>[]>(`${base}/payroll/periods/${id}/export`).then((r) => r.data),

  deleteEmployee: (id: string) =>
    apiClient.delete(`${base}/employees/${id}`),
};
