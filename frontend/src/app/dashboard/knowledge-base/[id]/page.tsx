"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { kbApi, KBArticleDetail, KBRevision } from "@/lib/knowledge_base";

function renderMarkdown(md: string): string {
  // Basic markdown rendering without external lib
  return md
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold text-gray-800 mt-4 mb-2">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold text-gray-900 mt-6 mb-2 border-b pb-1">$2</h2>'.replace('$2', '$1'))
    .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold text-gray-900 mt-6 mb-3">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-xs font-mono">$1</code>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 text-gray-700 text-sm">• $1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 text-gray-700 text-sm list-decimal">$1</li>')
    .replace(/\n\n/g, '</p><p class="text-sm text-gray-700 leading-relaxed mb-3">')
    .replace(/^(?!<[h|l])(.+)$/gm, (m) => m.startsWith('<') ? m : `<p class="text-sm text-gray-700 leading-relaxed mb-3">${m}</p>`);
}

export default function ArticleViewPage() {
  const { id } = useParams<{ id: string }>();
  const [article, setArticle] = useState<KBArticleDetail | null>(null);
  const [revisions, setRevisions] = useState<KBRevision[]>([]);
  const [showRevisions, setShowRevisions] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    kbApi.getArticle(id).then(a => { setArticle(a); setLoading(false); });
  }, [id]);

  const loadRevisions = async () => {
    if (!showRevisions) {
      const revs = await kbApi.listRevisions(id);
      setRevisions(revs);
    }
    setShowRevisions(s => !s);
  };

  if (loading) return <div className="p-6 text-sm text-gray-500">Loading…</div>;
  if (!article) return <div className="p-6 text-sm text-red-500">Article not found.</div>;

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              {article.category_name && (
                <a href={`/dashboard/knowledge-base/articles?category_id=${article.category_id}`}
                  className="text-xs bg-blue-50 text-blue-600 rounded px-2 py-0.5 hover:underline">
                  {article.category_name}
                </a>
              )}
              {article.is_featured && (
                <span className="text-xs bg-amber-100 text-amber-700 rounded px-2 py-0.5">★ Featured</span>
              )}
              <span className={`text-xs rounded-full px-2 py-0.5 ${
                article.status === "PUBLISHED" ? "bg-green-100 text-green-700" :
                article.status === "DRAFT" ? "bg-gray-100 text-gray-600" : "bg-red-100 text-red-500"
              }`}>
                {article.status}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{article.title}</h1>
            {article.summary && <p className="text-sm text-gray-500 mt-1">{article.summary}</p>}
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <a href={`/dashboard/knowledge-base/${id}/edit`}
              className="rounded border px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50">
              Edit
            </a>
            <button onClick={loadRevisions}
              className="rounded border px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50">
              History ({article.version})
            </button>
          </div>
        </div>

        <div className="flex gap-4 text-xs text-gray-400 mt-3">
          {article.author_name && <span>By {article.author_name}</span>}
          {article.published_at && <span>Published {new Date(article.published_at).toLocaleDateString()}</span>}
          {article.updated_at && <span>Updated {new Date(article.updated_at).toLocaleDateString()}</span>}
          <span>{article.view_count} views</span>
          <span>v{article.version}</span>
        </div>

        {(article.tags ?? []).length > 0 && (
          <div className="flex gap-2 mt-3 flex-wrap">
            {(article.tags ?? []).map((tag: string) => (
              <span key={tag} className="text-xs bg-gray-100 text-gray-500 rounded px-2 py-0.5">#{tag}</span>
            ))}
          </div>
        )}
      </div>

      {showRevisions && revisions.length > 0 && (
        <div className="mb-5 bg-gray-50 border rounded-lg p-4">
          <h3 className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Version History</h3>
          <div className="space-y-2">
            {revisions.map(r => (
              <div key={r.id} className="flex items-center justify-between text-xs text-gray-600">
                <span className="font-mono">v{r.version_no}</span>
                <span className="flex-1 mx-3 text-gray-500">{r.change_summary ?? "Updated"}</span>
                <span className="text-gray-400">{r.changed_by_name ?? "—"}</span>
                <span className="text-gray-400 ml-3">{r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg p-6 prose max-w-none">
        {article.content_md ? (
          <div
            dangerouslySetInnerHTML={{ __html: renderMarkdown(article.content_md) }}
            className="space-y-2"
          />
        ) : (
          <p className="text-gray-400 text-sm italic">No content yet.</p>
        )}
      </div>

      <div className="mt-4 flex gap-3 text-xs">
        <a href="/dashboard/knowledge-base" className="text-blue-600 hover:underline">← Knowledge Base</a>
        <span className="text-gray-300">|</span>
        <a href="/dashboard/knowledge-base/articles" className="text-blue-600 hover:underline">All Articles</a>
      </div>
    </div>
  );
}
