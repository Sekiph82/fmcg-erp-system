"use client";
// M46.S01.T006 members-only help articles: shown to signed-in portal accounts on the article's access list.
import { useEffect, useState } from "react";
import Link from "next/link";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type Item = { slug: string; title: string; summary: string | null };
type Article = Item & { content_md: string };

export default function MemberArticles() {
  const { t } = useI18n();
  const [items, setItems] = useState<Item[] | null | "signin">(null);
  const [open, setOpen] = useState<Article | null>(null);
  useEffect(() => {
    fetch(`${API_ORIGIN}/api/v1/public/kb/members/articles`, { credentials: "include" })
      .then(async (r) => setItems(r.status === 401 ? "signin" : r.ok ? await r.json() : []))
      .catch(() => setItems([]));
  }, []);
  const read = (slug: string) => fetch(`${API_ORIGIN}/api/v1/public/kb/members/articles/${encodeURIComponent(slug)}`, { credentials: "include" })
    .then((r) => (r.ok ? r.json() : null)).then(setOpen).catch(() => setOpen(null));
  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2"><Link href="/kb" className="text-sm text-indigo-700">← {t("public.kb.title")}</Link><LanguageSwitcher /></div>
        <h1 className="text-2xl font-bold break-words">{t("public.kb.membersTitle")}</h1>
        {items === null ? <p className="text-sm text-gray-500">{t("common.loading")}</p>
          : items === "signin" ? <p className="text-sm">{t("public.kb.membersSignInBefore")}<a className="underline" href="/portal/login">{t("public.kb.membersSignInLink")}</a>{t("public.kb.membersSignInAfter")}</p>
          : items.length === 0 ? <p className="text-sm text-gray-600">{t("public.kb.membersNone")}</p>
          : <ul className="space-y-2">{items.map((a) => <li key={a.slug}><button className="text-indigo-700 underline text-left break-words" onClick={() => read(a.slug)}>{a.title}</button>
            {a.summary && <p className="text-xs text-gray-600">{a.summary}</p>}</li>)}</ul>}
        {open && <article className="border-t pt-3"><h2 className="text-xl font-semibold">{open.title}</h2><div className="whitespace-pre-wrap break-words text-sm leading-relaxed">{open.content_md}</div></article>}
      </div>
    </main>
  );
}
