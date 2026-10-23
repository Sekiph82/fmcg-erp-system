import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";

type RouterLike = { push: (path: string) => void };
let _router: RouterLike | null = null;
type RetryableConfig = InternalAxiosRequestConfig & { _authRefreshAttempted?: boolean };

const refreshClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});
let refreshInFlight: Promise<void> | null = null;

export function setAppRouter(router: RouterLike): void {
  _router = router;
}

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  return config;
});

apiClient.interceptors.response.use(
  (res: AxiosResponse) => res,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      const original = error.config as RetryableConfig | undefined;
      const requestPath = original?.url ?? "";
      const isLoginOrRefreshRequest = /\/api\/v1\/auth\/(?:login|refresh|2fa\/(?:login-verify|use-recovery-code|resend-otp))(?:[/?]|$)/.test(requestPath);

      if (original && !original._authRefreshAttempted && !isLoginOrRefreshRequest) {
        original._authRefreshAttempted = true;
        try {
          if (!refreshInFlight) {
            refreshInFlight = refreshClient
              .post("/api/v1/auth/refresh")
              .then(() => undefined)
              .finally(() => { refreshInFlight = null; });
          }
          await refreshInFlight;
          return apiClient(original);
        } catch {
          // Continue to the existing signed-out behavior below.
        }
      }

      if (isLoginOrRefreshRequest) return Promise.reject(error);
      if (_router) {
        _router.push("/login");
      } else if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
