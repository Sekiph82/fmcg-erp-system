import { apiClient } from "@/lib/api";

export type CustomerChannel = "RETAIL" | "WHOLESALE" | "DISTRIBUTOR" | "DIRECT" | "EXPORT" | "ONLINE";
export type SOStatus = "DRAFT" | "CONFIRMED" | "ALLOCATED" | "PICKING" | "SHIPPED" | "INVOICED" | "CANCELLED";
export type ShipmentStatus = "PENDING" | "PICKING" | "PACKED" | "DISPATCHED" | "DELIVERED" | "CANCELLED";
export type InvoiceStatus = "DRAFT" | "ISSUED" | "PARTIALLY_PAID" | "PAID" | "OVERDUE" | "CANCELLED";
export type PaymentMethod = "cash" | "mpesa" | "bank_transfer" | "credit";
export type SOPaymentStatus = "pending" | "partially_paid" | "paid" | "failed";
export type MpesaTxStatus = "pending" | "completed" | "failed" | "cancelled";

export interface Customer {
  id: string;
  code: string;
  name: string;
  contact_person?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  country?: string;
  delivery_address?: string;
  delivery_city?: string;
  delivery_country?: string;
  channel: CustomerChannel;
  payment_terms_days: number;
  credit_limit?: number;
  tax_id?: string;
  currency: string;
  notes?: string;
  is_active: boolean;
  is_prepaid: boolean;
  created_at: string;
}

export interface SOLine {
  id: string;
  line_no: number;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  ordered_quantity: number;
  unit: string;
  unit_price: number;
  discount_pct: number;
  tax_rate: number;
  allocated_quantity: number;
  shipped_quantity: number;
  notes?: string;
  net_price: number;
  line_total: number;
  pending_quantity: number;
  unallocated_quantity: number;
}

export interface SalesOrder {
  id: string;
  order_no: string;
  customer_id: string;
  customer_name?: string;
  order_date: string;
  requested_delivery_date: string;
  status: SOStatus;
  warehouse_id?: string;
  warehouse_name?: string;
  currency: string;
  notes?: string;
  confirmed_at?: string;
  created_at: string;
  total_value?: number;
  line_count: number;
  days_until_delivery?: number;
  payment_method: PaymentMethod;
  payment_status: SOPaymentStatus;
  mpesa_reference?: string;
  mpesa_request_id?: string;
  lines?: SOLine[];
  shipments?: any[];
  invoices?: any[];
}

export interface ShipmentLine {
  id: string;
  so_line_id?: string;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  lot_id?: string;
  lot_number?: string;
  quantity: number;
  unit: string;
  is_picked: boolean;
  picked_by_id?: string;
  stock_movement_id?: string;
}

export interface Shipment {
  id: string;
  shipment_no: string;
  so_id: string;
  so_no?: string;
  customer_name?: string;
  warehouse_id: string;
  warehouse_name?: string;
  status: ShipmentStatus;
  scheduled_date: string;
  dispatched_date?: string;
  carrier?: string;
  tracking_number?: string;
  delivery_notes?: string;
  created_at: string;
  line_count: number;
  picked_count: number;
  lines?: ShipmentLine[];
}

export interface InvoiceLine {
  id: string;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  description?: string;
  quantity: number;
  unit: string;
  unit_price: number;
  discount_pct: number;
  tax_rate: number;
  line_total: number;
}

export interface Payment {
  id: string;
  invoice_id: string;
  payment_date: string;
  amount: number;
  reference?: string;
  notes?: string;
  created_at: string;
}

export interface Invoice {
  id: string;
  invoice_no: string;
  so_id: string;
  so_no?: string;
  shipment_id?: string;
  customer_id: string;
  customer_name?: string;
  invoice_date: string;
  due_date: string;
  status: InvoiceStatus;
  currency: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  notes?: string;
  created_at: string;
  outstanding_balance: number;
  days_overdue?: number;
  lines?: InvoiceLine[];
  payments?: Payment[];
}

