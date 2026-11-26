"use client";
// Public shared sales document (M45.S01.T013): no login; the token is the only credential.
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type Meta = { title: string; version: number; file_name: string | null; size_bytes: number | null; sha256: string | null; available: boolean; note: string | null; expires_at: string };

export default function SharedDoc() {
  const { t, f, err } = useI18n();
  const { token } = useParams<{ token: string }>();
  const url = `${API_ORIGIN}/api/v1/public/docs/${encodeURIComponent(token)}`;
  const [m, setM] = useState<Meta | null>(null);
  const [gone, setGone] = useState<number | null>(null);   // HTTP status of a failed load (0 = network)
  useEffect(() => {
    fetch(url).then(async (r) => {
      if (!r.ok) { setGone(r.status); return; }
      setM(await r.json());
      fetch(`${url}/view`, { method: "POST" }).catch(() => undefined);   // recorded only once the page rendered
    }).catch(() => setGone(0));
  }, [url]);
  return (
    <main className="min-h-screen bg-gray-50 flex items-start justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl border shadow-sm p-5 space-y-3 text-sm">
        <div className="flex items-start justify-between gap-2"><h1 className="text-lg font-semibold">{t("docs.file.title")}</h1><LanguageSwitcher /></div>
        {gone !== null ? <p className="text-red-600">{gone === 404 ? t("docs.file.invalid") : err(gone)}</p> : !m ? <p className="text-gray-500">{t("common.loading")}</p> : <>
          <p className="font-medium">{m.title} <span className="text-gray-500">{t("docs.file.version", { n: m.version })}</span></p>
          <p className="text-xs text-gray-500">{m.file_name}{m.size_bytes ? ` · ${f.number(m.size_bytes / 1024)} KB` : ""} · {t("docs.file.availableUntil", { date: f.date(m.expires_at) })}</p>
          {m.sha256 && <p className="text-xs text-gray-500 break-all">SHA-256: {m.sha256}</p>}
          {m.available ? <a className="block text-center bg-indigo-600 text-white rounded py-2 font-semibold" href={`${url}/file`}>{t("docs.file.download")}</a>
            : <p className="text-amber-700 text-xs">{t("docs.file.scanning")}</p>}
        </>}
      </div>
    </main>
  );
}
