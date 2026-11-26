// M46.S01.T007 UI internationalization (EN / SW / TR), customer-facing screens first.
//
// - Catalogs live in ./messages/<area>.json as {"en": {...}, "sw": {...}, "tr": {...}}; English is the source.
//   `node scripts/i18n-report.mjs` lists keys missing in sw/tr and t("…") keys used in code but absent from en.
// - Locale negotiation: explicit choice (localStorage "povu.lang", set by the switcher) → ?lang= → the browser's
//   languages → English. One shared store, so every screen and the switcher change together.
// - Numbers, money and dates use Intl with the locale's region (en-KE, sw-KE, tr-TR).
// - Server errors are shown from their HTTP status code (error.<status>), not the English server text.
// - Missing keys fall back to English and are collected in window.__i18nMissing for the report screen/tests.
import common from "./messages/common.json";
import docs from "./messages/docs.json";
import portal from "./messages/portal.json";
import publicPages from "./messages/public.json";
import staff from "./messages/staff.json";
import staffUi from "./messages/staff_ui.json";
import backendMessages from "./messages/backend_messages.json";

export const LOCALES = ["en", "sw", "tr"] as const;
export type Locale = (typeof LOCALES)[number];
export const LOCALE_NAME: Record<Locale, string> = { en: "English", sw: "Kiswahili", tr: "Türkçe" };
const TAG: Record<Locale, string> = { en: "en-KE", sw: "sw-KE", tr: "tr-TR" };
const KEY = "povu.lang";

type Catalog = Record<Locale, Record<string, string>>;
const CATALOGS: Catalog[] = [common as Catalog, docs as Catalog, portal as Catalog, publicPages as Catalog, staff as Catalog];
export const MESSAGES: Catalog = LOCALES.reduce((acc, l) => {
  acc[l] = Object.assign({}, ...CATALOGS.map((c) => c[l] ?? {}));
  return acc;
}, {} as Catalog);

const isLocale = (v: unknown): v is Locale => typeof v === "string" && (LOCALES as readonly string[]).includes(v);

export function negotiate(): Locale {
  if (typeof window === "undefined") return "en";
  try {
    const saved = localStorage.getItem(KEY);
    if (isLocale(saved)) return saved;
  } catch { /* storage blocked */ }
  const q = new URLSearchParams(window.location.search).get("lang");
  if (isLocale(q)) return q;
  for (const l of navigator.languages ?? [navigator.language]) {
    const base = (l || "").slice(0, 2).toLowerCase();
    if (isLocale(base)) return base;
  }
  return "en";
}

let current: Locale | null = null;
const listeners = new Set<() => void>();
export function getLocale(): Locale {
  if (current === null) current = negotiate();
  return current;
}
export function setLocale(l: Locale) {
  current = l;
  try { localStorage.setItem(KEY, l); } catch { /* ignore */ }
  if (typeof document !== "undefined") document.documentElement.lang = l;
  listeners.forEach((f) => f());
}
export function subscribe(f: () => void) { listeners.add(f); return () => { listeners.delete(f); }; }

function missing(key: string, locale: Locale) {
  if (typeof window === "undefined") return;
  const w = window as unknown as { __i18nMissing?: Record<string, string[]> };
  w.__i18nMissing ??= {};
  const list = (w.__i18nMissing[locale] ??= []);
  if (!list.includes(key)) list.push(key);
}

export function translate(locale: Locale, key: string, vars?: Record<string, string | number>): string {
  let s = MESSAGES[locale][key];
  if (s === undefined) {
    missing(key, locale);
    s = MESSAGES.en[key] ?? key;
  }
  return vars ? s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)) : s;
}

export function formatters(locale: Locale) {
  const tag = TAG[locale];
  return {
    money: (v: number | string | null | undefined, currency = "KES") =>
      v === null || v === undefined || v === "" ? "—" : new Intl.NumberFormat(tag, { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(v)),
    number: (v: number | string | null | undefined, digits = 0) =>
      v === null || v === undefined || v === "" ? "—" : new Intl.NumberFormat(tag, { maximumFractionDigits: digits }).format(Number(v)),
    date: (v: string | Date | null | undefined) => (v ? new Intl.DateTimeFormat(tag, { dateStyle: "medium" }).format(new Date(v)) : "—"),
    dateTime: (v: string | Date | null | undefined) => (v ? new Intl.DateTimeFormat(tag, { dateStyle: "medium", timeStyle: "short" }).format(new Date(v)) : "—"),
    day: (v: string | Date) => new Intl.DateTimeFormat(tag, { weekday: "short", day: "numeric", month: "short" }).format(new Date(v)),
    time: (v: string | Date) => new Intl.DateTimeFormat(tag, { timeStyle: "short" }).format(new Date(v)),
  };
}

/** Translate a failed request by its status code (server text is English and not shown to customers). */
export function errorText(locale: Locale, status?: number): string {
  const k = `error.${status ?? 0}`;
  return MESSAGES.en[k] ? translate(locale, k) : translate(locale, "error.generic");
}

// M51.S01.T008 staff UI: catalogs keyed by the ENGLISH source string, used by tx().
// staff_ui.json is generated by scripts/i18n-codemod.mjs; backend_messages.json maps common API error texts.
const TX_CATALOGS: Catalog[] = [staffUi as Catalog, backendMessages as Catalog];
export const TX_MESSAGES: Catalog = LOCALES.reduce((acc, l) => {
  acc[l] = Object.assign({}, ...TX_CATALOGS.map((c) => c[l] ?? {}));
  return acc;
}, {} as Catalog);

// tx() stays English until the shell has hydrated, so server HTML and the first client render agree.
let txLive = false;
export function enableTx() { txLive = true; }

/** Translate a literal English UI string. Only ever pass source literals here, never user or API data. */
export function tx(english: string, vars?: Record<string, unknown>): string {
  let s = english;
  if (txLive) {
    const locale = getLocale();
    if (locale !== "en") {
      const hit = TX_MESSAGES[locale][english];
      if (hit && hit.trim()) s = hit;
      else missing(english, locale);
    }
  }
  return vars ? s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k] ?? "") : m)) : s;
}

/**
 * Lazy module-level constant (tab arrays, option lists): `const TABS = lx(() => [{ label: tx("Overview") }])`.
 * A Proxy over the value built for the current locale (cached per locale), so tx() runs at use time, not at import time.
 */
export function lx<T extends object>(build: () => T): T {
  const cache: Record<string, T> = {};
  const cur = (): T => (cache[txLive ? getLocale() : "en"] ??= build());
  const target = (Array.isArray(cur()) ? [] : {}) as T;
  return new Proxy(target, {
    get: (_, k) => Reflect.get(cur(), k),
    set: (_, k, v) => Reflect.set(cur(), k, v),
    has: (_, k) => Reflect.has(cur(), k),
    ownKeys: () => Reflect.ownKeys(cur()),
    getOwnPropertyDescriptor: (_, k) => {
      const d = Reflect.getOwnPropertyDescriptor(cur(), k);
      if (d && k !== "length") d.configurable = true;
      return d;
    },
    getPrototypeOf: () => Reflect.getPrototypeOf(cur()),
  });
}

/** API system message -> locale. Exact match in backend_messages.json only; anything else, including user data, is returned unchanged. */
export function txApi(message: string): string {
  const api = backendMessages as Catalog;           // ONLY the API-message catalog: never the staff UI strings (a user's own text could match one)
  if (!txLive || !Object.hasOwn(api.en, message)) return message;
  const hit = api[getLocale()]?.[message];
  return hit && hit.trim() ? hit : message;
}
