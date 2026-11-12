"use client";
// Public help article (no login). Content is shown as plain text (no HTML injection from article bodies).
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { API_ORIGIN } from "@/lib/api";

interface Article { slug: string; title: string; summary: string | null; content_md: string; updated_at: string | null }

export default function PublicArticle() {
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
    setVoted(r && r.status === 202 ? "Thank you for the feedback." : "Feedback could not be sent right now.");
  }

  return (
    <main className="min-h-screen bg-white text-gray-900 p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <Link href="/kb" className="text-sm text-indigo-700">← Help centre</Link>
        {article === undefined ? <p className="text-sm text-gray-500">Loading…</p> : article === null ? (
          <p className="text-sm text-gray-600">This article is not available.</p>
        ) : (
          <>
            <h1 className="text-2xl font-bold">{article.title}</h1>
            {article.summary && <p className="text-gray-600">{article.summary}</p>}
            <article className="whitespace-pre-wrap text-sm leading-relaxed">{article.content_md}</article>
            <div className="border-t pt-3 text-sm flex items-center gap-2">
              {voted ? <span role="status">{voted}</span> : <>
                Was this helpful?
                <button className="px-3 py-1 border rounded-lg" onClick={() => vote(true)}>Yes</button>
                <button className="px-3 py-1 border rounded-lg" onClick={() => vote(false)}>No</button>
              </>}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
