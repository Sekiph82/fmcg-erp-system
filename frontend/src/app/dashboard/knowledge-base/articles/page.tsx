"use client";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { kbApi, KBArticle, KBCategory } from "@/lib/knowledge_base";

export default function ArticleListPage() {
  const params = useSearchParams();
  const [articles, setArticles] = useState<KBArticle[]>([]);
  const [categories, setCategories] = useState<KBCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCat, setFilterCat] = useState(params.get("category_id") ?? "");
  const [filterStatus, setFilterStatus] = useState("PUBLISHED");
  const [search, setSearch] = useState("");

  const load = useCallback(async (filters?: { search?: string }) => {
    setLoading(true);
    try {
      const data = await kbApi.listArticles({
        category_id: filterCat || undefined,
        status: filterStatus || undefined,
        search: filters?.search || undefined,
        limit: 100,
      });
      setArticles(data);
    } finally {
      setLoading(false);
    }
  }, [filterCat, filterStatus]);

  useEffect(() => {
    kbApi.listCategories().then(setCategories);
  }, []);

  useEffect(() => { load(); }, [load]);

  const searchSubmit = (e: React.FormEvent) => { e.preventDefault(); load({ search }); };

  const del = async (id: string) => {
    if (!confirm("Archive this article?")) return;
    await kbApi.deleteArticle(id);
    await load();
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-gray-900">Articles</h1>
        <a href="/dashboard/knowledge-base/articles/new"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + New Article
        </a>
      </div>

      <div className="flex gap-3 flex-wrap">
        <form onSubmit={searchSubmit} className="flex gap-2">
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search…"
            className="border rounded px-3 py-1.5 text-sm focus:ring-1 focus:ring-blue-500 outline-none w-48"
          />
          <button type="submit" className="rounded border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Search</button>
        </form>
        <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
          className="border rounded px-2 py-1.5 text-sm">
          <option value="">All Categories</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          className="border rounded px-2 py-1.5 text-sm">
          <option value="">All Status</option>
          <option value="PUBLISHED">Published</option>
          <option value="DRAFT">Draft</option>
          <option value="ARCHIVED">Archived</option>
        </select>
        <span className="text-xs text-gray-500 self-center">{articles.length} articles</span>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : articles.length === 0 ? (
        <div className="bg-white border rounded-lg p-10 text-center text-gray-400">
          <p className="text-2xl mb-2">📝</p>
          <p className="text-sm">No articles found.</p>
        </div>
      ) : (
        <div className="bg-white border rounded-lg shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {["Title", "Category", "Tags", "Author", "Views", "Version", "Status", "Actions"].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {articles.map(a => (
                <tr key={a.id} className={`hover:bg-gray-50 ${a.status === "ARCHIVED" ? "opacity-60" : ""}`}>
                  <td className="px-4 py-3 font-medium text-gray-800 max-w-xs">
                    <a href={`/dashboard/knowledge-base/${a.id}`} className="hover:text-blue-600 line-clamp-2">
                      {a.is_featured && <span className="text-xs bg-amber-100 text-amber-700 rounded px-1 mr-1">★</span>}
                      {a.title}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">{a.category_name ?? "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {(a.tags ?? []).slice(0, 3).map((tag: string) => (
                        <span key={tag} className="text-xs bg-gray-100 text-gray-500 rounded px-1">#{tag}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{a.author_name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{a.view_count}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">v{a.version}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${
                      a.status === "PUBLISHED" ? "bg-green-100 text-green-700" :
                      a.status === "DRAFT" ? "bg-gray-100 text-gray-600" :
                      "bg-red-100 text-red-500"
                    }`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <a href={`/dashboard/knowledge-base/${a.id}`} className="text-xs text-blue-600 hover:underline">View</a>
                      <a href={`/dashboard/knowledge-base/${a.id}/edit`} className="text-xs text-gray-600 hover:underline">Edit</a>
                      {a.status !== "ARCHIVED" && (
                        <button onClick={() => del(a.id)} className="text-xs text-red-500 hover:underline">Archive</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