export interface OutstandingInvoiceRow {
  invoice_id: string;
  invoice_no: string;
  customer_name: string;
  invoice_date: string;
  due_date: string;
  total_amount: number;
  paid_amount: number;
  outstanding_balance: number;
  days_overdue?: number;
  status: InvoiceStatus;
}

export interface SalesSummary {
  total_orders: number;
  confirmed_orders: number;
  total_order_value: number;
  total_invoiced: number;
  total_collected: number;
  outstanding_balance: number;
  overdue_invoices: number;
}

export interface MpesaTransaction {
  id: string;
  so_id: string;
  phone_number: string;
  amount: number;
  mpesa_request_id?: string;
  mpesa_reference?: string;
  status: MpesaTxStatus;
  result_code?: number;
  result_description?: string;
  created_at: string;
}

export interface SOLineCreate {
  line_no: number;
  product_id: string;
  ordered_quantity: number;
  unit: string;
  unit_price: number;
  discount_pct: number;
  tax_rate: number;
  notes?: string;
}

export interface SOCreate {
  order_no: string;
  customer_id: string;
  order_date: string;
  requested_delivery_date: string;
  warehouse_id?: string;
  currency: string;
  notes?: string;
  lines: SOLineCreate[];
}

export interface ShipmentLineCreate {
  so_line_id?: string;
  product_id: string;
  lot_id?: string;
  quantity: number;
  unit: string;
}

export interface ShipmentCreate {
  shipment_no: string;
  so_id: string;
  warehouse_id: string;
  scheduled_date: string;
  carrier?: string;
  tracking_number?: string;
  delivery_notes?: string;
  lines: ShipmentLineCreate[];
}

