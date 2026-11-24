// M42 employee digital business cards: HR management, the employee's own card, and the public card.
import { apiClient, API_ORIGIN } from "./api";

export interface CardRow {
  employee_id: string;
  employee_code: string | null;
  name: string;
  role: string;
  department: string;
  employee_status: string;
  card_id: string;
  slug: string;
  status: "PUBLISHED" | "REVOKED";
  live: boolean;
  url: string;
  show_phone: boolean;
  show_whatsapp: boolean;
  show_email: boolean;
  title_en: string | null;
  has_photo: boolean;
  photo_consent_at: string | null;
  revoked_reason: string | null;
  phone: string | null;
  email: string | null;
  assets_base: string;
  photo?: string | null;
  public?: PublicCard;
}

export interface PublicCard {
  slug: string;
  name: string;
  title: string;
  company: string;
  website: string;
  phone: string | null;
  whatsapp: string | null;
  email: string | null;
  has_photo: boolean;
  assets_base: string;
  url: string;
}

export interface CardFilter { department?: string; status?: string; search?: string }

const H = "/api/v1/hr";
const blobUrl = async (url: string, params?: object) =>
  URL.createObjectURL((await apiClient.get(url, { params, responseType: "blob" })).data as Blob);

export const cardsApi = {
  list: (f: CardFilter) => apiClient.get<CardRow[]>(`${H}/cards`, { params: f }).then((r) => r.data),
  get: (employeeId: string) => apiClient.get<CardRow>(`${H}/employees/${employeeId}/card`).then((r) => r.data),
  update: (employeeId: string, body: Partial<Pick<CardRow, "show_phone" | "show_whatsapp" | "show_email" | "title_en">>) =>
    apiClient.patch<CardRow>(`${H}/employees/${employeeId}/card`, body).then((r) => r.data),
  uploadPhoto: (employeeId: string, file: File, consent: boolean) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("consent", consent ? "true" : "false");
    return apiClient.post<CardRow>(`${H}/employees/${employeeId}/card/photo`, fd).then((r) => r.data);
  },
  removePhoto: (employeeId: string) => apiClient.delete<CardRow>(`${H}/employees/${employeeId}/card/photo`).then((r) => r.data),
  revoke: (employeeId: string, reason?: string) =>
    apiClient.post<CardRow>(`${H}/employees/${employeeId}/card/revoke`, { reason }).then((r) => r.data),
  republish: (employeeId: string) => apiClient.post<CardRow>(`${H}/employees/${employeeId}/card/republish`).then((r) => r.data),
  /** object URL of the QR image (login needed, so fetched as a blob) */
  qr: (employeeId: string, fmt: "svg" | "png" = "svg") => blobUrl(`${H}/employees/${employeeId}/card/qr.${fmt}`),
  qrZip: (f: CardFilter) => blobUrl(`${H}/cards/qr.zip`, f),
  mine: () => apiClient.get<CardRow>(`${H}/my-card`).then((r) => r.data),
  myQr: (fmt: "svg" | "png" = "svg") => blobUrl(`${H}/my-card/qr.${fmt}`),
};

/** path of the public card inside this app (QR codes carry the absolute PUBLIC_APP_URL form) */
export const cardPath = (slug: string) => `/kartvizit/${slug}`;
export const publicCardApi = `${API_ORIGIN}/api/v1/public/cards`;

export function download(url: string, filename: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
}
