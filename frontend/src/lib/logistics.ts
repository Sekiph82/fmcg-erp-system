import { apiClient } from "@/lib/api";

export type LocalCostType =
  | "TRANSPORT" | "CLEARING_FEE" | "PORT_HANDLING"
  | "WAREHOUSE_HANDLING" | "FUMIGATION" | "INSPECTION_FEE" | "OTHER";
export type LocalPaymentMethod = "MPESA" | "BANK" | "CASH";
export type LocalCostStatus = "PENDING" | "PAID" | "DISPUTED";

export type ShipmentMode = "SEA" | "AIR" | "ROAD" | "RAIL";
export type IntlShipmentStatus =
  | "DRAFT" | "BOOKING_CONFIRMED" | "CARGO_LOADED" | "IN_TRANSIT"
  | "ARRIVED_PORT" | "CUSTOMS_HOLD" | "CUSTOMS_CLEARED"
  | "OUT_FOR_DELIVERY" | "DELIVERED" | "CANCELLED";
export type ContainerType = "20FT_DRY" | "40FT_DRY" | "40FT_HC" | "20FT_REEFER" | "LCL";
export type ContainerStatus = "EMPTY" | "LOADING" | "LOADED" | "IN_TRANSIT" | "AT_PORT" | "CUSTOMS_HOLD" | "RELEASED" | "RETURNED";
export type CustomsDocType =
  | "COMMERCIAL_INVOICE" | "PACKING_LIST" | "BILL_OF_LADING" | "AIRWAY_BILL"
  | "CERTIFICATE_OF_ORIGIN" | "PHYTOSANITARY" | "IMPORT_DECLARATION" | "DUTY_RECEIPT" | "OTHER";
export type CustomsDocStatus = "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED";
export type ClearanceStatus =
  | "PENDING" | "DOCS_SUBMITTED" | "UNDER_REVIEW" | "EXAM_REQUESTED"
  | "DUTY_ASSESSED" | "DUTY_PAID" | "CLEARED" | "HELD";

export interface IntlShipment {
  id: string;
  shipment_no: string;
  mode: ShipmentMode;
  origin_country: string;
  origin_city?: string;
  origin_port?: string;
  destination_country: string;
  destination_city: string;
  destination_port: string;
  final_destination?: string;
  carrier?: string;
  vessel_name?: string;
  voyage_no?: string;
  bl_number?: string;
  planned_departure?: string;
  actual_departure?: string;
  eta?: string;
  ata?: string;
  status: IntlShipmentStatus;
  incoterm?: string;
  currency: string;
  freight_cost?: number;
  insurance_cost?: number;
  total_cbm?: number;
  total_weight_kg?: number;
  forwarder?: string;
  notes?: string;
  created_at: string;
  container_count?: number;
  po_count?: number;
  days_to_eta?: number;
}

export interface ShipmentContainer {
  id: string;
  shipment_id: string;
  shipment_no?: string;
  container_no: string;
  seal_no?: string;
  container_type: ContainerType;
  tare_weight_kg?: number;
  gross_weight_kg?: number;
  cbm?: number;
  contents_summary?: string;
  status: ContainerStatus;
  customs_release_no?: string;
  demurrage_free_days?: number;
  notes?: string;
  created_at: string;
}

export interface POLink {
  id: string;
  shipment_id: string;
  po_id: string;
  po_no?: string;
  supplier_name?: string;
  po_total?: number;
  notes?: string;
  created_at: string;
}

export interface CustomsDocument {
  id: string;
  shipment_id: string;
  doc_type: CustomsDocType;
  doc_no: string;
  doc_date?: string;
  issuer?: string;
  description?: string;
  file_ref?: string;
  status: CustomsDocStatus;
  created_at: string;
}

