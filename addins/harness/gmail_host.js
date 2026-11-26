#!/usr/bin/env node
// Local Gmail host harness (M50.S01.T011): runs the add-on's Code.gs in a sandbox with the Apps Script services it uses
// (CardService, PropertiesService, UrlFetchApp, GmailApp, Utilities) and drives it with a scenario. UrlFetchApp performs REAL
// synchronous HTTP requests (loopback only) against a running ERP, so the same code path as in Gmail is exercised.
//   node gmail_host.js <Code.gs> <scenario.json>   ->  JSON on stdout: {results, requests, properties}
"use strict";
const fs = require("fs"), vm = require("vm"), crypto = require("crypto"), cp = require("child_process"), path = require("path");

if (process.argv[2] === "--fetch") {            // child: one HTTP request, answer as JSON on stdout
  let raw = ""; process.stdin.on("data", (d) => (raw += d)).on("end", async () => {
    const r = JSON.parse(raw);
    try {
      const res = await fetch(r.url, { method: r.method, headers: r.headers, body: r.body });
      process.stdout.write(JSON.stringify({ code: res.status, text: await res.text() }));
    } catch (e) { process.stdout.write(JSON.stringify({ code: 0, text: String(e) })); }
  });
  return;
}

const [codePath, scenarioPath] = process.argv.slice(2);
const scenario = JSON.parse(fs.readFileSync(scenarioPath, "utf8"));
const requests = [], props = {};
const origin = (u) => new URL(u).origin;

function node(type) {                           // a recording CardService builder node
  const n = { type, calls: [], children: [] };
  return new Proxy(n, {
    get(t, name) {
      if (name === "toJSON") return () => t;
      if (name === "build") return () => ({ ...t, built: true });
      if (name === "then") return undefined;
      return (...args) => {
        t.calls.push([String(name), args.map((a) => (a && a.type ? "[node " + a.type + "]" : a))]);
        args.forEach((a) => { if (a && a.type) t.children.push(a); });
        return new Proxy(t, this);
      };
    },
  });
}
const CardService = new Proxy({ SelectionInputType: { DROPDOWN: "DROPDOWN" } }, {
  get(t, name) { if (name in t) return t[name]; return () => node(String(name).replace(/^new/, "")); },
});
const Utilities = {
  DigestAlgorithm: { SHA_256: "sha256" },
  getUuid: () => crypto.randomUUID(),
  computeDigest: (alg, s) => Array.from(crypto.createHash(alg).update(String(s)).digest()).map((b) => (b > 127 ? b - 256 : b)),
  sleep: () => {},
  base64EncodeWebSafe: (bytes) => Buffer.from(bytes.map((b) => (b < 0 ? b + 256 : b))).toString("base64").replace(/\+/g, "-").replace(/\//g, "_"),
};
const LockService = { getUserLock: () => ({ waitLock() {}, releaseLock() {} }) };
const store = {};
const PropertiesService = { getUserProperties: () => ({
  getProperty: (k) => (k in store ? store[k] : null), setProperty: (k, v) => { store[k] = String(v); }, deleteProperty: (k) => { delete store[k]; } }) };
const UrlFetchApp = { fetch(url, opts) {
  if (!/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//.test(url)) throw new Error("harness: loopback only: " + url);
  const entry = { method: (opts.method || "get").toUpperCase(), url, headers: opts.headers || {}, body: opts.payload };
  if (opts.contentType && entry.body) entry.headers = { ...entry.headers, "Content-Type": opts.contentType };
  const out = cp.spawnSync(process.execPath, [__filename, "--fetch"], { input: JSON.stringify(entry), encoding: "utf8" });
  const res = JSON.parse(out.stdout);
  requests.push({ ...entry, status: res.code });
  return { getResponseCode: () => res.code, getContentText: () => res.text };
} };
const drafts = [];
const GmailApp = { setCurrentMessageAccessToken() {}, getMessageById(id) {
  const m = scenario.messages[id];
  return { getFrom: () => m.from, getSubject: () => m.subject, getPlainBody: () => m.body, getHeader: () => m.messageIdHeader,
    getThread: () => ({ getId: () => m.threadId }), createDraftReply: (body) => { const d = { body, to: m.from }; drafts.push(d); return d; } };
} };
const ctx = vm.createContext({ CardService, LockService, Utilities, PropertiesService, UrlFetchApp, GmailApp, Date, JSON, encodeURIComponent, Error, console });
vm.runInContext(fs.readFileSync(codePath, "utf8"), ctx, { filename: "Code.gs" });

function getSync(url) {                          // loopback GET used only to stand in for the user pressing Allow on the consent page
  const out = cp.spawnSync(process.execPath, [__filename, "--fetch"], { input: JSON.stringify({ url, method: "GET", headers: {} }), encoding: "utf8" });
  return JSON.parse(JSON.parse(out.stdout).text);
}
const results = [];
let lastOpenLink = null;
for (const step of scenario.steps) {
  try {
    const e = { gmail: step.gmail, formInput: { ...(step.formInput || {}) }, parameters: step.parameters || {} };
    if (step.expire) { const s = JSON.parse(store.POVU_SESSION); s.exp = 0; store.POVU_SESSION = JSON.stringify(s); }
    if (step.consent) {                            // the page the user opens from the card, approved with a signed-in ERP session
      const challenge = new URL(lastOpenLink).searchParams.get("challenge");
      e.formInput.code = getSync(step.consent + "/_consent?challenge=" + encodeURIComponent(challenge)).code;
    }
    const r = vm.runInContext(step.call, ctx)(e);
    const plain = JSON.parse(JSON.stringify(r || null));
    const m = JSON.stringify(plain).match(/https?:[^"\\]*\/addin\/authorize[^"\\]*/);
    if (m) lastOpenLink = m[0];
    results.push({ call: step.call, ok: true, result: plain });
  } catch (err) { results.push({ call: step.call, ok: false, error: String(err.message || err) }); }
}
process.stdout.write(JSON.stringify({ results, requests, properties: store, drafts }));
