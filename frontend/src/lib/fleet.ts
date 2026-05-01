import { apiClient } from "./api";

export type VehicleType = "truck" | "van" | "motorcycle" | "pickup" | "third_party";
export type VehicleStatus = "active" | "in_service" | "maintenance" | "inactive";
export type FuelType = "petrol" | "diesel" | "electric" | "hybrid";
export type TripStatus = "planned" | "in_progress" | "completed" | "cancelled";
export type MaintenanceType = "service" | "repair" | "inspection" | "tyre" | "other";
export type IncidentType = "accident" | "damage" | "theft" | "breakdown" | "other";
export type IncidentStatus = "open" | "under_review" | "resolved" | "closed";
export type DriverStatus = "available" | "on_trip" | "off_duty" | "inactive";

export interface Vehicle {
  id: string;
  vehicle_code: string;
  plate_number: string;
  vehicle_type: VehicleType;
  make?: string;
  model?: string;
  year?: number;
  capacity_weight_kg?: number;
  capacity_volume_m3?: number;
  fuel_type: FuelType;
  status: VehicleStatus;
  purchase_date?: string;
  odometer_km?: number;
  assigned_driver_id?: string;
  notes?: string;
  created_at: string;
}

export interface FleetDriver {
  id: string;
  driver_code: string;
  full_name: string;
  phone?: string;
  email?: string;
  license_number: string;
  license_class?: string;
  license_expiry?: string;
  status: DriverStatus;
  employee_id?: string;
  created_at: string;
}

export interface FleetTrip {
  id: string;
  trip_no: string;
  vehicle_id: string;
  driver_id?: string;
  trip_date: string;
  start_time?: string;
  end_time?: string;
  start_location?: string;
  end_location?: string;
  planned_distance_km?: number;
  actual_distance_km?: number;
  status: TripStatus;
  purpose?: string;
  cargo_weight_kg?: number;
  fuel_used_liters?: number;
  trip_cost?: number;
  created_at: string;
}

export interface FuelLog {
  id: string;
  vehicle_id: string;
  trip_id?: string;
  fuel_date: string;
  fuel_quantity_liters: number;
  fuel_cost: number;
  cost_per_liter?: number;
  odometer_reading?: number;
  fuel_station?: string;
  created_at: string;
}

export interface MaintenanceRecord {
  id: string;
  vehicle_id: string;
  maintenance_type: MaintenanceType;
  maintenance_date: string;
  description?: string;
  cost?: number;
  odometer_at_service?: number;
  next_due_date?: string;
  vendor?: string;
  downtime_days?: number;
  completed: boolean;
  created_at: string;
}

export interface IncidentLog {
  id: string;
  vehicle_id: string;
  driver_id?: string;
  incident_date: string;
  incident_type: IncidentType;
  description?: string;
  location?: string;
  cost_estimate?: number;
  insurance_claim_no?: string;
  status: IncidentStatus;
  resolved_date?: string;
  created_at: string;
}

export interface FleetDashboard {
  total_vehicles: number;
  active_vehicles: number;
  in_maintenance: number;
  trips_today: number;
  trips_in_progress: number;
  fuel_cost_this_month: number;
  maintenance_cost_this_month: number;
  open_incidents: number;
  available_drivers: number;
  upcoming_maintenance: Array<Record<string, unknown>>;
  recent_trips: Array<Record<string, unknown>>;
}

const BASE = "/api/v1/fleet";

export async function getDashboard(): Promise<FleetDashboard> {
  const res = await apiClient.get<FleetDashboard>(`${BASE}/dashboard`);
  return res.data;
}

// Vehicles
export async function listVehicles(params?: { status?: VehicleStatus; vehicle_type?: VehicleType }): Promise<Vehicle[]> {
  const res = await apiClient.get<Vehicle[]>(`${BASE}/vehicles`, { params });
  return res.data;
}
export async function createVehicle(data: Partial<Vehicle>): Promise<Vehicle> {
  const res = await apiClient.post<Vehicle>(`${BASE}/vehicles`, data);
  return res.data;
}
export async function updateVehicle(id: string, data: Partial<Vehicle>): Promise<Vehicle> {
  const res = await apiClient.patch<Vehicle>(`${BASE}/vehicles/${id}`, data);
  return res.data;
}
export async function checkAvailability(id: string, check_date: string): Promise<{ available: boolean; reason?: string }> {
  const res = await apiClient.get(`${BASE}/vehicles/${id}/availability`, { params: { check_date } });
  return res.data;
}

// Drivers
export async function listDrivers(params?: { status?: DriverStatus }): Promise<FleetDriver[]> {
  const res = await apiClient.get<FleetDriver[]>(`${BASE}/drivers`, { params });
  return res.data;
}
export async function createDriver(data: Partial<FleetDriver>): Promise<FleetDriver> {
  const res = await apiClient.post<FleetDriver>(`${BASE}/drivers`, data);
  return res.data;
}
export async function updateDriver(id: string, data: Partial<FleetDriver>): Promise<FleetDriver> {
  const res = await apiClient.patch<FleetDriver>(`${BASE}/drivers/${id}`, data);
  return res.data;
}

