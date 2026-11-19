// M37: the service worker must never intercept API, non-GET or cross-origin requests,
// must not cache navigations (authenticated HTML), and only caches hashed build assets.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("../../public/sw.js", import.meta.url), "utf8");

function loadWorker({ networkFails = false } = {}) {
  const listeners = {};
  const stored = [];
  const cache = { addAll: async () => {}, put: async (req) => stored.push(new URL(req.url).pathname) };
  const ctx = {
    URL,
    Promise,
    self: { location: { origin: "https://erp.example.test" }, addEventListener: (t, fn) => { listeners[t] = fn; }, skipWaiting() {}, clients: { claim() {} } },
    caches: { open: async () => cache, match: async (req) => (typeof req === "string" ? `cached:${req}` : undefined), keys: async () => [], delete: async () => true },
    fetch: async () => {
      if (networkFails) throw new Error("offline");
      return { ok: true, clone() { return this; } };
    },
  };
  vm.runInNewContext(source, ctx);
  const dispatch = (url, { method = "GET", mode = "cors" } = {}) => {
    let responded = null;
    listeners.fetch({ request: { url, method, mode }, respondWith: (p) => { responded = p; } });
    return responded;
  };
  return { dispatch, stored };
}

test("ignores non-GET, cross-origin API and unlisted same-origin requests", () => {
  const { dispatch } = loadWorker();
  assert.equal(dispatch("https://erp.example.test/_next/static/a.js", { method: "POST" }), null);
  assert.equal(dispatch("https://api.example.test/api/v1/auth/me"), null);
  assert.equal(dispatch("https://erp.example.test/api/v1/mobile/kpis"), null);
  assert.equal(dispatch("https://erp.example.test/manifest.webmanifest"), null);
});

test("navigation is network-only and never stored", async () => {
  const { dispatch, stored } = loadWorker();
  const res = await dispatch("https://erp.example.test/dashboard", { mode: "navigate" });
  assert.equal(res.ok, true);
  assert.deepEqual(stored, []);
});

test("navigation falls back to the static offline page when the network fails", async () => {
  const { dispatch } = loadWorker({ networkFails: true });
  assert.equal(await dispatch("https://erp.example.test/dashboard", { mode: "navigate" }), "cached:/offline.html");
});

test("hashed build assets are cached", async () => {
  const { dispatch, stored } = loadWorker();
  await dispatch("https://erp.example.test/_next/static/chunks/app.js");
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(stored, ["/_next/static/chunks/app.js"]);
});