export const salesApi = {
  // Customers
  async listCustomers(activeOnly = false): Promise<Customer[]> {
    const res = await apiClient.get<Customer[]>(`/api/v1/sales/customers/?active_only=${activeOnly}`);
    return res.data;
  },
  async getCustomer(id: string): Promise<Customer> {
    const res = await apiClient.get<Customer>(`/api/v1/sales/customers/${id}`);
    return res.data;
  },
  async createCustomer(data: Partial<Customer>): Promise<Customer> {
    const res = await apiClient.post<Customer>("/api/v1/sales/customers/", data);
    return res.data;
  },
  async updateCustomer(id: string, data: Partial<Customer>): Promise<Customer> {
    const res = await apiClient.patch<Customer>(`/api/v1/sales/customers/${id}`, data);
    return res.data;
  },

  // Sales Orders
  async listOrders(params?: { status?: SOStatus; customer_id?: string; from_date?: string; to_date?: string }): Promise<SalesOrder[]> {
    const res = await apiClient.get<SalesOrder[]>("/api/v1/sales/orders/", { params });
    return res.data;
  },
  async getOrder(id: string): Promise<SalesOrder> {
    const res = await apiClient.get<SalesOrder>(`/api/v1/sales/orders/${id}`);
    return res.data;
  },
  async createOrder(data: SOCreate): Promise<SalesOrder> {
    const res = await apiClient.post<SalesOrder>("/api/v1/sales/orders/", data);
    return res.data;
  },
  async updateOrder(id: string, data: Partial<SalesOrder>): Promise<SalesOrder> {
    const res = await apiClient.patch<SalesOrder>(`/api/v1/sales/orders/${id}`, data);
    return res.data;
  },
  async confirmOrder(id: string): Promise<SalesOrder> {
    const res = await apiClient.post<SalesOrder>(`/api/v1/sales/orders/${id}/confirm`, {});
    return res.data;
  },
  async allocateOrder(id: string, warehouse_id: string): Promise<SalesOrder> {
    const res = await apiClient.post<SalesOrder>(`/api/v1/sales/orders/${id}/allocate`, { warehouse_id });
    return res.data;
  },
  async cancelOrder(id: string): Promise<SalesOrder> {
    const res = await apiClient.post<SalesOrder>(`/api/v1/sales/orders/${id}/cancel`, {});
    return res.data;
  },

  // Shipments
  async listShipments(params?: { status?: ShipmentStatus; so_id?: string }): Promise<Shipment[]> {
    const res = await apiClient.get<Shipment[]>("/api/v1/sales/shipments/", { params });
    return res.data;
  },
  async getShipment(id: string): Promise<Shipment> {
    const res = await apiClient.get<Shipment>(`/api/v1/sales/shipments/${id}`);
    return res.data;
  },
  async createShipment(data: ShipmentCreate): Promise<Shipment> {
    const res = await apiClient.post<Shipment>("/api/v1/sales/shipments/", data);
    return res.data;
  },
  async startPicking(id: string): Promise<Shipment> {
    const res = await apiClient.post<Shipment>(`/api/v1/sales/shipments/${id}/start-picking`, {});
    return res.data;
  },
  async pickLine(shipmentId: string, lineId: string): Promise<ShipmentLine> {
    const res = await apiClient.post<ShipmentLine>(`/api/v1/sales/shipments/${shipmentId}/lines/${lineId}/pick`, {});
    return res.data;
  },
  async dispatchShipment(id: string, dispatched_date?: string): Promise<Shipment> {
    const res = await apiClient.post<Shipment>(`/api/v1/sales/shipments/${id}/dispatch`, { dispatched_date });
    return res.data;
  },

  // Invoices
  async listInvoices(params?: { status?: InvoiceStatus; customer_id?: string }): Promise<Invoice[]> {
    const res = await apiClient.get<Invoice[]>("/api/v1/sales/invoices/", { params });
    return res.data;
  },
  async getInvoice(id: string): Promise<Invoice> {
    const res = await apiClient.get<Invoice>(`/api/v1/sales/invoices/${id}`);
    return res.data;
  },
  async createInvoiceFromShipment(shipmentId: string, data: { invoice_no: string; invoice_date: string; due_date: string; notes?: string }): Promise<Invoice> {
    const res = await apiClient.post<Invoice>(`/api/v1/sales/shipments/${shipmentId}/invoice`, data);
    return res.data;
  },
  async recordPayment(invoiceId: string, data: { payment_date: string; amount: number; reference?: string; notes?: string }): Promise<Payment> {
    const res = await apiClient.post<Payment>(`/api/v1/sales/invoices/${invoiceId}/payments`, data);
    return res.data;
  },
  async syncOverdue(): Promise<{ updated: number }> {
    const res = await apiClient.post<{ updated: number }>("/api/v1/sales/invoices/sync-overdue", {});
    return res.data;
  },

  // M-Pesa
  async initiateMpesaPayment(soId: string, data: { phone_number: string; amount: number }): Promise<MpesaTransaction> {
    const res = await apiClient.post<MpesaTransaction>(`/api/v1/sales/orders/${soId}/mpesa/initiate`, data);
    return res.data;
  },
  async listMpesaTransactions(soId: string): Promise<MpesaTransaction[]> {
    const res = await apiClient.get<MpesaTransaction[]>(`/api/v1/sales/orders/${soId}/mpesa/transactions`);
    return res.data;
  },

  // Reports
  async getOutstandingInvoices(): Promise<OutstandingInvoiceRow[]> {
    const res = await apiClient.get<OutstandingInvoiceRow[]>("/api/v1/sales/reports/outstanding");
    return res.data;
  },
  async getSalesSummary(): Promise<SalesSummary> {
    const res = await apiClient.get<SalesSummary>("/api/v1/sales/reports/summary");
    return res.data;
  },
};

export function extractApiError(error: unknown): string {
  const e = error as { response?: { data?: { detail?: string | { message?: string } } } };
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (typeof detail === "object" && detail?.message) return detail.message;
  return "An error occurred";
}
