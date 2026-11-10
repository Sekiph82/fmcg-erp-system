"use client";

import { useEffect, useState } from "react";

export type ShopFloorConnectionState = "online" | "offline" | "reconnected";

export function useShopFloorConnectionState(): {
  state: ShopFloorConnectionState;
  acknowledgeRefresh: () => void;
} {
  const [state, setState] = useState<ShopFloorConnectionState>("online");

  useEffect(() => {
    const markOffline = () => setState("offline");
    const markOnline = () => setState((current) => current === "offline" ? "reconnected" : current);
    setState(window.navigator.onLine ? "online" : "offline");
    window.addEventListener("offline", markOffline);
    window.addEventListener("online", markOnline);
    return () => {
      window.removeEventListener("offline", markOffline);
      window.removeEventListener("online", markOnline);
    };
  }, []);

  return {
    state,
    acknowledgeRefresh: () => setState("online"),
  };
}

export function ShopFloorConnectionNotice({
  state,
  onRefresh,
  refreshing = false,
  forceRefresh = false,
}: {
  state: ShopFloorConnectionState;
  onRefresh: () => void;
  refreshing?: boolean;
  forceRefresh?: boolean;
}) {
  if (state === "online" && !forceRefresh) return null;

  const offline = state === "offline";
  return (
    <div
      role={offline ? "alert" : "status"}
      aria-live={offline ? "assertive" : "polite"}
      className={`rounded-lg border px-3 py-2 text-sm ${offline ? "border-amber-300 bg-amber-50 text-amber-950" : "border-blue-200 bg-blue-50 text-blue-950"}`}
    >
      <p>
        {offline
          ? "This device reports no network connection. Shop Floor changes are not saved offline. Reconnect before continuing."
          : forceRefresh
            ? "The previous action is not confirmed. Refresh Shop Floor state and revalidate your sign-in and permissions before continuing."
            : "Connection restored. Refresh the latest Shop Floor state and revalidate your sign-in and permissions before continuing."}
      </p>
      {!offline && (
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="mt-2 min-h-11 rounded-md border border-blue-500 px-3 font-semibold disabled:opacity-50"
        >
          {refreshing ? "Refreshing Shop Floor state…" : "Refresh Shop Floor state"}
        </button>
      )}
    </div>
  );
}
