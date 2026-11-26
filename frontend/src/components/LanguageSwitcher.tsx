"use client";
// M46.S01.T007 language switcher for customer screens (choice is remembered on this device).
import { useEffect } from "react";
import { LOCALES, LOCALE_NAME, useI18n, type Locale } from "@/lib/i18n";

export default function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { locale, setLocale, t } = useI18n();
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);
  return (
    <label className={`inline-flex items-center gap-1 text-xs ${className}`}>
      <span className="sr-only">{t("common.language")}</span>
      <select aria-label={t("common.language")} className="border rounded px-1 py-0.5 bg-white text-gray-900" value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}>
        {LOCALES.map((l) => <option key={l} value={l} lang={l}>{LOCALE_NAME[l]}</option>)}
      </select>
    </label>
  );
}
