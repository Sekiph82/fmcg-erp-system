"use client";
// Public self-booking page (M43.S01.T005), no login. Hosts stay anonymous; times shown in the visitor's zone.
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

interface Page { slug: string; title: string; description: string | null; duration_minutes: number; time_zone: string;
  weekdays: number[]; max_days_ahead: number; consent_text: string | null }
interface Slot { start_utc: string; start_local: string }

const visitorTz = () => Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi";
const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export default function BookingPage() {
  const { t, f, err, locale } = useI18n();
  const { slug } = useParams<{ slug: string }>();
  const tz = useMemo(() => visitorTz(), []);
  const [page, setPage] = useState<Page | null>(null);
  const [state, setState] = useState<"loading" | "missing" | "ready" | "booked">("loading");
  const [day, setDay] = useState(isoDay(new Date()));
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [picked, setPicked] = useState<Slot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manage, setManage] = useState<string | null>(null);
  const [invited, setInvited] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API_ORIGIN}/api/v1/public/book/${encodeURIComponent(slug)}`)
      .then(async (r) => { if (!r.ok) throw new Error(); setPage(await r.json()); setState("ready"); })
      .catch(() => setState("missing"));
  }, [slug]);

  useEffect(() => {
    if (state !== "ready") return;
    setSlots(null); setPicked(null);
    fetch(`${API_ORIGIN}/api/v1/public/book/${encodeURIComponent(slug)}/slots?day=${day}&tz=${encodeURIComponent(tz)}`)
      .then((r) => r.json()).then((d) => setSlots(d.slots ?? [])).catch(() => setSlots([]));
  }, [slug, day, tz, state]);

  const days = useMemo(() => {
    const out: string[] = [];
    const n = Math.min(page?.max_days_ahead ?? 14, 21);
    for (let i = 0; i < n; i++) { const d = new Date(); d.setDate(d.getDate() + i); out.push(isoDay(d)); }
    return out;
  }, [page]);

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!picked) return;
    const data = new FormData(e.currentTarget);
    setBusy(true); setError(null);
    const r = await fetch(`${API_ORIGIN}/api/v1/public/book/${encodeURIComponent(slug)}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start_utc: picked.start_utc, name: data.get("name"), email: data.get("email"),
        consent: data.get("consent") === "on", website: data.get("website") || null }),
    }).catch(() => null);
    setBusy(false);
    if (r && r.status === 201) { const j = await r.json(); setManage(j.manage_token); setInvited(j.invitation === "SENT"); setState("booked"); return; }
    setError(err(r?.status));
  }

  if (state === "loading") return <main className="p-6 text-sm text-gray-500 space-y-3"><div className="flex justify-end"><LanguageSwitcher /></div><p>{t("common.loading")}</p></main>;
  if (state === "missing" || !page) return <main className="p-6 text-sm text-gray-600 space-y-3"><div className="flex justify-end"><LanguageSwitcher /></div><p>{t("public.book.pageMissing")}</p></main>;
  if (state === "booked") {
    const url = `${window.location.origin}/book/manage/${manage}`;
    return (
      <main className="p-6 max-w-lg mx-auto space-y-3">
        <div className="flex justify-end"><LanguageSwitcher /></div>
        <h1 className="text-xl font-semibold">{t("public.book.booked")}</h1>
        <p className="text-sm text-gray-700 break-words">{page.title} — {picked && f.dateTime(picked.start_utc)} ({tz}).</p>
        <p className="text-sm text-gray-700">{invited ? t("public.book.invited") : t("public.book.saved")} {t("public.book.keepLink")}</p>
        <a className="text-indigo-600 underline break-all text-sm" href={url}>{url}</a>
      </main>
    );
  }
  const input = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white text-gray-900";
  return (
    <main className="p-4 md:p-6 max-w-2xl mx-auto space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h1 className="text-xl font-semibold text-gray-900 break-words min-w-0">{page.title}</h1>
        <LanguageSwitcher />
      </div>
      <div>
        {page.description && <p className="text-sm text-gray-600 mt-1 whitespace-pre-line">{page.description}</p>}
        <p className="text-xs text-gray-500 mt-1 break-words">{t("public.book.durationTz", { minutes: f.number(page.duration_minutes), tz })}</p>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label={t("public.book.day")}>
        {days.map((d) => (
          <button key={d} role="tab" aria-selected={d === day} onClick={() => setDay(d)}
                  className={`shrink-0 px-3 py-2 rounded-lg border text-xs ${d === day ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-700"}`}>
            {f.day(`${d}T12:00:00`)}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2" aria-live="polite">
        {slots === null && <p className="col-span-full text-sm text-gray-500">{t("public.book.loadingTimes")}</p>}
        {slots?.length === 0 && <p className="col-span-full text-sm text-gray-500">{t("public.book.noTimes")}</p>}
        {slots?.map((s) => (
          <button key={s.start_utc} onClick={() => setPicked(s)}
                  className={`px-2 py-2 rounded-lg border text-sm ${picked?.start_utc === s.start_utc ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-800"}`}>
            {f.time(s.start_utc)}
          </button>
        ))}
      </div>
      {picked && (
        <form onSubmit={submit} className="space-y-3 border rounded-lg p-4 bg-white">
          <input name="name" required maxLength={200} placeholder={t("public.book.name")} aria-label={t("public.book.name")} className={input} />
          <input name="email" type="email" required placeholder={t("common.email")} aria-label={t("common.email")} className={input} />
          <input name="website" tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
          {page.consent_text && (
            <label className="flex gap-2 text-xs text-gray-700"><input type="checkbox" name="consent" required /> <span className="min-w-0 break-words">{page.consent_text}</span></label>
          )}
          {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
          <button disabled={busy} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm disabled:opacity-50">
            {busy ? t("public.book.booking") : t("public.book.bookThis")}
          </button>
        </form>
      )}
    </main>
  );
}
