import { apiClient } from "./api";

export type TripStatus = "PLANNED" | "LOADING" | "IN_TRANSIT" | "COMPLETED" | "CANCELLED";
export type TripOrderStatus = "PENDING" | "DELIVERED" | "PARTIAL" | "FAILED" | "RESCHEDULED";

export interface TripOrder {
  id: string;
  shipment_id: string;
  shipment_no?: string;
  customer_name?: string;
  delivery_sequence: number;
  status: TripOrderStatus;
  failure_reason?: string;
  notes?: string;
}

export interface DeliveryTrip {
  id: string;
  trip_no: string;
  trip_date: string;
  vehicle_plate?: string;
  vehicle_type?: string;
  driver_name?: string;
  driver_phone?: string;
  warehouse_id?: string;
  rep_id?: string;
  rep_name?: string;
  status: TripStatus;
  capacity_kg?: number;
  route_notes?: string;
  departed_at?: string;
  returned_at?: string;
  created_at: string;
  order_count: number;
  orders: TripOrder[];
}

export interface ProofOfDelivery {
  id: string;
  shipment_id: string;
  trip_order_id?: string;
  received_by?: string;
  signature_text?: string;
  photo_url?: string;
  delivered_at?: string;
  gps_lat?: number;
  gps_lng?: number;
  notes?: string;
  confirmed_by_id?: string;
  created_at: string;
}

export const deliveryApi = {
  listTrips: (params?: { status?: TripStatus }) =>
    apiClient.get<DeliveryTrip[]>("/api/v1/delivery/trips", { params }).then((r) => r.data),
  createTrip: (data: Partial<DeliveryTrip> & { orders?: Partial<TripOrder>[] }) =>
    apiClient.post<DeliveryTrip>("/api/v1/delivery/trips", data).then((r) => r.data),
  getTrip: (id: string) =>
    apiClient.get<DeliveryTrip>(`/api/v1/delivery/trips/${id}`).then((r) => r.data),
  updateTrip: (id: string, data: Partial<DeliveryTrip>) =>
    apiClient.patch<DeliveryTrip>(`/api/v1/delivery/trips/${id}`, data).then((r) => r.data),

  listPods: () =>
    apiClient.get<ProofOfDelivery[]>("/api/v1/delivery/pod").then((r) => r.data),
  createPod: (data: Partial<ProofOfDelivery>) =>
    apiClient.post<ProofOfDelivery>("/api/v1/delivery/pod", data).then((r) => r.data),
  getPodByShipment: (shipmentId: string) =>
    apiClient.get<ProofOfDelivery>(`/api/v1/delivery/pod/shipment/${shipmentId}`).then((r) => r.data),
};
