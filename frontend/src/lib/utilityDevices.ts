import { apiClient } from "./api";
import { UtilityType, UTILITY_TYPE_LABELS } from "./utilityManagement";

// ── Device Enums ───────────────────────────────────────────────────────────────

export type DeviceType = "METER" | "SENSOR" | "LOGGER" | "CONTROLLER" | "ANALYSER";
export type ReadingType = "CUMULATIVE" | "INSTANTANEOUS" | "DIFFERENTIAL";
export type ReadingSource = "MANUAL" | "IOT" | "API" | "SCADA" | "IMPORTED";
export type ReadingFrequency =
  | "CONTINUOUS"
  | "EVERY_15MIN"
  | "HOURLY"
  | "EVERY_4H"
  | "DAILY"
  | "WEEKLY"
  | "ON_DEMAND";
export type ValidatedStatus = "PENDING" | "VALIDATED" | "REJECTED" | "AUTO_APPROVED";
export type SourceMethod = "MANUAL" | "IMPORTED" | "API" | "IOT" | "CALCULATED" | "ESTIMATED";
export type DataQuality = "GOOD" | "ESTIMATED" | "SUSPECT" | "MISSING";

// ── Label maps ─────────────────────────────────────────────────────────────────

export const DEVICE_TYPE_LABELS: Record<DeviceType, string> = {
  METER:      "Meter",
  SENSOR:     "Sensor",
  LOGGER:     "Data Logger",
  CONTROLLER: "Controller",
  ANALYSER:   "Analyser",
};

