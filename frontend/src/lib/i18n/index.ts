"use client";
// M46.S01.T007 / M51.S01.T008 UI internationalization (EN / SW / TR). The runtime lives in ./core (no client directive,
// so server files can import `tx` from "@/lib/i18n/core"); this module adds the React hook.
//
// - Catalogs live in ./messages/<area>.json as {"en": {...}, "sw": {...}, "tr": {...}}; English is the source.
//   t("key") uses dotted keys; tx("English text") uses staff_ui.json / backend_messages.json keyed by the English text.
//   `node scripts/i18n-report.mjs` lists keys missing in sw/tr and t("…") keys used in code but absent from en.
// - Locale negotiation: explicit choice (localStorage "povu.lang") → ?lang= → browser languages → English.
// - Numbers, money and dates use Intl with the locale's region (en-KE, sw-KE, tr-TR).
// - Server errors are shown from their HTTP status code (error.<status>), not the English server text.
// - Missing keys fall back to English and are collected in window.__i18nMissing.
import { useSyncExternalStore } from "react";
import { LOCALES, LOCALE_NAME, MESSAGES, TX_MESSAGES, negotiate, setLocale, translate, tx, txApi, lx, enableTx, formatters, errorText, getLocale, subscribe } from "./core";
import type { Locale } from "./core";

export { LOCALES, LOCALE_NAME, MESSAGES, TX_MESSAGES, negotiate, setLocale, translate, tx, txApi, lx, enableTx, formatters, errorText };
export type { Locale };

export function useI18n() {
  const locale = useSyncExternalStore(subscribe, getLocale, () => "en" as Locale);
  return {
    locale,
    setLocale,
    t: (key: string, vars?: Record<string, string | number>) => translate(locale, key, vars),
    f: formatters(locale),
    err: (status?: number) => errorText(locale, status),
  };
}
