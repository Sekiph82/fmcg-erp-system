"use client";
// Public help article (no login). Content is shown as plain text (no HTML injection from article bodies).
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import LanguageSwitcher from "@/components/LanguageSwitcher";

interface Article { slug: string; title: string; summary: string | null; content_md: string; updated_at: string | null }

export default function PublicArticle() {
  const { t } = useI18n();
  const { slug } = useParams<{ slug: string }>();
  const [article, setArticle] = useState<Article | null | undefined>(undefined);
  const [voted, setVoted] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_ORIGIN}/api/v1/public/kb/articles/${encodeURIComponent(slug)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setArticle)
      .catch(() => setArticle(null));
  }, [slug]);

  async function vote(helpful: boolean) {
    const r = await fetch(`${API_ORIGIN}/api/v1/public/kb/articles/${encodeURIComponent(slug)}/feedback`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ helpful }),
    }).catch(() => null);
    setVoted(r && r.status === 202 ? t("public.kb.feedbackThanks") : t("public.kb.feedbackFailed"));
  }

  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2"><Link href="/kb" className="text-sm text-indigo-700">← {t("public.kb.title")}</Link><LanguageSwitcher /></div>
        {article === undefined ? <p className="text-sm text-gray-500">{t("common.loading")}</p> : article === null ? (
          <p className="text-sm text-gray-600">{t("public.kb.articleMissing")}</p>
        ) : (
          <>
            <h1 className="text-2xl font-bold break-words">{article.title}</h1>
            {article.summary && <p className="text-gray-600">{article.summary}</p>}
            <article className="whitespace-pre-wrap break-words text-sm leading-relaxed">{article.content_md}</article>
            <div className="border-t pt-3 text-sm flex flex-wrap items-center gap-2">
              {voted ? <span role="status">{voted}</span> : <>
                <span>{t("public.kb.helpful")}</span>
                <button className="px-3 py-1 border rounded-lg" onClick={() => vote(true)}>{t("common.yes")}</button>
                <button className="px-3 py-1 border rounded-lg" onClick={() => vote(false)}>{t("common.no")}</button>
              </>}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
