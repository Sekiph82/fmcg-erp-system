import { apiClient } from "./api";

// ── Types ──────────────────────────────────────────────────────────────────────

export type ConfigCategory =
  | "COMPANY"
  | "SYSTEM"
  | "FINANCE"
  | "NOTIFICATIONS"
  | "OPERATIONS";

export interface SystemConfig {
  id: string;
  key: string;
  value: string | null;
  description: string | null;
  category: ConfigCategory;
  is_editable: boolean;
  updated_by_id: string | null;
}

export interface SystemConfigCreate {
  key: string;
  value?: string | null;
  description?: string | null;
  category?: ConfigCategory;
  is_editable?: boolean;
}

export interface SystemConfigUpdate {
  value?: string | null;
  description?: string | null;
  category?: ConfigCategory;
  is_editable?: boolean;
}

export interface UomConversion {
  id: string;
  from_uom: string;
  to_uom: string;
  factor: string;
  is_active: boolean;
}

export interface UomConversionCreate {
  from_uom: string;
  to_uom: string;
  factor: string;
  is_active?: boolean;
}

export interface UomConversionUpdate {
  factor?: string;
  is_active?: boolean;
}

export interface NumberSeries {
  id: string;
  module: string;
  label: string;
  prefix: string;
  suffix: string | null;
  current_number: number;
  padding: number;
  is_active: boolean;
}

export interface NumberSeriesCreate {
  module: string;
  label: string;
  prefix: string;
  suffix?: string | null;
  current_number?: number;
  padding?: number;
  is_active?: boolean;
}

export interface NumberSeriesUpdate {
  label?: string;
  prefix?: string;
  suffix?: string | null;
  current_number?: number;
  padding?: number;
  is_active?: boolean;
}

export interface NextNumberResponse {
  module: string;
  number: string;
  sequence: number;
}

export interface Currency {
  id: string;
  code: string;
  name: string;
  symbol: string;
  exchange_rate: string;
  is_base: boolean;
  is_active: boolean;
}

export interface CurrencyCreate {
  code: string;
  name: string;
  symbol: string;
  exchange_rate?: string;
  is_base?: boolean;
  is_active?: boolean;
}

export interface CurrencyUpdate {
  name?: string;
  symbol?: string;
  exchange_rate?: string;
  is_base?: boolean;
  is_active?: boolean;
}

// ── API ────────────────────────────────────────────────────────────────────────

export const utilitiesApi = {
  // System Configs
  configs: {
    async list(category?: ConfigCategory, skip = 0, limit = 200): Promise<SystemConfig[]> {
      const params: Record<string, unknown> = { skip, limit };
      if (category) params.category = category;
      const res = await apiClient.get<SystemConfig[]>("/api/v1/utilities/configs", { params });
      return res.data;
    },
    async get(id: string): Promise<SystemConfig> {
      const res = await apiClient.get<SystemConfig>(`/api/v1/utilities/configs/${id}`);
      return res.data;
    },
    async create(data: SystemConfigCreate): Promise<SystemConfig> {
      const res = await apiClient.post<SystemConfig>("/api/v1/utilities/configs", data);
      return res.data;
    },
    async update(id: string, data: SystemConfigUpdate): Promise<SystemConfig> {
      const res = await apiClient.patch<SystemConfig>(`/api/v1/utilities/configs/${id}`, data);
      return res.data;
    },
    async delete(id: string): Promise<void> {
      await apiClient.delete(`/api/v1/utilities/configs/${id}`).then((r) => r.data);
    },
  },

  // UOM Conversions
  uomConversions: {
    async list(skip = 0, limit = 200): Promise<UomConversion[]> {
      const res = await apiClient.get<UomConversion[]>("/api/v1/utilities/uom-conversions", {
        params: { skip, limit },
      });
      return res.data;
    },
    async get(id: string): Promise<UomConversion> {
      const res = await apiClient.get<UomConversion>(`/api/v1/utilities/uom-conversions/${id}`);
      return res.data;
    },
    async create(data: UomConversionCreate): Promise<UomConversion> {
      const res = await apiClient.post<UomConversion>("/api/v1/utilities/uom-conversions", data);
      return res.data;
    },
    async update(id: string, data: UomConversionUpdate): Promise<UomConversion> {
      const res = await apiClient.patch<UomConversion>(`/api/v1/utilities/uom-conversions/${id}`, data);
      return res.data;
    },
    async delete(id: string): Promise<void> {
      await apiClient.delete(`/api/v1/utilities/uom-conversions/${id}`).then((r) => r.data);
    },
  },

  // Number Series
  numberSeries: {
    async list(skip = 0, limit = 200): Promise<NumberSeries[]> {
      const res = await apiClient.get<NumberSeries[]>("/api/v1/utilities/number-series", {
        params: { skip, limit },
      });
      return res.data;
    },
    async get(id: string): Promise<NumberSeries> {
      const res = await apiClient.get<NumberSeries>(`/api/v1/utilities/number-series/${id}`);
      return res.data;
    },
    async create(data: NumberSeriesCreate): Promise<NumberSeries> {
      const res = await apiClient.post<NumberSeries>("/api/v1/utilities/number-series", data);
      return res.data;
    },
    async update(id: string, data: NumberSeriesUpdate): Promise<NumberSeries> {
      const res = await apiClient.patch<NumberSeries>(`/api/v1/utilities/number-series/${id}`, data);
      return res.data;
    },
    async delete(id: string): Promise<void> {
      await apiClient.delete(`/api/v1/utilities/number-series/${id}`).then((r) => r.data);
    },
    async getNextNumber(module: string): Promise<NextNumberResponse> {
      const res = await apiClient.post<NextNumberResponse>(
        `/api/v1/utilities/number-series/next/${module}`
      );
      return res.data;
    },
  },

  // Currencies
  currencies: {
    async list(skip = 0, limit = 200): Promise<Currency[]> {
      const res = await apiClient.get<Currency[]>("/api/v1/utilities/currencies", {
        params: { skip, limit },
      });
      return res.data;
    },
    async get(id: string): Promise<Currency> {
      const res = await apiClient.get<Currency>(`/api/v1/utilities/currencies/${id}`);
      return res.data;
    },
    async create(data: CurrencyCreate): Promise<Currency> {
      const res = await apiClient.post<Currency>("/api/v1/utilities/currencies", data);
      return res.data;
    },
    async update(id: string, data: CurrencyUpdate): Promise<Currency> {
      const res = await apiClient.patch<Currency>(`/api/v1/utilities/currencies/${id}`, data);
      return res.data;
    },
    async delete(id: string): Promise<void> {
      await apiClient.delete(`/api/v1/utilities/currencies/${id}`).then((r) => r.data);
    },
  },
};
