"use client";
// Visitor's reschedule / cancel page for a booking (M43.S01.T005); the token in the link is the credential.
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

interface View { page_slug: string; title: string; status: string; time_zone: string; start_utc: string;
  duration_minutes: number; meeting_url: string | null; visitor_name: string }
interface Slot { start_utc: string }

const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export default function ManageBooking() {
  const { t, f, err } = useI18n();
  const { token } = useParams<{ token: string }>();
  const tz = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi", []);
  const base = `${API_ORIGIN}/api/v1/public/book/manage/${encodeURIComponent(token)}`;
  const [view, setView] = useState<View | null | "missing">(null);
  const [day, setDay] = useState(isoDay(new Date()));
  const [slots, setSlots] = useState<Slot[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  const load = () => fetch(base).then(async (r) => (r.ok ? setView(await r.json()) : setView("missing"))).catch(() => setView("missing"));
  useEffect(() => { load(); }, [base]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!view || view === "missing") return;
    fetch(`${API_ORIGIN}/api/v1/public/book/${encodeURIComponent(view.page_slug)}/slots?day=${day}&tz=${encodeURIComponent(tz)}`)
      .then((r) => r.json()).then((d) => setSlots(d.slots ?? [])).catch(() => setSlots([]));
  }, [view, day, tz]);

  async function act(path: string, body?: object) {
    const r = await fetch(`${base}/${path}`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined }).catch(() => null);
    setMsg(r?.ok ? (path === "cancel" ? t("public.book.cancelled") : t("public.book.moved")) : err(r?.status));
    load();
  }

  if (view === null) return <main className="p-6 text-sm text-gray-500 space-y-3"><div className="flex justify-end"><LanguageSwitcher /></div><p>{t("common.loading")}</p></main>;
  if (view === "missing") return <main className="p-6 text-sm text-gray-600 space-y-3"><div className="flex justify-end"><LanguageSwitcher /></div><p>{t("public.book.linkInvalid")}</p></main>;
  const when = f.dateTime(view.start_utc);
  return (
    <main className="p-4 md:p-6 max-w-lg mx-auto space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2"><h1 className="text-xl font-semibold break-words min-w-0">{view.title}</h1><LanguageSwitcher /></div>
      <p className="text-sm text-gray-700 break-words">{view.status === "SCHEDULED" ? t("public.book.bookedFor", { name: view.visitor_name, when, tz }) : t("public.book.isCancelled", { name: view.visitor_name })}</p>
      {view.meeting_url && <a className="text-sm text-indigo-600 underline break-all" href={view.meeting_url}>{view.meeting_url}</a>}
      {msg && <p role="status" className="text-sm text-gray-800">{msg}</p>}
      {view.status === "SCHEDULED" && (
        <>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="day">{t("public.book.moveDay")}</label>
            <input id="day" type="date" value={day} min={isoDay(new Date())} onChange={(e) => setDay(e.target.value)}
                   className="border rounded-lg px-3 py-2 text-sm w-full" />
            <div className="grid grid-cols-3 gap-2">
              {slots.map((s) => (
                <button key={s.start_utc} onClick={() => act("reschedule", { start_utc: s.start_utc })}
                        className="px-2 py-2 rounded-lg border text-sm bg-white">
                  {f.time(s.start_utc)}
                </button>
              ))}
            </div>
          </div>
          <button onClick={() => { if (confirm(t("public.book.confirmCancel"))) act("cancel"); }}
                  className="w-full border border-red-300 text-red-700 rounded-lg py-2 text-sm">{t("public.book.cancelBooking")}</button>
        </>
      )}
    </main>
  );
}