export interface CustomsClearance {
  id: string;
  shipment_id: string;
  entry_no?: string;
  agent_name?: string;
  submission_date?: string;
  examination_date?: string;
  clearance_date?: string;
  status: ClearanceStatus;
  cif_value_usd?: number;
  import_duty?: number;
  vat?: number;
  idf_fee?: number;
  railway_development_levy?: number;
  other_charges?: number;
  total_taxes_kes?: number;
  kra_pin?: string;
  notes?: string;
  created_at: string;
}

export interface ArrivalNotification {
  id: string;
  shipment_id: string;
  eta_original?: string;
  eta_revised?: string;
  eta_alert_sent: boolean;
  ata?: string;
  port_discharge_date?: string;
  customs_clearance_date?: string;
  delivery_date?: string;
  grn_id?: string;
  notes?: string;
  created_at: string;
}

export interface LocalCostRecord {
  id: string;
  shipment_id: string;
  cost_type: LocalCostType;
  description: string;
  vendor_name?: string;
  amount_kes: number;
  payment_method: LocalPaymentMethod;
  payment_status: LocalCostStatus;
  paid_date?: string;
  mpesa_reference?: string;
  mpesa_phone?: string;
  notes?: string;
  created_at: string;
}

export interface LocalCostSummary {
  shipment_id: string;
  total_kes: number;
  paid_kes: number;
  pending_kes: number;
  by_type: LocalCostRecord[];
}

export interface ShipmentDashboardRow {
  shipment_id: string;
  shipment_no: string;
  mode: ShipmentMode;
  status: IntlShipmentStatus;
  carrier?: string;
  vessel_name?: string;
  bl_number?: string;
  origin_port?: string;
  destination_port: string;
  planned_departure?: string;
  eta?: string;
  eta_revised?: string;
  ata?: string;
  days_to_eta?: number;
  container_count: number;
  po_count: number;
  clearance_status?: ClearanceStatus;
  total_taxes_kes?: number;
  has_overdue_docs: boolean;
}