// Trips
export async function listTrips(params?: { vehicle_id?: string; status?: TripStatus; trip_date?: string }): Promise<FleetTrip[]> {
  const res = await apiClient.get<FleetTrip[]>(`${BASE}/trips`, { params });
  return res.data;
}
export async function createTrip(data: Partial<FleetTrip>): Promise<FleetTrip> {
  const res = await apiClient.post<FleetTrip>(`${BASE}/trips`, data);
  return res.data;
}
export async function updateTrip(id: string, data: Partial<FleetTrip>): Promise<FleetTrip> {
  const res = await apiClient.patch<FleetTrip>(`${BASE}/trips/${id}`, data);
  return res.data;
}

// Fuel
export async function listFuelLogs(params?: { vehicle_id?: string }): Promise<FuelLog[]> {
  const res = await apiClient.get<FuelLog[]>(`${BASE}/fuel`, { params });
  return res.data;
}
export async function createFuelLog(data: Partial<FuelLog>): Promise<FuelLog> {
  const res = await apiClient.post<FuelLog>(`${BASE}/fuel`, data);
  return res.data;
}

// Maintenance
export async function listMaintenance(params?: { vehicle_id?: string; completed?: boolean }): Promise<MaintenanceRecord[]> {
  const res = await apiClient.get<MaintenanceRecord[]>(`${BASE}/maintenance`, { params });
  return res.data;
}
export async function createMaintenance(data: Partial<MaintenanceRecord>): Promise<MaintenanceRecord> {
  const res = await apiClient.post<MaintenanceRecord>(`${BASE}/maintenance`, data);
  return res.data;
}
export async function updateMaintenance(id: string, data: Partial<MaintenanceRecord>): Promise<MaintenanceRecord> {
  const res = await apiClient.patch<MaintenanceRecord>(`${BASE}/maintenance/${id}`, data);
  return res.data;
}

// Incidents
export async function listIncidents(params?: { vehicle_id?: string; status?: IncidentStatus }): Promise<IncidentLog[]> {
  const res = await apiClient.get<IncidentLog[]>(`${BASE}/incidents`, { params });
  return res.data;
}
export async function createIncident(data: Partial<IncidentLog>): Promise<IncidentLog> {
  const res = await apiClient.post<IncidentLog>(`${BASE}/incidents`, data);
  return res.data;
}
export async function updateIncident(id: string, data: Partial<IncidentLog>): Promise<IncidentLog> {
  const res = await apiClient.patch<IncidentLog>(`${BASE}/incidents/${id}`, data);
  return res.data;
}

// Reports
export async function getUtilizationReport(days = 30): Promise<unknown[]> {
  const res = await apiClient.get(`${BASE}/reports/utilization`, { params: { days } });
  return res.data;
}
export async function getFuelReport(days = 30): Promise<unknown[]> {
  const res = await apiClient.get(`${BASE}/reports/fuel`, { params: { days } });
  return res.data;
}
export async function getMaintenanceReport(days = 90): Promise<unknown[]> {
  const res = await apiClient.get(`${BASE}/reports/maintenance`, { params: { days } });
  return res.data;
}
export async function getDriverReport(days = 30): Promise<unknown[]> {
  const res = await apiClient.get(`${BASE}/reports/drivers`, { params: { days } });
  return res.data;
}

// AI
export async function getRouteEfficiency(): Promise<unknown> {
  return (await apiClient.get(`${BASE}/ai/route-efficiency`)).data;
}
export async function getFuelAnomaly(): Promise<unknown> {
  return (await apiClient.get(`${BASE}/ai/fuel-anomaly`)).data;
}
export async function getMaintenancePredictor(): Promise<unknown> {
  return (await apiClient.get(`${BASE}/ai/maintenance-predictor`)).data;
}

// Helpers
export const VEHICLE_STATUS_BADGE: Record<VehicleStatus, string> = {
  active: "bg-green-100 text-green-800",
  in_service: "bg-blue-100 text-blue-800",
  maintenance: "bg-amber-100 text-amber-800",
  inactive: "bg-gray-100 text-gray-500",
};

export const TRIP_STATUS_BADGE: Record<TripStatus, string> = {
  planned: "bg-gray-100 text-gray-700",
  in_progress: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-700",
};

export const DRIVER_STATUS_BADGE: Record<DriverStatus, string> = {
  available: "bg-green-100 text-green-800",
  on_trip: "bg-blue-100 text-blue-800",
  off_duty: "bg-gray-100 text-gray-500",
  inactive: "bg-red-100 text-red-700",
};

export const INCIDENT_STATUS_BADGE: Record<IncidentStatus, string> = {
  open: "bg-red-100 text-red-800",
  under_review: "bg-amber-100 text-amber-800",
  resolved: "bg-blue-100 text-blue-800",
  closed: "bg-gray-100 text-gray-500",
};
