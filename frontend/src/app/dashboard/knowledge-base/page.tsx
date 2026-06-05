"use client";
import { useEffect, useState } from "react";
import { kbApi, KBStats, KBCategory, KBArticle } from "@/lib/knowledge_base";
import { RequirePermission } from "@/components/PermissionGuard";
import { PageHelpTooltip } from "@/components/help/PageHelpTooltip";

export default function KBHomePage() {
  const [stats, setStats] = useState<KBStats | null>(null);
  const [categories, setCategories] = useState<KBCategory[]>([]);
  const [featured, setFeatured] = useState<KBArticle[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<KBArticle[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      kbApi.getStats(),
      kbApi.listCategories(),
      kbApi.listArticles({ status: "PUBLISHED", limit: 6 }),
    ]).then(([s, cats, articles]) => {
      setStats(s);
      setCategories(cats);
      setFeatured(articles.filter(a => a.is_featured).slice(0, 3).concat(articles.filter(a => !a.is_featured)).slice(0, 6));
    }).finally(() => setLoading(false));
  }, []);

  const doSearch = async () => {
    if (!searchQuery.trim() || searchQuery.length < 2) return;
    setSearching(true);
    try {
      const results = await kbApi.search(searchQuery);
      setSearchResults(results);
    } finally {
      setSearching(false);
    }
  };

  return (
    <RequirePermission permission="knowledge_base.view">
    <div className="p-6 space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <PageHelpTooltip topic="knowledge-base" />
        </div>
        <p className="text-sm text-gray-500 mt-0.5">Internal wiki — SOPs, guides, policies, and how-tos.</p>
      </div>

      {/* Search */}
      <div className="bg-white border rounded-xl p-6 shadow-sm">
        <div className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={e => { setSearchQuery(e.target.value); if (!e.target.value) setSearchResults([]); }}
            onKeyDown={e => e.key === "Enter" && doSearch()}
            placeholder="Search articles, SOPs, guides…"
            className="flex-1 border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          <button onClick={doSearch} disabled={searching}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {searching ? "…" : "Search"}
          </button>
        </div>
        {searchResults.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{searchResults.length} Results</p>
            {searchResults.map(a => (
              <a key={a.id} href={`/dashboard/knowledge-base/${a.id}`}
                className="block p-3 rounded-lg border hover:bg-blue-50 transition-colors">
                <p className="text-sm font-medium text-gray-800">{a.title}</p>
                {a.summary && <p className="text-xs text-gray-500 mt-0.5 truncate">{a.summary}</p>}
                <p className="text-xs text-gray-400 mt-0.5">{a.category_name ?? "Uncategorized"} · {a.view_count} views</p>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Published Articles", value: stats.published, color: "text-blue-600" },
            { label: "Draft Articles", value: stats.drafts, color: "text-amber-600" },
            { label: "Categories", value: stats.categories, color: "text-green-600" },
            { label: "Total", value: stats.total_articles, color: "text-gray-700" },
          ].map(s => (
            <div key={s.label} className="bg-white border rounded-lg p-4 shadow-sm">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-2xl font-bold mt-1 ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Categories */}
        <div className="bg-white border rounded-lg shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-800">Categories</h2>
            <a href="/dashboard/knowledge-base/categories" className="text-xs text-blue-600 hover:underline">Manage</a>
          </div>
          {loading ? (
            <p className="text-xs text-gray-400">Loading…</p>
          ) : categories.length === 0 ? (
            <p className="text-xs text-gray-400">No categories yet.</p>
          ) : (
            <div className="space-y-2">
              {categories.map(c => (
                <a key={c.id} href={`/dashboard/knowledge-base/articles?category_id=${c.id}`}
                  className="flex items-center justify-between p-2 rounded hover:bg-gray-50">
                  <div className="flex items-center gap-2">
                    {c.icon && <span>{c.icon}</span>}
                    <span className="text-sm text-gray-700">{c.name}</span>
                  </div>
                  <span className="text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-0.5">{c.article_count}</span>
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Recent/Featured Articles */}
        <div className="lg:col-span-2 bg-white border rounded-lg shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-800">Recent Articles</h2>
            <div className="flex gap-2">
              <a href="/dashboard/knowledge-base/articles" className="text-xs text-blue-600 hover:underline">View all</a>
              <a href="/dashboard/knowledge-base/articles/new" className="text-xs text-blue-600 hover:underline">+ New</a>
            </div>
          </div>
          {loading ? (
            <p className="text-xs text-gray-400">Loading…</p>
          ) : featured.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <p className="text-2xl mb-2">📝</p>
              <p className="text-sm">No articles published yet.</p>
              <a href="/dashboard/knowledge-base/articles/new" className="text-xs text-blue-600 hover:underline mt-1 block">
                Write your first article →
              </a>
            </div>
          ) : (
            <div className="space-y-3">
              {featured.map(a => (
                <a key={a.id} href={`/dashboard/knowledge-base/${a.id}`}
                  className="block p-3 rounded-lg border hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        {a.is_featured && <span className="text-xs bg-amber-100 text-amber-700 rounded px-1.5">Featured</span>}
                        <p className="text-sm font-medium text-gray-800 truncate">{a.title}</p>
                      </div>
                      {a.summary && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{a.summary}</p>}
                      <div className="flex gap-2 mt-1 flex-wrap">
                        {a.category_name && (
                          <span className="text-xs bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">{a.category_name}</span>
                        )}
                        {(a.tags ?? []).slice(0, 3).map((tag: string) => (
                          <span key={tag} className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">#{tag}</span>
                        ))}
                      </div>
                    </div>
                    <div className="text-xs text-gray-400 text-right whitespace-nowrap">
                      <p>{a.view_count} views</p>
                      <p>v{a.version}</p>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Articles */}
      {stats?.top_articles && stats.top_articles.length > 0 && (
        <div className="bg-white border rounded-lg shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-3">Most Viewed</h2>
          <div className="flex gap-3 flex-wrap">
            {stats.top_articles.map((a, i) => (
              <a key={a.id} href={`/dashboard/knowledge-base/${a.id}`}
                className="flex items-center gap-2 border rounded-full px-3 py-1.5 hover:bg-blue-50 transition-colors">
                <span className="text-xs font-bold text-gray-400">#{i+1}</span>
                <span className="text-xs text-gray-700">{a.title}</span>
                <span className="text-xs text-gray-400">{a.view_count}×</span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
    </RequirePermission>
  );
}
