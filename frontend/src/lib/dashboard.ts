import { apiClient } from "./api";

export interface TrendPoint {
  date: string;
  value: number;
}

export interface ProductionSummary {
  active_orders: number;
  today_planned_qty: number;
  today_actual_qty: number;
  completion_rate: number;
  machines_down: number;
  open_breakdowns: number;
  trend_7d: TrendPoint[];
}

export interface LowStockItem {
  id: string;
  name: string;
  item_type: "product" | "material";
  quantity_on_hand: number;
  reorder_point: number;
  uom: string;
}

export interface InventorySummary {
  total_stock_value: number;
  total_sku_count: number;
  critical_low_stock_count: number;
  low_stock_items: LowStockItem[];
}

export interface SalesSummary {
  today_invoices_amount: number;
  today_orders_count: number;
  pending_payments_amount: number;
  overdue_invoices_count: number;
  pending_shipments_count: number;
  trend_7d: TrendPoint[];
}

export interface MpesaTransactionRow {
  id: string;
  phone_number: string;
  amount: number;
  status: string;
  reference: string | null;
  created_at: string;
}

export interface MpesaSummary {
  today_collected: number;
  pending_count: number;
  failed_today: number;
  total_today: number;
  success_rate: number;
  last_10: MpesaTransactionRow[];
}

export interface LogisticsSummary {
  in_transit: number;
  arrived_port: number;
  customs_hold: number;
  delayed_count: number;
  arrivals_this_week: number;
}

export interface AlertItem {
  id: string;
  severity: "low" | "medium" | "critical";
  module: string;
  message: string;
  timestamp: string;
  action_url: string;
}

export interface DashboardSummary {
  generated_at: string;
  production: ProductionSummary;
  inventory: InventorySummary;
  sales: SalesSummary;
  mpesa: MpesaSummary;
  logistics: LogisticsSummary;
  alerts: AlertItem[];
}

export const dashboardApi = {
  getSummary: async (): Promise<DashboardSummary> => {
    const res = await apiClient.get<DashboardSummary>("/api/v1/dashboard/summary").then((r) => r.data);
    return res.data;
  },
};