export const logisticsApi = {
  // Shipments
  async listShipments(params?: { status?: IntlShipmentStatus }): Promise<IntlShipment[]> {
    const res = await apiClient.get<IntlShipment[]>("/api/v1/logistics/shipments/", { params }).then((r) => r.data);
    return res.data;
  },
  async getShipment(id: string): Promise<IntlShipment> {
    const res = await apiClient.get<IntlShipment>(`/api/v1/logistics/shipments/${id}`).then((r) => r.data);
    return res.data;
  },
  async createShipment(data: object): Promise<IntlShipment> {
    const res = await apiClient.post<IntlShipment>("/api/v1/logistics/shipments/", data).then((r) => r.data);
    return res.data;
  },
  async updateShipment(id: string, data: object): Promise<IntlShipment> {
    const res = await apiClient.patch<IntlShipment>(`/api/v1/logistics/shipments/${id}`, data).then((r) => r.data);
    return res.data;
  },

  // Containers
  async listContainers(params?: { shipment_id?: string; status?: ContainerStatus }): Promise<ShipmentContainer[]> {
    const res = await apiClient.get<ShipmentContainer[]>("/api/v1/logistics/containers/", { params }).then((r) => r.data);
    return res.data;
  },
  async createContainer(data: object): Promise<ShipmentContainer> {
    const res = await apiClient.post<ShipmentContainer>("/api/v1/logistics/containers/", data).then((r) => r.data);
    return res.data;
  },
  async updateContainer(id: string, data: object): Promise<ShipmentContainer> {
    const res = await apiClient.patch<ShipmentContainer>(`/api/v1/logistics/containers/${id}`, data).then((r) => r.data);
    return res.data;
  },

  // PO Links
  async listPOLinks(shipmentId: string): Promise<POLink[]> {
    const res = await apiClient.get<POLink[]>(`/api/v1/logistics/shipments/${shipmentId}/po-links`).then((r) => r.data);
    return res.data;
  },
  async addPOLink(shipmentId: string, data: { po_id: string; notes?: string }): Promise<POLink> {
    const res = await apiClient.post<POLink>(`/api/v1/logistics/shipments/${shipmentId}/po-links`, data).then((r) => r.data);
    return res.data;
  },
  async removePOLink(linkId: string): Promise<void> {
    await apiClient.delete(`/api/v1/logistics/po-links/${linkId}`).then((r) => r.data);
  },

  // Customs Documents
  async listDocuments(shipmentId: string): Promise<CustomsDocument[]> {
    const res = await apiClient.get<CustomsDocument[]>(`/api/v1/logistics/shipments/${shipmentId}/documents`).then((r) => r.data);
    return res.data;
  },
  async createDocument(data: object): Promise<CustomsDocument> {
    const res = await apiClient.post<CustomsDocument>("/api/v1/logistics/documents/", data).then((r) => r.data);
    return res.data;
  },
  async updateDocument(id: string, data: object): Promise<CustomsDocument> {
    const res = await apiClient.patch<CustomsDocument>(`/api/v1/logistics/documents/${id}`, data).then((r) => r.data);
    return res.data;
  },

  // Customs Clearance
  async getClearance(shipmentId: string): Promise<CustomsClearance> {
    const res = await apiClient.get<CustomsClearance>(`/api/v1/logistics/shipments/${shipmentId}/clearance`).then((r) => r.data);
    return res.data;
  },
  async createClearance(data: object): Promise<CustomsClearance> {
    const res = await apiClient.post<CustomsClearance>("/api/v1/logistics/clearance/", data).then((r) => r.data);
    return res.data;
  },
  async updateClearance(id: string, data: object): Promise<CustomsClearance> {
    const res = await apiClient.patch<CustomsClearance>(`/api/v1/logistics/clearance/${id}`, data).then((r) => r.data);
    return res.data;
  },

  // Arrivals
  async listArrivals(): Promise<ArrivalNotification[]> {
    const res = await apiClient.get<ArrivalNotification[]>("/api/v1/logistics/arrivals/").then((r) => r.data);
    return res.data;
  },
  async getEtaAlerts(daysAhead = 14): Promise<IntlShipment[]> {
    const res = await apiClient.get<IntlShipment[]>("/api/v1/logistics/arrivals/alerts", { params: { days_ahead: daysAhead } }).then((r) => r.data);
    return res.data;
  },
  async getArrival(shipmentId: string): Promise<ArrivalNotification> {
    const res = await apiClient.get<ArrivalNotification>(`/api/v1/logistics/shipments/${shipmentId}/arrival`).then((r) => r.data);
    return res.data;
  },
  async updateArrival(shipmentId: string, data: object): Promise<ArrivalNotification> {
    const res = await apiClient.patch<ArrivalNotification>(`/api/v1/logistics/shipments/${shipmentId}/arrival`, data).then((r) => r.data);
    return res.data;
  },

  // Dashboard
  async getDashboard(): Promise<ShipmentDashboardRow[]> {
    const res = await apiClient.get<ShipmentDashboardRow[]>("/api/v1/logistics/dashboard/").then((r) => r.data);
    return res.data;
  },

  // Local Logistics Costs
  async listLocalCosts(shipmentId: string): Promise<LocalCostSummary> {
    const res = await apiClient.get<LocalCostSummary>(`/api/v1/logistics/shipments/${shipmentId}/local-costs`).then((r) => r.data);
    return res.data;
  },
  async createLocalCost(shipmentId: string, data: object): Promise<LocalCostRecord> {
    const res = await apiClient.post<LocalCostRecord>(`/api/v1/logistics/shipments/${shipmentId}/local-costs`, data).then((r) => r.data);
    return res.data;
  },
  async updateLocalCost(costId: string, data: object): Promise<LocalCostRecord> {
    const res = await apiClient.patch<LocalCostRecord>(`/api/v1/logistics/local-costs/${costId}`, data).then((r) => r.data);
    return res.data;
  },
  async deleteLocalCost(costId: string): Promise<void> {
    await apiClient.delete(`/api/v1/logistics/local-costs/${costId}`).then((r) => r.data);
  },
};
