"use client";
// M46 public site shell: theme, navigation, language switcher, blocks, members gate and experiment conversions.
import { useEffect, useState } from "react";
import { API_ORIGIN } from "@/lib/api";
import { SiteBlocks, type Block, type Theme } from "./SiteBlocks";

export type PageData = {
  site: { key: string; name: string; theme: Theme; nav: { label: string; path: string; locale?: string }[]; locales: string[]; default_locale: string };
  page: { id: string; title: string; kind: string; locale: string; path: string; author: string | null; category: string | null; tags: string[];
    published_at: string; version: number; members_only: boolean };
  blocks: Block[]; seo: { meta_title?: string; meta_description?: string; noindex?: boolean; keywords?: string[]; og_image?: string; canonical?: string };
  alternates: { locale: string; path: string }[]; json_ld: object[]; experiments: Record<string, string>; personalized: boolean; canonical: string;
};

const LANG: Record<string, string> = { en: "English", sw: "Kiswahili", tr: "Türkçe" };
const MSG: Record<string, Record<string, string>> = {
  en: { members: "This page is for signed-in members.", denied: "Your account does not have access to this page.", signin: "Sign in", unavailable: "This page is not available right now.", by: "By" },
  sw: { members: "Ukurasa huu ni kwa wanachama walioingia.", denied: "Akaunti yako haina ruhusa ya ukurasa huu.", signin: "Ingia", unavailable: "Ukurasa huu haupatikani kwa sasa.", by: "Na" },
  tr: { members: "Bu sayfa giriş yapmış üyeler içindir.", denied: "Hesabınızın bu sayfaya erişimi yok.", signin: "Giriş yap", unavailable: "Bu sayfa şu anda kullanılamıyor.", by: "Yazar" },
};

function consentedVisitor(): string | null {
  try {
    const c = JSON.parse(localStorage.getItem("povu_consent_v1") || "null");
    return c && (c.analytics || c.marketing) ? localStorage.getItem("povu_vid") : null;
  } catch { return null; }
}

export default function SiteView({ siteKey, locale, path, initial, initialStatus }: { siteKey: string; locale: string; path: string; initial: PageData | null; initialStatus: number }) {
  const [data, setData] = useState<PageData | null>(initial);
  const [status, setStatus] = useState(initialStatus);
  const t = MSG[locale] ?? MSG.en;

  useEffect(() => {
    const visitor = consentedVisitor();
    if (initialStatus === 200 && !visitor) return;          // anonymous: the server render is already right
    const q = new URLSearchParams({ path, locale, ...(visitor ? { visitor } : {}) });
    fetch(`${API_ORIGIN}/api/v1/public/cms/site/${encodeURIComponent(siteKey)}/page?${q}`, { credentials: "include", cache: "no-store" })
      .then(async (r) => { setStatus(r.status); if (r.ok) setData(await r.json()); })
      .catch(() => {});
  }, [siteKey, locale, path, initialStatus]);

  useEffect(() => { document.documentElement.lang = locale; }, [locale]);

  // experiment conversion: any click on a link inside the page counts for the experiments shown
  const convert = () => {
    const visitor = consentedVisitor();
    if (!visitor || !data) return;
    for (const experiment of Object.keys(data.experiments)) {
      fetch(`${API_ORIGIN}/api/v1/public/cms/site/${encodeURIComponent(siteKey)}/convert`, { method: "POST", keepalive: true,
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path, locale, experiment, visitor }) }).catch(() => {});
    }
  };

  const base = `/site/${siteKey}/${data?.page.locale ?? locale}`;
  const theme = data?.site.theme;
  if (!data || !theme) {
    return <main className="min-h-screen p-6 max-w-2xl mx-auto">
      {status === 401 ? <p>{t.members} <a className="underline" href="/portal/login">{t.signin}</a></p>
        : status === 403 ? <p>{t.denied}</p> : <p>{t.unavailable}</p>}</main>;
  }
  return (
    <div style={{ background: theme.background, color: theme.text_color, fontFamily: theme.font }} className="min-h-screen">
      {data.json_ld.map((ld, i) => <script key={i} type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(ld).replace(/</g, "\\u003c") }} />)}
      <header className="border-b" style={{ borderColor: `${theme.brand_color}33` }}>
        <div className="max-w-5xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-3">
          <a href={base} className="font-bold text-lg" style={{ color: theme.brand_color }}>{data.site.name}</a>
          <nav aria-label="Main" className="flex flex-wrap gap-4 text-sm">{data.site.nav.filter((n) => !n.locale || n.locale === data.page.locale).map((n) =>
            <a key={n.path + n.label} href={n.path.startsWith("/") ? `${base}${n.path === "/" ? "" : n.path}` : n.path} className="hover:underline">{n.label}</a>)}</nav>
          {data.alternates.length > 1 && <nav aria-label="Language" className="flex gap-2 text-xs">{data.alternates.map((a) =>
            <a key={a.locale} hrefLang={a.locale} lang={a.locale} href={`/site/${siteKey}/${a.locale}${a.path === "/" ? "" : a.path}`}
              className={a.locale === data.page.locale ? "font-bold underline" : "opacity-70"}>{LANG[a.locale] ?? a.locale}</a>)}</nav>}
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-4 py-6" onClickCapture={(e) => { if ((e.target as HTMLElement).closest("a")) convert(); }}>
        {data.page.kind === "POST" && <div className="mb-4"><h1 className="text-3xl font-bold">{data.page.title}</h1>
          <p className="text-sm opacity-70">{data.page.author && `${t.by} ${data.page.author} · `}{new Date(data.page.published_at).toLocaleDateString(data.page.locale)}{data.page.category ? ` · ${data.page.category}` : ""}</p></div>}
        <SiteBlocks blocks={data.blocks} theme={theme} base={base} siteKey={siteKey} />
      </main>
      <footer className="max-w-5xl mx-auto px-4 py-6 text-xs opacity-60">© {data.site.name}</footer>
    </div>
  );
}
