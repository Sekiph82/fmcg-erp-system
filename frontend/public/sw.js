/* POVU ERP service worker (M37).
 * Security rule: never cache API responses, authenticated HTML or any non-GET request.
 * Only same-origin, content-hashed build assets and icons are cached; navigations are
 * network-only with a static offline page. ERP writes are never queued offline. */
const VERSION = "povu-pwa-v2";   // v2: POVU Brand Vault icons (old caches are evicted on activate)
const OFFLINE_URL = "/offline.html";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll([OFFLINE_URL])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

function isCacheableAsset(url) {
  return url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/");
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // API (separate origin) is never touched

  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }
  if (isCacheableAsset(url)) {
    event.respondWith(
      caches.match(request).then((hit) => hit || fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(VERSION).then((cache) => cache.put(request, copy));
        }
        return response;
      })),
    );
  }
});


// Web Push (M37.S03.T001): show the message; a tap opens (or focuses) the app at its link.
self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = { title: "POVU ERP", body: event.data ? event.data.text() : "" }; }
  event.waitUntil(self.registration.showNotification(data.title || "POVU ERP", {
    body: data.body || "", tag: data.tag || undefined, icon: "/icons/povu-icon-192.png", badge: "/icons/povu-icon-192.png",
    data: { url: data.url || "/dashboard" },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = new URL((event.notification.data && event.notification.data.url) || "/dashboard", self.location.origin);
  if (url.origin !== self.location.origin) return; // never open other sites from a push
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
    for (const w of wins) { if ("focus" in w) { w.navigate(url.href); return w.focus(); } }
    return self.clients.openWindow(url.href);
  }));
});