export const DEVICE_TYPE_OPTIONS = Object.entries(DEVICE_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const READING_TYPE_LABELS: Record<ReadingType, string> = {
  CUMULATIVE:    "Cumulative (Totalizer)",
  INSTANTANEOUS: "Instantaneous",
  DIFFERENTIAL:  "Differential",
};

export const READING_TYPE_OPTIONS = Object.entries(READING_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const READING_SOURCE_LABELS: Record<ReadingSource, string> = {
  MANUAL:   "Manual Entry",
  IOT:      "IoT / Sensor",
  API:      "External API",
  SCADA:    "SCADA",
  IMPORTED: "CSV Import",
};

export const READING_SOURCE_OPTIONS = Object.entries(READING_SOURCE_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const READING_FREQUENCY_LABELS: Record<ReadingFrequency, string> = {
  CONTINUOUS:  "Continuous",
  EVERY_15MIN: "Every 15 min",
  HOURLY:      "Hourly",
  EVERY_4H:    "Every 4 hours",
  DAILY:       "Daily",
  WEEKLY:      "Weekly",
  ON_DEMAND:   "On Demand",
};

export const READING_FREQUENCY_OPTIONS = Object.entries(READING_FREQUENCY_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const VALIDATED_STATUS_LABELS: Record<ValidatedStatus, string> = {
  PENDING:       "Pending",
  VALIDATED:     "Validated",
  REJECTED:      "Rejected",
  AUTO_APPROVED: "Auto-Approved",
};

export const VALIDATED_STATUS_OPTIONS = Object.entries(VALIDATED_STATUS_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const SOURCE_METHOD_LABELS: Record<SourceMethod, string> = {
  MANUAL:     "Manual",
  IMPORTED:   "Imported",
  API:        "External API",
  IOT:        "IoT",
  CALCULATED: "Calculated",
  ESTIMATED:  "Estimated",
};

export const DATA_QUALITY_LABELS: Record<DataQuality, string> = {
  GOOD:      "Good",
  ESTIMATED: "Estimated",
  SUSPECT:   "Suspect",
  MISSING:   "Missing",
};

// ── Utility Device ─────────────────────────────────────────────────────────────

export interface UtilityDevice {
  id: string;
  device_code: string;
  name: string;
  description: string | null;
  device_type: DeviceType;
  utility_type: UtilityType;
  asset_id: string | null;
  asset_no: string | null;
  asset_name: string | null;
  location: string | null;
  building_area: string | null;
  department: string | null;
  related_line_id: string | null;
  related_machine_id: string | null;
  reading_type: ReadingType | null;
  reading_source: ReadingSource | null;
  reading_frequency: ReadingFrequency | null;
  manufacturer: string | null;
  equipment_model: string | null;
  serial_no: string | null;
  install_date: string | null;
  last_calibration_date: string | null;
  next_calibration_date: string | null;
  calibration_required: boolean;
  calibration_frequency_days: number | null;
  unit_of_measure: string;
  min_value: string | null;
  max_value: string | null;
  pulse_factor: string | null;
  min_alarm_limit: string | null;
  max_alarm_limit: string | null;
  is_active: boolean;
  notes: string | null;
  reading_count: number;
  calibration_due: boolean;
}

export interface UtilityDeviceCreate {
  device_code: string;
  name: string;
  description?: string | null;
  device_type: DeviceType;
  utility_type: UtilityType;
  asset_id?: string | null;
  location?: string | null;
  building_area?: string | null;
  department?: string | null;
  related_line_id?: string | null;
  related_machine_id?: string | null;
  reading_type?: ReadingType | null;
  reading_source?: ReadingSource | null;
  reading_frequency?: ReadingFrequency | null;
  manufacturer?: string | null;
  equipment_model?: string | null;
  serial_no?: string | null;
  install_date?: string | null;
  last_calibration_date?: string | null;
  next_calibration_date?: string | null;
  calibration_required?: boolean;
  calibration_frequency_days?: number | null;
  unit_of_measure: string;
  min_value?: string | null;
  max_value?: string | null;
  pulse_factor?: string | null;
  min_alarm_limit?: string | null;
  max_alarm_limit?: string | null;
  is_active?: boolean;
  notes?: string | null;
}

export type UtilityDeviceUpdate = Partial<UtilityDeviceCreate>;

export interface DeviceFilters {
  utility_type?: UtilityType;
  device_type?: DeviceType;
  asset_id?: string;
  department?: string;
  building_area?: string;
  related_line_id?: string;
  related_machine_id?: string;
  is_active?: boolean;
  calibration_due_before?: string;
  search?: string;
}

// ── Utility Reading ────────────────────────────────────────────────────────────

export interface UtilityReading {
  id: string;
  reading_no: string;
  device_id: string;
  device_code: string | null;
  device_name: string | null;
  asset_id: string | null;
  reading_datetime: string;
  raw_value: string;
  adjusted_value: string | null;
  unit_of_measure: string;
  cumulative_value: string | null;
  interval_consumption: string | null;
  source_method: SourceMethod;
  source_reference: string | null;
  quality: DataQuality;
  is_anomaly: boolean;
  anomaly_note: string | null;
  validated_status: ValidatedStatus;
  validation_notes: string | null;
  department: string | null;
  building_area: string | null;
  shift_ref: string | null;
  batch_id: string | null;
  notes: string | null;
  created_at: string | null;
}

export interface UtilityReadingCreate {
  reading_no?: string | null;
  device_id: string;
  asset_id?: string | null;
  reading_datetime: string;    // ISO string
  raw_value: number | string;
  unit_of_measure?: string | null;
  cumulative_value?: number | string | null;
  source_method?: SourceMethod;
  source_reference?: string | null;
  department?: string | null;
  building_area?: string | null;
  shift_ref?: string | null;
  batch_id?: string | null;
  notes?: string | null;
}

export interface ReadingFilters {
  device_id?: string;
  asset_id?: string;
  department?: string;
  source_method?: SourceMethod;
  validated_status?: ValidatedStatus;
  is_anomaly?: boolean;
  batch_id?: string;
  from_dt?: string;
  to_dt?: string;
}

// ── API client ─────────────────────────────────────────────────────────────────

const BASE = "/api/v1/utility-management";

export const utilityDevicesApi = {
  // ── Devices ──────────────────────────────────────────────────────────────────
  devices: {
    async list(params?: DeviceFilters & { skip?: number; limit?: number }): Promise<UtilityDevice[]> {
      const res = await apiClient.get<UtilityDevice[]>(`${BASE}/devices`, { params });
      return res.data;
    },

    async get(id: string): Promise<UtilityDevice> {
      const res = await apiClient.get<UtilityDevice>(`${BASE}/devices/${id}`);
      return res.data;
    },

    async create(data: UtilityDeviceCreate): Promise<UtilityDevice> {
      const res = await apiClient.post<UtilityDevice>(`${BASE}/devices`, data);
      return res.data;
    },

    async update(id: string, data: UtilityDeviceUpdate): Promise<UtilityDevice> {
      const res = await apiClient.patch<UtilityDevice>(`${BASE}/devices/${id}`, data);
      return res.data;
    },

    async delete(id: string): Promise<void> {
      await apiClient.delete(`${BASE}/devices/${id}`).then((r) => r.data);
    },
  },

  // ── Readings ──────────────────────────────────────────────────────────────────
  readings: {
    async list(params?: ReadingFilters & { skip?: number; limit?: number }): Promise<UtilityReading[]> {
      const res = await apiClient.get<UtilityReading[]>(`${BASE}/readings`, { params });
      return res.data;
    },

    async get(id: string): Promise<UtilityReading> {
      const res = await apiClient.get<UtilityReading>(`${BASE}/readings/${id}`);
      return res.data;
    },

    async create(data: UtilityReadingCreate): Promise<UtilityReading> {
      const res = await apiClient.post<UtilityReading>(`${BASE}/readings`, data);
      return res.data;
    },

    async validate(id: string, status: ValidatedStatus, notes?: string): Promise<UtilityReading> {
      const res = await apiClient.patch<UtilityReading>(`${BASE}/readings/${id}/validate`, {
        validated_status: status,
        validation_notes: notes ?? null,
      });
      return res.data;
    },

    async delete(id: string): Promise<void> {
      await apiClient.delete(`${BASE}/readings/${id}`).then((r) => r.data);
    },
  },
};

// ── Authenticated CSV download helper ────────────────────────────────────────

export async function downloadAuthenticatedCsvDevices(path: string, filename: string): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "";
  const res = await fetch(`${base}${path}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Export failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
