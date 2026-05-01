import axios from "axios";

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

/**
 * Convert an axios error to a user-friendly message.
 * Use in React Query onError callbacks or catch blocks.
 */
export function parseApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status ?? 0;
    const data = err.response?.data;
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : typeof data === "string"
          ? data
          : undefined;

    if (status === 401) return { status, message: "Session expired. Please log in again.", detail };
    if (status === 403) return { status, message: "You don't have permission to perform this action.", detail };
    if (status === 404) return { status, message: "Record not found.", detail };
    if (status === 409) return { status, message: "Conflict — record may already exist.", detail };
    if (status === 422) return { status, message: "Validation error. Check your input.", detail };
    if (status === 429) return { status, message: "Too many requests. Please slow down.", detail };
    if (status >= 500) return { status, message: "Server error. Please try again shortly.", detail };
    return { status, message: detail ?? "An unexpected error occurred.", detail };
  }
  if (err instanceof Error) return { status: 0, message: err.message };
  return { status: 0, message: "Network error. Check your connection." };
}

/** Convenience: extract just the message string. */
export function errorMessage(err: unknown): string {
  return parseApiError(err).message;
}
