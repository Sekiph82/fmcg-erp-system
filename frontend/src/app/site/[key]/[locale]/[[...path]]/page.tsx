// M46 public website page: /site/<site>/<locale>/<path>. The server renders the anonymous live version (SEO metadata,
// hreflang alternates, canonical, JSON-LD); the browser then asks again with its consented visitor id and portal
// cookie, so personalization and members-only content never pass through a shared cache.
import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import SiteView, { type PageData } from "@/components/site/SiteView";

type Params = { key: string; locale: string; path?: string[] };
const SERVER_API = process.env.INTERNAL_API_URL ?? API_ORIGIN;

async function load(p: Params): Promise<{ status: number; data?: PageData & { redirect?: string } }> {
  const path = "/" + (p.path ?? []).map(encodeURIComponent).join("/");
  try {
    const r = await fetch(`${SERVER_API}/api/v1/public/cms/site/${encodeURIComponent(p.key)}/page?path=${encodeURIComponent(path)}&locale=${encodeURIComponent(p.locale)}`,
      { cache: "no-store" });
    return { status: r.status, data: r.ok ? await r.json() : undefined };
  } catch {
    return { status: 503 };
  }
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const p = await params;
  const { data } = await load(p);
  if (!data || data.redirect) return { title: "POVU" };
  const base = `/site/${p.key}`;
  const languages = Object.fromEntries(data.alternates.map((a) => [a.locale, `${base}/${a.locale}${a.path === "/" ? "" : a.path}`]));
  return {
    title: data.seo.meta_title || `${data.page.title} · ${data.site.name}`,
    description: data.seo.meta_description || undefined,
    keywords: data.seo.keywords,
    alternates: { canonical: data.canonical, languages },
    robots: data.seo.noindex || data.page.members_only ? { index: false, follow: false } : undefined,
    openGraph: { title: data.page.title, siteName: data.site.name, locale: data.page.locale, images: data.seo.og_image ? [data.seo.og_image] : undefined },
  };
}

export default async function SitePage({ params }: { params: Promise<Params> }) {
  const p = await params;
  const { status, data } = await load(p);
  if (data?.redirect) redirect(`/site/${p.key}/${p.locale}${data.redirect === "/" ? "" : data.redirect}`);
  if (status === 404) notFound();
  return <SiteView siteKey={p.key} locale={p.locale} path={"/" + (p.path ?? []).join("/")} initial={data ?? null} initialStatus={status} />;
}
