import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";

type RouterLike = { push: (path: string) => void };
let _router: RouterLike | null = null;
type RetryableConfig = InternalAxiosRequestConfig & { _authRefreshAttempted?: boolean };

/** Backend origin; API paths are `/api/v1/...` below it. */
export const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const refreshClient = axios.create({
  baseURL: API_ORIGIN,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});
let refreshInFlight: Promise<void> | null = null;

export function setAppRouter(router: RouterLike): void {
  _router = router;
}

export const apiClient = axios.create({
  baseURL: API_ORIGIN,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

/** Same session handling as apiClient, with `/api/v1` as the base path. */
export const apiV1Client = axios.create({
  baseURL: `${API_ORIGIN}/api/v1`,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// Credential-checking endpoints: a 401 there means "wrong credentials", not "session expired".
const AUTH_ENDPOINT = /\/api\/v1\/(?:auth\/(?:login|refresh|2fa\/(?:login-verify|use-recovery-code|resend-otp|required-setup(?:\/verify)?))|ess\/login|portal\/auth\/(?:login|activate)|supplier-portal\/auth\/login)(?:[/?]|$)/;

function refreshSession(): Promise<void> {
  if (!refreshInFlight) {
    refreshInFlight = refreshClient
      .post("/api/v1/auth/refresh")
      .then(() => undefined)
      .finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

function redirectToLogin(): void {
  // public pages (website lead forms) have no session to expire
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/forms/")) return;
  if (_router) {
    _router.push("/login");
  } else if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

/**
 * fetch() for backend calls: resolves `/api/...` paths against the API origin, always sends the
 * session cookie, and retries once after a session refresh on 401.
 */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const url = input.startsWith("/") ? `${API_ORIGIN}${input}` : input;
  const options: RequestInit = { ...init, credentials: "include" };
  const res = await fetch(url, options);
  if (res.status !== 401 || AUTH_ENDPOINT.test(url)) return res;
  try {
    await refreshSession();
  } catch {
    redirectToLogin();
    return res;
  }
  return fetch(url, options);
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  return config;
});

const handleResponseError = async (error: AxiosError) => {
    if (error.response?.status === 401) {
      const original = error.config as RetryableConfig | undefined;
      const requestPath = original?.url ?? "";
      const isLoginOrRefreshRequest = AUTH_ENDPOINT.test(`${original?.baseURL ?? ""}${requestPath}`);

      if (original && !original._authRefreshAttempted && !isLoginOrRefreshRequest) {
        original._authRefreshAttempted = true;
        try {
          await refreshSession();
          return apiClient(original);
        } catch {
          // Continue to the existing signed-out behavior below.
        }
      }

      if (isLoginOrRefreshRequest) return Promise.reject(error);
      redirectToLogin();
    }
    return Promise.reject(error);
};

apiClient.interceptors.response.use((res: AxiosResponse) => res, handleResponseError);
apiV1Client.interceptors.response.use((res: AxiosResponse) => res, handleResponseError);
