// Web Push for the installed app (M37.S03.T001): subscribe this browser with the server's VAPID key.
import { apiClient } from "@/lib/api";

const toBytes = (b64: string) => {
  const s = atob((b64 + "=".repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(s, (c) => c.charCodeAt(0));
};

export const pushSupported = () =>
  typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

export async function pushState(): Promise<"unsupported" | "denied" | "on" | "off"> {
  if (!pushSupported()) return "unsupported";
  if (Notification.permission === "denied") return "denied";
  const reg = await navigator.serviceWorker.getRegistration();
  return (await reg?.pushManager.getSubscription()) ? "on" : "off";
}

export async function enablePush(): Promise<void> {
  if ((await Notification.requestPermission()) !== "granted") throw new Error("Notifications are blocked for this site.");
  const reg = await navigator.serviceWorker.ready;
  const { public_key } = (await apiClient.get<{ public_key: string }>("/api/v1/mobile/push/public-key")).data;
  const sub = (await reg.pushManager.getSubscription())
    ?? (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: toBytes(public_key) }));
  await apiClient.post("/api/v1/mobile/push/subscribe", sub.toJSON());
}

export async function disablePush(): Promise<void> {
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  if (!sub) return;
  await apiClient.post("/api/v1/mobile/push/unsubscribe", sub.toJSON()).catch(() => undefined);
  await sub.unsubscribe();
}
