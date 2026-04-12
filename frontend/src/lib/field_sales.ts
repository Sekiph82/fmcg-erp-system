import { apiClient } from "./api";

export type VehicleType = "MOTORBIKE" | "VAN" | "TRUCK" | "FOOT" | "OTHER";
export type VisitOutcome = "ORDERED" | "NO_ORDER" | "CUSTOMER_CLOSED" | "CREDIT_HOLD" | "NOT_FOUND";

export interface SalesRep {
  id: string;
  code: string;
  name: string;
  phone?: string;
  region?: string;
  territory?: string;
  vehicle_type: VehicleType;
  is_active: boolean;
  user_id?: string;
  created_at: string;
}

export interface RouteStop {
  id: string;
  customer_id: string;
  customer_name?: string;
  stop_sequence: number;
  notes?: string;
}

export interface SalesRoute {
  id: string;
  code: string;
  name: string;
  region?: string;
  description?: string;
  assigned_rep_id?: string;
  rep_name?: string;
  is_active: boolean;
  stop_count: number;
  stops: RouteStop[];
}

export interface DailyTarget {
  id: string;
  rep_id: string;
  rep_name?: string;
  route_id?: string;
  route_name?: string;
  target_date: string;
  target_amount: number;
  target_orders: number;
  actual_amount?: number;
  actual_orders?: number;
  currency: string;
}

export interface VisitLog {
  id: string;
  rep_id: string;
  rep_name?: string;
  customer_id: string;
  customer_name?: string;
  route_id?: string;
  order_id?: string;
  visit_date: string;
  visited_at?: string;
  outcome: VisitOutcome;
  gps_lat?: number;
  gps_lng?: number;
  notes?: string;
  created_at: string;
}

export const fieldSalesApi = {
  // Reps
  listReps: (params?: { region?: string; active_only?: boolean }) =>
    apiClient.get<SalesRep[]>("/api/v1/field-sales/reps", { params }).then((r) => r.data),
  createRep: (data: Partial<SalesRep>) =>
    apiClient.post<SalesRep>("/api/v1/field-sales/reps", data).then((r) => r.data),
  updateRep: (id: string, data: Partial<SalesRep>) =>
    apiClient.patch<SalesRep>(`/api/v1/field-sales/reps/${id}`, data).then((r) => r.data),

  // Routes
  listRoutes: (params?: { region?: string }) =>
    apiClient.get<SalesRoute[]>("/api/v1/field-sales/routes", { params }).then((r) => r.data),
  createRoute: (data: Partial<SalesRoute> & { stops?: Partial<RouteStop>[] }) =>
    apiClient.post<SalesRoute>("/api/v1/field-sales/routes", data).then((r) => r.data),
  getRoute: (id: string) =>
    apiClient.get<SalesRoute>(`/api/v1/field-sales/routes/${id}`).then((r) => r.data),

  // Targets
  listTargets: (params?: { rep_id?: string; from_date?: string; to_date?: string }) =>
    apiClient.get<DailyTarget[]>("/api/v1/field-sales/targets", { params }).then((r) => r.data),
  upsertTarget: (data: Partial<DailyTarget>) =>
    apiClient.post<DailyTarget>("/api/v1/field-sales/targets", data).then((r) => r.data),

  // Visits
  listVisits: (params?: { rep_id?: string; visit_date?: string; route_id?: string }) =>
    apiClient.get<VisitLog[]>("/api/v1/field-sales/visits", { params }).then((r) => r.data),
  logVisit: (data: Partial<VisitLog>) =>
    apiClient.post<VisitLog>("/api/v1/field-sales/visits", data).then((r) => r.data),
};
