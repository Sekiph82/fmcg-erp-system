"use client";

import { useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { mobileApi, type MobilePlatform } from "@/lib/mobile_api";

function detectPlatform(): MobilePlatform {
  const ua = navigator.userAgent;
  if (/android/i.test(ua)) return "android";
  // iPadOS reports a Macintosh UA; touch points tell it apart
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return "ios";
  return "web";
}

function deviceId(): string {
  let id = localStorage.getItem("povu-device-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("povu-device-id", id);
  }
  return id;
}

/** Registers the service worker and, when running as the installed app, the device (M37). */
export function PwaRegister() {
  const { user } = useAuth();

  useEffect(() => {
    // dev chunks are not content-hashed; a cache-first SW would serve stale code
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch((err) => console.warn("[PWA] SW registration failed", err));
  }, []);

  useEffect(() => {
    if (!user || !window.matchMedia("(display-mode: standalone)").matches) return;
    const key = `povu-device-registered-${user.id}`;
    try {
      if (sessionStorage.getItem(key)) return;
      const platform = detectPlatform();
      // ponytail: token empty until FCM/APNs/Web Push is wired (M37.S03); row still gives admins a device inventory
      mobileApi.registerDevice({
        device_id: deviceId(),
        platform,
        token: "",
        device_name: `POVU app (${platform})`,
        app_version: "pwa-1",
        os_version: navigator.userAgent.slice(0, 100),
      }).then(() => sessionStorage.setItem(key, "1")).catch(() => undefined);
    } catch {
      // storage blocked (private mode) — skip registration
    }
  }, [user]);

  return null;
}
