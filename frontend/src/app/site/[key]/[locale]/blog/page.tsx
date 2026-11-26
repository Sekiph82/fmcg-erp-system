// M46.S01.T002 public blog index for a site and language (published public posts only).
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

type Post = { title: string; path: string; author: string | null; category: string | null; published_at: string; description: string | null };
const SERVER_API = process.env.INTERNAL_API_URL ?? API_ORIGIN;

async function load(key: string, locale: string, category?: string) {
  const q = new URLSearchParams({ locale, ...(category ? { category } : {}) });
  const r = await fetch(`${SERVER_API}/api/v1/public/cms/site/${encodeURIComponent(key)}/blog?${q}`, { cache: "no-store" }).catch(() => null);
  return r && r.ok ? (await r.json()) as { site: { name: string; theme: { brand_color: string } }; posts: Post[] } : null;
}

export async function generateMetadata({ params }: { params: Promise<{ key: string; locale: string }> }): Promise<Metadata> {
  const { key, locale } = await params;
  const d = await load(key, locale);
  return { title: d ? `Blog · ${d.site.name}` : "Blog", alternates: { canonical: `/site/${key}/${locale}/blog` } };
}

export default async function Blog({ params, searchParams }: { params: Promise<{ key: string; locale: string }>; searchParams: Promise<{ category?: string }> }) {
  const { key, locale } = await params;
  const { category } = await searchParams;
  const d = await load(key, locale, category);
  if (!d) notFound();
  const cats = Array.from(new Set(d.posts.map((p) => p.category).filter(Boolean))) as string[];
  return (
    <main lang={locale} className="max-w-3xl mx-auto px-4 py-8 space-y-4">
      <a href={`/site/${key}/${locale}`} className="font-bold" style={{ color: d.site.theme.brand_color }}>{d.site.name}</a>
      <h1 className="text-3xl font-bold">Blog</h1>
      {cats.length > 0 && <nav aria-label="Categories" className="flex flex-wrap gap-2 text-sm">{cats.map((c) =>
        <a key={c} href={`?category=${encodeURIComponent(c)}`} className="border rounded px-2 py-0.5">{c}</a>)}</nav>}
      {d.posts.length === 0 ? <p className="text-sm opacity-70">No posts yet.</p> : <ul className="space-y-4">{d.posts.map((p) =>
        <li key={p.path}><a href={`/site/${key}/${locale}${p.path}`} className="text-xl font-semibold underline">{p.title}</a>
          <p className="text-xs opacity-70">{p.author ?? ""}{p.author ? " · " : ""}{new Date(p.published_at).toLocaleDateString(locale)}{p.category ? ` · ${p.category}` : ""}</p>
          {p.description && <p className="text-sm">{p.description}</p>}</li>)}</ul>}
    </main>
  );
}
